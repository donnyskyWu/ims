import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/s7-topic-gantt-190'

/**
 * S7 选题甘特尾巴（#190 · acceptance · 纯 UI）
 * Given: 不重建选题库 / 甘特主路径 / 状态空态看板
 * When: 提报时选热点并填写计划发布日，再按单日、不存在的账号、颠倒区间查看甘特
 * Then: 热点参考只读且不阻断提交；待评审选题在单日打点；账号筛空与颠倒区间各有说明
 */
test.describe('content topic gantt tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pending plan date, hotspot stub, and gantt empty edges stay on the topic page', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-tail-${Date.now()}`
    const title = `E2E 甘特尾巴 ${label}`
    const planDate = '2026-11-18'

    await loginAdmin(page)
    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })

    await page.getByTestId('topic-create-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('topic-title').fill(title)
    await drawer.getByTestId('topic-description').fill(`内容要求：甘特尾巴 ${label}`)
    await drawer.getByTestId('topic-source').selectOption({ label: '热点' })
    const hotspot = drawer.getByTestId('topic-hotspot')
    await expect(hotspot).toBeVisible()
    await expect(hotspot.getByText('加载中')).toHaveCount(0, { timeout: 15_000 })
    const hotspotState = hotspot
      .getByTestId('topic-hotspot-empty')
      .or(hotspot.getByTestId('topic-hotspot-error'))
      .or(hotspot.getByTestId('topic-hotspot-row'))
    await expect(hotspotState.first()).toBeVisible()
    if (await hotspot.getByTestId('topic-hotspot-error').count()) {
      await hotspot.getByTestId('topic-hotspot-retry').click()
      await expect(hotspot.getByText('加载中')).toHaveCount(0, { timeout: 15_000 })
    }
    await page.screenshot({ path: `${SHOTS}/01-hotspot-stub.png`, fullPage: true })

    await drawer.getByTestId('topic-edit-plan-date').fill(planDate)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic') && !r.url().includes('/gantt') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('topic-submit').click()
    const created = (await (await createResp).json()) as { code: number; data?: { topicStatus?: string; planPublishDate?: string } }
    expect(created.code).toBe(0)
    expect(created.data?.topicStatus).toBe('PENDING_REVIEW')
    expect(created.data?.planPublishDate).toBe(planDate)
    await expect(drawer).not.toBeVisible({ timeout: 10_000 })

    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('待评审')
    await expect(row).toContainText(planDate)
    await expect(row).toContainText('未立项不可出任务')
    await page.screenshot({ path: `${SHOTS}/02-pending-with-plan-date.png`, fullPage: true })

    await row.getByRole('button', { name: '评审' }).click()
    const review = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await expect(review).toBeVisible()
    await expect(review.getByText('正在加载启用中的 SOP')).toHaveCount(0, { timeout: 15_000 })
    const sopOptions = await review.getByTestId('topic-sop').locator('option').count()
    if (sopOptions <= 1) {
      await expect(review.getByTestId('topic-sop-empty')).toContainText('暂无启用中的 SOP')
    } else {
      await expect(review.getByTestId('topic-sop-empty')).toHaveCount(0)
    }
    await page.screenshot({ path: `${SHOTS}/03-sop-catalog.png`, fullPage: true })
    await review.locator('.dr-x').click()
    await expect(review).not.toBeVisible({ timeout: 10_000 })

    await page.getByTestId('topic-view-gantt').click()
    await expect(page.getByTestId('topic-gantt')).toBeVisible()
    await page.getByTestId('topic-gantt-from').fill(planDate)
    await page.getByTestId('topic-gantt-to').fill(planDate)
    const ganttResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    const ganttBody = (await (await ganttResp).json()) as {
      code: number
      data?: { items?: Array<{ title: string; planPublishDate: string; topicStatus: string }> }
    }
    expect(ganttBody.code).toBe(0)
    const hit = (ganttBody.data?.items || []).find((item) => item.title === title)
    expect(hit?.planPublishDate).toBe(planDate)
    expect(hit?.topicStatus).toBe('PENDING_REVIEW')
    const ganttRow = page.getByTestId('topic-gantt-row').filter({ hasText: title })
    await expect(ganttRow).toBeVisible({ timeout: 15_000 })
    await expect(ganttRow).toContainText('待评审')
    await expect(ganttRow.locator('[data-testid="topic-gantt-mark"]')).toHaveAttribute('data-date', planDate)
    await page.screenshot({ path: `${SHOTS}/04-single-day-gantt.png`, fullPage: true })

    await page.getByTestId('topic-gantt-account').fill('999999')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.url().includes('accountId=999999') && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    const emptyBody = (await (await emptyResp).json()) as { code: number; data?: { items?: unknown[] } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.items || []).toEqual([])
    const ganttEmpty = page.getByTestId('topic-gantt-empty')
    await expect(ganttEmpty).toHaveAttribute('data-reason', 'account')
    await expect(ganttEmpty).toContainText('该账号在此区间暂无排期')
    await page.screenshot({ path: `${SHOTS}/05-gantt-account-empty.png`, fullPage: true })

    await page.getByTestId('topic-gantt-from').fill('2026-11-20')
    await page.getByTestId('topic-gantt-to').fill('2026-11-18')
    await page.getByTestId('topic-gantt-query').click()
    await expect(page.getByTestId('topic-gantt-error')).toContainText('请选择有效的计划发布日区间')
    await expect(page.getByTestId('topic-gantt-row')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/06-gantt-reversed-range.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
