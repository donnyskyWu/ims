import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs, passContentReviewViaUi } from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI**）
 * Given: e2e_author 立项/送审 · admin 审核通过 · UI 新建超计划发布单
 * When: `/ims/content/publish` 督办 hint · 行内「回填」
 * Then: 已归档/已回填
 */
test.describe('content publish supervision closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pending hint then receipt archives publish row', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-pub-closure-${Date.now()}`
    const title = `E2E 发布督办 ${label}`
    const publishUrl = `https://example.com/p/${label}`

    await loginAs(page, 'e2e_author')

    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number; data?: { id: number } }
    expect(createBody.code).toBe(0)
    const contentId = createBody.data!.id

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '提审' }).click()
    await expect(contentRow).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)

    await passContentReviewViaUi(page, { title, stageTab: '一级审核' })
    await passContentReviewViaUi(page, { title, stageTab: '二级审核' })

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
    const accountId = inUse!.id

    const overdueAt = new Date(Date.now() - 48 * 3600 * 1000)
    const planPublishAt = `${overdueAt.toISOString().slice(0, 19)}+08:00`

    await page.goto('/ims/content/publish')
    await page.getByRole('button', { name: '新建发布单' }).click()
    const pubDrawer = page.locator('.drawer.on').filter({ hasText: '新建发布单' })
    await pubDrawer.locator('input[type="number"]').first().fill(String(contentId))
    await pubDrawer.locator('input[type="number"]').nth(1).fill(String(accountId))
    await pubDrawer.locator('input[placeholder="DOUYIN"]').fill('DOUYIN')
    await pubDrawer.locator('input[placeholder="2026-10-08T20:00:00+08:00"]').fill(planPublishAt)
    await pubDrawer.locator('.fld').filter({ hasText: '文案' }).locator('input').fill(`caption ${label}`)

    const pubResp = page.waitForResponse(
      (r) => r.url().includes('/content/publish') && r.request().method() === 'POST' && r.status() === 200,
    )
    await pubDrawer.getByRole('button', { name: '保存' }).click()
    const pubBody = (await (await pubResp).json()) as {
      code: number
      data?: { publishNo: string; publishStatus?: string }
    }
    expect(pubBody.code).toBe(0)
    const publishNo = pubBody.data!.publishNo
    expect(pubBody.data?.publishStatus).toBe('PENDING_PUBLISH')

    await expect(page.getByText(/^督办：/)).toBeVisible({ timeout: 15_000 })

    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: publishNo }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('待发布')

    await row.getByRole('button', { name: '回填' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '回填发布链接' })
    await drawer.locator('input[placeholder="https://..."]').fill(publishUrl)
    const receiptResp = page.waitForResponse(
      (r) => r.url().includes('/content/publish/') && r.url().includes('/receipt') && r.request().method() === 'PUT',
    )
    await drawer.getByRole('button', { name: '保存' }).click()
    await receiptResp

    await expect(row.locator('a', { hasText: '已回填' })).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('已归档')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
