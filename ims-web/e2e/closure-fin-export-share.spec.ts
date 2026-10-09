import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  approveAndPayoffFinSharesViaUi,
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-145-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #145 FIN 看板日/周粒度、导出格式弹窗（PDF）与分成发放凭证（纯 UI）
 */
test.describe('fin dashboard export and share voucher closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('day trend, pdf export dialog, and payoff voucher name', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
      actualStart: '2026-10-06T20:00:00+08:00',
      actualEnd: '2026-10-06T22:00:00+08:00',
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/dashboard')
    await expect(page.locator('h1')).toHaveText('利润看板', { timeout: 15_000 })
    await page.getByTestId('fin-dash-period').fill('2026-10')
    const overviewResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/overview') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-dash-query').click()
    await overviewResp

    const dayResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/trend') && r.url().includes('granularity=DAY') && r.status() === 200,
    )
    await page.getByTestId('fin-dash-grain-DAY').click()
    await dayResp
    await expect(page.getByTestId('fin-dash-trend')).toContainText('2026-10-06')
    await page.screenshot({ path: `${shotDir}/01-trend-day.png`, fullPage: true })

    const weekResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/trend') && r.url().includes('granularity=WEEK') && r.status() === 200,
    )
    await page.getByTestId('fin-dash-grain-WEEK').click()
    await weekResp
    await expect(page.getByTestId('fin-dash-trend')).toContainText('周')
    await page.screenshot({ path: `${shotDir}/02-trend-week.png`, fullPage: true })

    await page.getByTestId('fin-dash-export').click()
    const dialog = page.getByTestId('fin-dash-export-dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByTestId('fin-dash-export-scope')).toContainText('2026-10')
    await expect(dialog.getByTestId('fin-dash-export-scope')).toContainText('账号')
    await dialog.getByTestId('fin-dash-export-pdf').check()
    await page.screenshot({ path: `${shotDir}/03-export-pdf-dialog.png`, fullPage: true })

    const exportResp = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/dashboard/export') &&
        !r.url().includes('/file') &&
        r.url().includes('format=PDF') &&
        r.request().method() === 'GET',
    )
    await dialog.getByTestId('fin-dash-export-confirm').click()
    const exportBody = (await (await exportResp).json()) as { code: number; data?: { fileName?: string } }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.fileName).toContain('.pdf')
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('导出成功')
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('.pdf')
    await page.screenshot({ path: `${shotDir}/04-export-pdf-ok.png`, fullPage: true })

    await approveAndPayoffFinSharesViaUi(page, sessionCode, { voucherFileName: 'voucher-e2e.txt' })
    await page.screenshot({ path: `${shotDir}/05-share-voucher.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
