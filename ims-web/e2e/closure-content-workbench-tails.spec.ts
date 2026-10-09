import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs, passContentReviewViaUi } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/content-143'

/**
 * #143 CONTENT 工作台收尾（纯 UI）
 * 内容列表按类型/平台筛选；发布抽屉核对清单；超 24h 发布单进入工作台待办；操作日志记「新增发布单」。
 */
test.describe('content workbench tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('list filters, publish checklist, overdue todo and content audit', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const videoTitle = `E2E143 短视频 ${stamp}`
    const articleTitle = `E2E143 图文 ${stamp}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })

    async function createContent(title: string, contentType: string, platform: string) {
      await page.getByRole('button', { name: '新增内容' }).click()
      const drawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
      await drawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
      await drawer.locator('.fld').filter({ hasText: '内容类型' }).locator('select').selectOption(contentType)
      await drawer.getByTestId('edit-platform').selectOption(platform)
      const createResp = page.waitForResponse(
        (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
      )
      await drawer.getByRole('button', { name: '保存' }).click()
      const body = (await (await createResp).json()) as { code: number; data?: { id: number } }
      expect(body.code).toBe(0)
      await expect(page.locator('tr', { hasText: title }).first()).toBeVisible({ timeout: 15_000 })
      return body.data!.id
    }

    const contentId = await createContent(videoTitle, 'SHORT_VIDEO', 'DOUYIN')
    await createContent(articleTitle, 'ARTICLE', 'KUAISHOU')

    await page.getByTestId('filter-content-type').selectOption('ARTICLE')
    const typeResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.url().includes('contentType=ARTICLE') && r.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await typeResp
    await expect(page.locator('tr', { hasText: articleTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: videoTitle })).toHaveCount(0)
    await expect(page.locator('tr', { hasText: articleTitle }).getByTestId('row-content-type')).toHaveText('图文')

    await page.getByRole('button', { name: '重置' }).click()
    await page.getByTestId('filter-platform').selectOption('DOUYIN')
    const platformResp = page.waitForResponse(
      (r) => r.url().includes('platformType=DOUYIN') && r.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await platformResp
    await expect(page.locator('tr', { hasText: videoTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: articleTitle })).toHaveCount(0)
    await expect(page.locator('tr', { hasText: videoTitle }).getByTestId('row-platform')).toHaveText('抖音')
    await page.screenshot({ path: `${SHOTS}/list-filters.png`, fullPage: true })

    await page.getByRole('button', { name: '重置' }).click()
    await page.locator('input[placeholder="标题"]').fill(videoTitle)
    const titleResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await titleResp
    const videoRow = page.locator('tr', { hasText: videoTitle }).first()
    await videoRow.getByRole('button', { name: '提审' }).click()
    await expect(videoRow).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)
    await passContentReviewViaUi(page, { title: videoTitle, stageTab: '一级审核' })
    await passContentReviewViaUi(page, { title: videoTitle, stageTab: '二级审核' })

    const acctListResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/corp/account/douyin')
    const acctBody = (await (await acctListResp).json()) as {
      code: number
      data?: { list?: { id: number; status?: string }[] }
    }
    expect(acctBody.code).toBe(0)
    const inUse = acctBody.data?.list?.find((row) => row.status === 'IN_USE')
    expect(inUse?.id).toBeTruthy()

    const overdueAt = new Date(Date.now() - 48 * 3600 * 1000)
    const planPublishAt = `${overdueAt.toISOString().slice(0, 19)}+08:00`

    await page.goto('/ims/content/publish')
    await page.getByRole('button', { name: '新建发布单' }).click()
    const pubDrawer = page.locator('.drawer.on').filter({ hasText: '新建发布单' })
    const checklistResp = page.waitForResponse(
      (r) => r.url().includes(`/content/${contentId}`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await pubDrawer.locator('input[type="number"]').first().fill(String(contentId))
    await checklistResp
    await expect(pubDrawer.getByTestId('publish-checklist')).toBeVisible()
    await expect(pubDrawer.locator('[data-item="REVIEW_PASSED"]')).toHaveAttribute('data-passed', '1')
    await expect(pubDrawer.locator('[data-item="COMPLIANCE"]')).toHaveAttribute('data-passed', '1')
    await expect(pubDrawer.locator('[data-item="QUALITY"]')).toHaveAttribute('data-passed', '1')
    await expect(pubDrawer.locator('[data-item="BRAND"]')).toHaveAttribute('data-passed', '1')
    await pubDrawer.locator('.fld').filter({ hasText: '文案' }).locator('input').fill(`caption ${stamp}`)
    await expect(pubDrawer.locator('[data-item="CAPTION"]')).toHaveAttribute('data-passed', '1')
    await page.screenshot({ path: `${SHOTS}/publish-checklist.png`, fullPage: true })

    await pubDrawer.locator('input[type="number"]').nth(1).fill(String(inUse!.id))
    await pubDrawer.locator('input[placeholder="DOUYIN"]').fill('DOUYIN')
    await pubDrawer.locator('input[placeholder="2026-10-08T20:00:00+08:00"]').fill(planPublishAt)
    const pubResp = page.waitForResponse(
      (r) => r.url().includes('/content/publish') && r.request().method() === 'POST' && r.status() === 200,
    )
    await pubDrawer.getByRole('button', { name: '保存' }).click()
    const pubBody = (await (await pubResp).json()) as { code: number; data?: { publishNo: string } }
    expect(pubBody.code).toBe(0)
    const publishNo = pubBody.data!.publishNo
    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: publishNo }).first()
    await expect(row.getByTestId('publish-overdue')).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${SHOTS}/publish-overdue.png`, fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.getByText(`发布督办：${publishNo}`).first()).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${SHOTS}/workbench-todo.png`, fullPage: true })

    await page.goto('/ims/system/log')
    await page.locator('.qbar select').selectOption('内容')
    await page.locator('input[placeholder="操作人 / 路径"]').fill('publish')
    const logResp = page.waitForResponse(
      (r) => r.url().includes('/system/operate-log/page') && r.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await logResp
    await expect(page.locator('tr', { hasText: '新增发布单' }).first()).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${SHOTS}/content-audit.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})