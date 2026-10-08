import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
  submitFinCostCorrectionViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S3-04**（#54 · 纯 UI）
 * 成本更正 → 利润 RECALCULATED · 达人分成同步（79900 净利润）
 */
test.describe('fin cost correction closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('cost correction recalculates profit and share amounts', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/profit')
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const beforeResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const beforeBody = (await (await beforeResp).json()) as {
      data?: { list?: Array<{ calcStatus?: string; netProfit?: number }> }
    }
    expect(beforeBody.data?.list?.[0]?.calcStatus).toBe('CALCULATED')
    expect(beforeBody.data?.list?.[0]?.netProfit).toBe(81_400)

    await submitFinCostCorrectionViaUi(
      page,
      sessionCode,
      { adCost: 6000, shareDaren: 3500 },
      'E2E 投放与分成更正',
    )

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const profitListResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const profitBody = (await (await profitListResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; calcStatus?: string; netProfit?: number; calcVersion?: number }> }
    }
    expect(profitBody.code).toBe(0)
    const profitRow = profitBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(profitRow?.calcStatus).toBe('RECALCULATED')
    expect(profitRow?.netProfit).toBe(79_900)
    expect((profitRow?.calcVersion ?? 0) >= 2).toBe(true)

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await expect(uiRow).toContainText('79,900.00')

    await page.goto('/ims/fin/profit-trace')
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    await page.getByRole('button', { name: '查询' }).click()
    const traceRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(traceRow).toBeVisible({ timeout: 15_000 })
    await traceRow.getByRole('button', { name: '反查' }).click()
    const drawer = page.getByTestId('fin-profit-trace-chain-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('达人分成')
    await expect(drawer).toContainText('3,500.00')

    expect(pageErrors).toEqual([])
  })
})
