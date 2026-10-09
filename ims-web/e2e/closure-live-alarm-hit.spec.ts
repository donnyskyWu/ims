import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
} from './closure-helpers'

/**
 * #134 LIVE-003（acceptance · 纯 UI）
 * 登记并提交下播（场观默认 500）→ 新建「场观低于 1000」规则
 * → 查询命中 → 再查合并 ×2 → 处置已处理 → 只读详情与统计
 */
test.describe('live alarm hit handle closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('rule hit dedup handle and readonly stats', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E 告警 ${Date.now()}`,
      gmv: 12_000,
      refundAmount: 100,
    })

    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警')

    await page.getByTestId('live-alarm-rule-open').click()
    const drawer = page.getByTestId('live-alarm-rule-drawer')
    await expect(drawer).toBeVisible()
    const ruleName = `场观过低 ${sessionCode.slice(-4)}`
    await drawer.getByTestId('live-alarm-rule-name').fill(ruleName)
    await drawer.getByTestId('live-alarm-rule-metric').selectOption('viewer_count')
    await drawer.getByTestId('live-alarm-rule-op').selectOption('LT')
    await drawer.getByTestId('live-alarm-rule-threshold').fill('1000')
    await drawer.getByTestId('live-alarm-rule-level').selectOption('2')

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/rule') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('live-alarm-rule-save').click()
    const saveBody = (await (await saveResp).json()) as { code: number }
    expect(saveBody.code).toBe(0)
    await expect(page.locator('tbody tr', { hasText: ruleName })).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('live-alarm-tab-records').click()
    await page.getByTestId('live-alarm-session').fill(sessionCode)
    const firstResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('live-alarm-query').click()
    const firstBody = (await (await firstResp).json()) as {
      code: number
      data?: { list?: Array<{ mergeCount?: number; handleStatus?: string; alarmContent?: string }> }
    }
    expect(firstBody.code).toBe(0)
    expect(firstBody.data?.list?.[0]?.handleStatus).toBe('UNHANDLED')
    expect(firstBody.data?.list?.[0]?.alarmContent || '').toContain('低于阈值')

    const row = page.locator('[data-testid="live-alarm-row"]', { hasText: sessionCode }).first()
    await expect(row).toBeVisible()

    const secondResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('live-alarm-query').click()
    const secondBody = (await (await secondResp).json()) as { data?: { list?: Array<{ mergeCount?: number }> } }
    expect(secondBody.data?.list?.[0]?.mergeCount).toBe(2)
    await expect(row.getByTestId('live-alarm-merge')).toHaveText('×2')

    await row.getByTestId('live-alarm-handle').click()
    const handleDrawer = page.getByTestId('live-alarm-handle-drawer')
    await handleDrawer.getByTestId('live-alarm-handle-status').selectOption('HANDLED')
    await handleDrawer.getByTestId('live-alarm-handle-remark').fill('已核对场观')
    const handleResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/record/') && r.url().includes('/handle') && r.request().method() === 'PUT',
    )
    await handleDrawer.getByTestId('live-alarm-handle-submit').click()
    const handleBody = (await (await handleResp).json()) as { code: number }
    expect(handleBody.code).toBe(0)
    await expect(row.getByTestId('live-alarm-handle-state')).toHaveText('已处理')

    await row.getByTestId('live-alarm-detail').click()
    const detail = page.getByTestId('live-alarm-detail-body')
    await expect(detail).toContainText('已核对场观')
    await expect(detail).toContainText('不外发钉钉或短信')

    await page.screenshot({ path: '/opt/cursor/artifacts/live-alarm-detail.png', fullPage: true })

    await page.getByTestId('live-alarm-tab-stats').click()
    await expect(page.getByTestId('live-alarm-stats-handled')).not.toHaveText('0')
    await expect(page.getByTestId('live-alarm-trend-row').first()).toBeVisible()
    await page.screenshot({ path: '/opt/cursor/artifacts/live-alarm-stats.png', fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})