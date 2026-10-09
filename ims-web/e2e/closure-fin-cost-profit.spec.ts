import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S3-01/02/03 切片**（#50 · 纯 UI · BR-107/108）
 * LIVE 核准下播 → 成本提交/核准 → 利润看板 CALCULATED + 净利润 81400
 */
test.describe('fin cost to profit closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('live report confirm then cost confirm shows profit on dashboard', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await expect(page.getByTestId('fin-cost-complete-rate')).toBeVisible()

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const profitListResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const profitBody = (await (await profitListResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; calcStatus?: string; netProfit?: number }> }
    }
    expect(profitBody.code).toBe(0)
    const profitRow = profitBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(profitRow?.calcStatus).toBe('CALCULATED')
    expect(profitRow?.netProfit).toBe(81_400)

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await expect(uiRow).toContainText('81,400.00')
    await expect(page.getByTestId('fin-profit-col-calc-status')).toHaveText('计算状态')
    await expect(page.getByTestId('fin-profit-col-calculated-at')).toHaveText('计算时间')
    await expect(uiRow.getByTestId('fin-profit-calc-status')).toHaveText('已计算')
    await expect(uiRow.getByTestId('fin-profit-calculated-at')).toHaveText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)

    await page.setViewportSize({ width: 1680, height: 900 })
    await uiRow.getByTestId('fin-profit-calculated-at').scrollIntoViewIfNeeded()
    await page.screenshot({
      path: '/opt/cursor/artifacts/e2e-113-screenshots/profit-list-calc-columns.png',
      fullPage: true,
    })

    await uiRow.getByRole('button', { name: '详情' }).click()
    const detailDrawer = page.locator('.drawer').filter({ hasText: '利润详情' })
    await expect(detailDrawer).toBeVisible()
    await expect(detailDrawer).toContainText('netProfit = revenue - refund - totalCost')
    await expect(detailDrawer).toContainText('已计算')
    await page.screenshot({
      path: '/opt/cursor/artifacts/e2e-113-screenshots/profit-detail-calc-status.png',
      fullPage: true,
    })

    expect(pageErrors).toEqual([])
  })
})
