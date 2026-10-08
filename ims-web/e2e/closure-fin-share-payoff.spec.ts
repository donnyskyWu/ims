import { test, expect } from '@playwright/test'
import {
  approveAndPayoffFinSharesViaUi,
  attachClosurePageHooks,
  loginAdmin,
  openFinLedgerReconcileViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S3-05/08 窄切片**（#57 · 纯 UI）
 * 复用 #50 LIVE→成本核准链 → 分成双审发放 PAID_OFF → 台账四账一致
 */
test.describe('fin share payoff and ledger closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share orders reach PAID_OFF and ledger books match', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)
    await approveAndPayoffFinSharesViaUi(page, sessionCode)
    await openFinLedgerReconcileViaUi(page, sessionCode)

    expect(pageErrors).toEqual([])
  })
})