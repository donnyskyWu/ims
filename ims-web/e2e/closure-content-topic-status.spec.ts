import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/s7-topic-status-159'

/**
 * CONTENT-002 选题状态空态与 TOP-R1 字段定位（acceptance · #159 · 纯 UI）
 * Given: UI 创建启用 SOP
 * When: 用不会命中的关键词筛待评审，再打开状态看板；提报后缺 SOP/计划发布日点立项
 * Then: 列表与四列都是该状态空态；红框落在空字段且仍返回 1052；补齐后进入已立项列
 */
test.describe('content topic status empty closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('status filters show empty copy and approve highlights missing TOP-R1 fields', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-topic-status-${Date.now()}`
    const sopName = `E2E 状态 SOP ${label}`
    const title = `E2E 状态选题 ${label}`
    const missingKeyword = `no-topic-${label}`

    await loginAdmin(page)
    await createSopViaUi(page, { sopName, nodeName: '脚本' })

    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })
    await page.getByTestId('topic-filter-keyword').fill(missingKeyword)
    await page.getByTestId('topic-filter-status').selectOption('PENDING_REVIEW')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-filter-search').click()
    const emptyBody = (await (await emptyResp).json()) as { code: number; data?: { total?: number } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.total).toBe(0)
    const listEmpty = page.getByTestId('topic-list-empty')
    await expect(listEmpty).toHaveAttribute('data-status', 'PENDING_REVIEW')
    await expect(listEmpty).toContainText('暂无符合当前筛选的选题')
    await expect(listEmpty).toContainText('状态 待评审')
    await page.screenshot({ path: `${SHOTS}/01-list-empty.png`, fullPage: true })

    await page.getByTestId('topic-filter-reset').click()
    await page.getByTestId('topic-view-board').click()
    await expect(page.getByTestId('topic-status-board')).toBeVisible()
    const cancelledEmpty = page.getByTestId('topic-status-empty-CANCELLED')
    await expect(cancelledEmpty).toBeVisible({ timeout: 15_000 })
    await expect(cancelledEmpty).toHaveAttribute('data-status', 'CANCELLED')
    await expect(cancelledEmpty).toContainText('暂无已取消选题')
    await expect(page.getByTestId('topic-status-count-CANCELLED')).toHaveText('0')
    await page.screenshot({ path: `${SHOTS}/02-board-cancelled-empty.png`, fullPage: true })

    await page.getByTestId('topic-view-list').click()
    await page.getByTestId('topic-create-open').click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await expect(createDrawer).toBeVisible()
    await createDrawer.getByTestId('topic-title').fill(title)
    await createDrawer.getByTestId('topic-description').fill(`内容要求：状态空态 ${label}`)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByTestId('topic-submit').click()
    const created = (await (await createResp).json()) as { code: number }
    expect(created.code).toBe(0)
    await expect(createDrawer).not.toBeVisible({ timeout: 10_000 })

    const pendingRow = page.locator('tr', { hasText: title })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await pendingRow.getByRole('button', { name: '评审' }).click()
    const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await expect(reviewDrawer).toBeVisible()

    const blocked = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewDrawer.getByTestId('topic-approve').click()
    const blockedBody = (await (await blocked).json()) as { code: number; msg?: string }
    expect(blockedBody.code).toBe(1052)
    await expect(reviewDrawer.getByTestId('topic-review-error')).toContainText('1052')
    await expect(reviewDrawer.getByTestId('topic-sop-error')).toHaveText('请选择挂接 SOP')
    await expect(reviewDrawer.getByTestId('topic-plan-date-error')).toHaveText('请填写计划发布日')
    await expect(reviewDrawer.getByTestId('topic-sop')).toHaveClass(/err/)
    await expect(reviewDrawer.getByTestId('topic-plan-date')).toHaveClass(/err/)
    await page.screenshot({ path: `${SHOTS}/03-top-r1-fields.png`, fullPage: true })

    await reviewDrawer.getByTestId('topic-sop').selectOption({ label: sopName })
    await expect(reviewDrawer.getByTestId('topic-sop-error')).toHaveCount(0)
    const dateOnly = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewDrawer.getByTestId('topic-approve').click()
    const dateOnlyBody = (await (await dateOnly).json()) as { code: number }
    expect(dateOnlyBody.code).toBe(1052)
    await expect(reviewDrawer.getByTestId('topic-sop-error')).toHaveCount(0)
    await expect(reviewDrawer.getByTestId('topic-plan-date-error')).toBeVisible()
    await expect(reviewDrawer.getByTestId('topic-sop')).not.toHaveClass(/err/)

    await reviewDrawer.getByTestId('topic-plan-date').fill('2026-12-18')
    await expect(reviewDrawer.getByTestId('topic-plan-date-error')).toHaveCount(0)
    const approved = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewDrawer.getByTestId('topic-approve').click()
    const approvedBody = (await (await approved).json()) as { code: number }
    expect(approvedBody.code).toBe(0)
    await expect(reviewDrawer).not.toBeVisible({ timeout: 10_000 })
    await expect(pendingRow).toContainText('已立项')
    await expect(pendingRow).toContainText('可出任务')

    await page.getByTestId('topic-view-board').click()
    const approvedCol = page.getByTestId('topic-status-col-APPROVED_PROJECT')
    await expect(approvedCol.getByTestId('topic-board-card').filter({ hasText: title })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('topic-status-col-PENDING_REVIEW').getByTestId('topic-board-card').filter({ hasText: title })).toHaveCount(0)
    await expect(page.getByTestId('topic-status-empty-CANCELLED')).toContainText('暂无已取消选题')
    await page.screenshot({ path: `${SHOTS}/04-board-approved.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
