import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  openFinProfitTraceChainViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S3-09 / TC-IMS-FIN-02-01**（#51 · 纯 UI · DC-002 · BR-209）
 * 复用 #50 LIVE/FIN 链 → `/ims/fin/profit-trace` 反查穿透可见
 */
test.describe('fin profit trace closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('confirmed cost then profit trace chain drawer shows penetration', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    const drawer = await openFinProfitTraceChainViaUi(page, sessionCode)
    await expect(drawer).toContainText('BR-209')
    await expect(drawer).toContainText('81,400.00')
    await expect(drawer).toContainText('AC-E2E-FIN')
    await expect(drawer).toContainText('E2E财务实名人')
    await expect(drawer).toContainText('投流成本')
    await expect(drawer).toContainText('5,000.00')
    await expect(drawer).toContainText('达人分成')
    await expect(drawer).toContainText('3,000.00')

    expect(pageErrors).toEqual([])
  })
})
