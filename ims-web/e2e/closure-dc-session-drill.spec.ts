import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  E2E_FIN_ACCOUNT_NO,
  loginAdmin,
  openDcAccountTraceViaUi,
  openDcSessionDetailViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S12-01 场次下钻切片 / DC-001**（#53 · 纯 UI）
 * 复用 #52 账号穿透 → 场次明细抽屉 → 导出 XLSX → 宽日期 1181
 */
test.describe('dc session drill export closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('account trace drills into session detail, exports, and shows 1181 hint', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await openDcAccountTraceViaUi(page, E2E_FIN_ACCOUNT_NO, sessionCode)
    await expect(page.getByTestId('dc-trace-query-cost')).toContainText('queryCostMs')
    await expect(page.getByTestId('dc-trace-timeout-hint')).toContainText('1181')

    const { drawer, detail } = await openDcSessionDetailViaUi(page, sessionCode)
    expect(detail?.liveData?.gmv).toBe(100_000)
    expect(detail?.profit?.netProfit).toBe(81_400)
    await expect(drawer).toContainText('81,400.00')
    await expect(drawer).toContainText('投流成本')
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('dc-trace-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('dc_trace_report.xlsx')
    const filePath = await download.path()
    expect(filePath).toBeTruthy()
    expect(fs.readFileSync(filePath!).toString('latin1')).toContain(sessionCode)
    await expect(page.getByTestId('dc-trace-export-note')).toContainText('已导出 XLSX')

    await page.getByTestId('dc-trace-date-from').fill('2020-01-01')
    await page.getByTestId('dc-trace-date-to').fill('2026-12-31')
    const slowResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('dc-trace-submit').click()
    const slowBody = (await (await slowResp).json()) as { code: number; data?: { queryCostMs?: number } }
    expect(slowBody.code).toBe(1181)
    expect(typeof slowBody.data?.queryCostMs).toBe('number')
    const hint = page.getByTestId('dc-trace-timeout-hint')
    await expect(hint).toHaveAttribute('data-degraded', '1')
    await expect(hint).toContainText('缩小日期范围')
    await expect(page.getByTestId('dc-trace-query-cost')).toContainText('queryCostMs')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
