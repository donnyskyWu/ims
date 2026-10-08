import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  E2E_FIN_ACCOUNT_NO,
  loginAdmin,
  openDcAccountTraceViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S12-01 切片 / DC-001**（#52 · 纯 UI · 账号入口）
 * 复用 #50 LIVE 链造场次 → `/ims/dc/trace` 账号穿透 · 关系图 + 明细表
 */
test.describe('dc account trace closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('live session then account entry trace shows graph and session detail', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    const trace = await openDcAccountTraceViaUi(page, E2E_FIN_ACCOUNT_NO, sessionCode)
    expect(trace?.nodes?.some((n) => n.nodeLabel?.includes(E2E_FIN_ACCOUNT_NO))).toBe(true)
    await expect(page.getByTestId('dc-trace-graph')).toContainText('PERSON')

    expect(pageErrors).toEqual([])
  })
})
