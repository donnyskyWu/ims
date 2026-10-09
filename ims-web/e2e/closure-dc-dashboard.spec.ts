import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-129-screenshots'

/**
 * Checklist **E2E-S12 切片 / DC-003**（#129 · 纯 UI）
 * 经营总览含本场 GMV/净利润 · 健康度目标 98 · 账号维度下钻到场次并跳穿透查询
 */
test.describe('dc dashboard overview health dimension', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('confirmed session shows on the dashboard and drills into trace', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
      planStartTime: '2026-10-06T20:00:00+08:00',
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.locator('.search input').fill('全链路看板')
    await page.locator('.nav-item', { hasText: '全链路看板' }).click()
    await expect(page.locator('h1')).toHaveText('全链路数据看板', { timeout: 15_000 })

    await page.getByTestId('dc-dash-period').fill('2026-10')
    const overviewResp = page.waitForResponse(
      (r) =>
        r.url().includes('/dc/dashboard/overview') &&
        r.url().includes('statPeriod=2026-10') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('dc-dash-refresh').click()
    const overviewBody = (await (await overviewResp).json()) as {
      code: number
      data?: { totalGmv?: number; netProfit?: number; dataAsOf?: string }
    }
    expect(overviewBody.code).toBe(0)
    expect(overviewBody.data?.totalGmv).toBeGreaterThanOrEqual(100_000)
    expect(overviewBody.data?.netProfit).toBeGreaterThanOrEqual(81_400)
    await expect(page.getByTestId('dc-dash-as-of')).toContainText('数据截至')
    await expect(page.getByTestId('dc-dash-gmv')).toContainText('¥')
    await expect(page.getByTestId('dc-dash-profit')).toContainText('¥')

    const health = page.getByTestId('dc-dash-health')
    await expect(health).toBeVisible()
    await expect(page.getByTestId('dc-dash-complete-rate')).toContainText('%')
    await expect(health).toContainText('目标 > 98%')
    const alarmed = (await health.getAttribute('data-alarm')) === '1'
    if (alarmed) {
      await expect(page.getByTestId('dc-dash-health-alert')).toContainText('低于目标 98%')
    } else {
      await expect(page.getByTestId('dc-dash-health-alert')).toHaveCount(0)
    }
    await page.screenshot({ path: `${SHOTS}/01-overview-health.png`, fullPage: true })

    await page.getByTestId('dc-dash-dim-ACCOUNT').check()
    const accountRow = page.locator('[data-testid="dc-dash-dim-row"]').filter({ hasText: 'AC-E2E-FIN' })
    await expect(accountRow).toBeVisible({ timeout: 15_000 })
    await accountRow.getByTestId('dc-dash-dim-expand').click()
    const child = page.locator(`[data-testid="dc-dash-dim-child"][data-session="${sessionCode}"]`)
    await expect(child).toContainText('100,000.00')
    await expect(child).toContainText('81,400.00')
    await page.screenshot({ path: `${SHOTS}/02-account-drill.png`, fullPage: true })

    await child.getByTestId('dc-dash-session-link').click()
    await expect(page.locator('h1')).toHaveText('穿透查询', { timeout: 15_000 })
    await expect(page.getByTestId('dc-trace-keyword')).toHaveValue(sessionCode)
    await expect(page.getByTestId('dc-trace-entry-type')).toHaveValue('SESSION')
    await expect(page.locator(`[data-node-type="SESSION"][data-node-id="${sessionCode}"]`)).toBeVisible({
      timeout: 15_000,
    })
    await page.screenshot({ path: `${SHOTS}/03-session-trace.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
