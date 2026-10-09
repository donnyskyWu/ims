import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  loginAs,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/fin-146'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #146 FIN 尾巴：R9 看板/利润列表金额脱敏，场次行打开直播台账详情。
 * 数据经 UI 登记；e2e_fin_r9 由启动种子提供。
 */
test.describe('fin r9 amount mask and ledger jump', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('dashboard session opens the live ledger and R9 amounts stay masked', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
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
    await expect(page.getByTestId('fin-dash-gmv')).toContainText('¥')
    await expect(page.getByTestId('fin-dash-amount-mask')).toHaveCount(0)

    const accountRow = page.locator('[data-testid="fin-dash-drill"] tbody tr', { hasText: 'AC-E2E-FIN' }).first()
    await expect(accountRow).toBeVisible({ timeout: 15_000 })
    await accountRow.getByTestId('fin-dash-expand').click()
    const sessionRow = page.locator('[data-testid="fin-dash-session"]', { hasText: sessionCode })
    await expect(sessionRow.getByTestId('fin-dash-session-net')).toContainText('81,400.00')
    await page.screenshot({ path: `${shotDir}/01-admin-dashboard-session.png`, fullPage: true })

    await sessionRow.getByTestId('fin-dash-open-ledger').click()
    await expect(page).toHaveURL(new RegExp(`/ims/live/sessions\\?sessionCode=${sessionCode}`))
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await expect(page.locator('input[placeholder="场次 ID"]')).toHaveValue(sessionCode)
    const ledger = page.locator('.drawer.on').filter({ has: page.getByTestId('live-ledger-detail') })
    await expect(ledger).toBeVisible({ timeout: 15_000 })
    await expect(ledger).toContainText(sessionCode)
    await expect(ledger).toContainText('AC-E2E-FIN')
    await expect(ledger).toContainText('ENDED')
    await page.screenshot({ path: `${shotDir}/02-live-ledger-from-dashboard.png`, fullPage: true })

    await loginAs(page, 'e2e_fin_r9')
    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const profitRow = page.locator('[data-testid="fin-profit-row"]', { hasText: sessionCode })
    await expect(profitRow).toBeVisible({ timeout: 15_000 })
    await expect(profitRow.getByTestId('fin-profit-gmv')).toHaveText('***')
    await expect(profitRow.getByTestId('fin-profit-gross')).toHaveText('***')
    await expect(profitRow.getByTestId('fin-profit-operating')).toHaveText('***')
    await expect(profitRow.getByTestId('fin-profit-net')).toHaveText('***')
    await expect(page.getByTestId('fin-profit-summary-revenue')).toHaveText('***')
    await expect(page.getByTestId('fin-profit-summary-cost')).toHaveText('***')
    await expect(page.getByTestId('fin-profit-summary-shown')).toHaveText('***')
    await expect(page.getByTestId('fin-profit-amount-mask')).toHaveText('金额已脱敏')
    await expect(profitRow).toContainText('83.06')
    await page.screenshot({ path: `${shotDir}/03-r9-profit-list-mask.png`, fullPage: true })

    await page.goto('/ims/fin/dashboard')
    await expect(page.locator('h1')).toHaveText('利润看板', { timeout: 15_000 })
    await page.getByTestId('fin-dash-period').fill('2026-10')
    const maskedOverview = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/overview') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-dash-query').click()
    await maskedOverview
    await expect(page.getByTestId('fin-dash-gmv')).toHaveText('***')
    await expect(page.getByTestId('fin-dash-cost')).toHaveText('***')
    await expect(page.getByTestId('fin-dash-profit')).toHaveText('***')
    await expect(page.getByTestId('fin-dash-amount-mask')).toHaveText('金额已脱敏')
    await expect(page.getByTestId('fin-dash-rate')).not.toContainText('***')
    const maskedAccount = page.locator('[data-testid="fin-dash-drill"] tbody tr', { hasText: 'AC-E2E-FIN' }).first()
    await maskedAccount.getByTestId('fin-dash-expand').click()
    const maskedSession = page.locator('[data-testid="fin-dash-session"]', { hasText: sessionCode })
    await expect(maskedSession.getByTestId('fin-dash-session-net')).toHaveText('***')
    await expect(page.getByTestId('fin-dash-share-total').first()).toHaveText('***')
    await page.screenshot({ path: `${shotDir}/04-r9-dashboard-mask.png`, fullPage: true })

    await maskedSession.getByTestId('fin-dash-open-ledger').click()
    await expect(page).toHaveURL(new RegExp(`/ims/live/sessions\\?sessionCode=${sessionCode}`))
    const r9Ledger = page.locator('.drawer.on').filter({ has: page.getByTestId('live-ledger-detail') })
    await expect(r9Ledger).toBeVisible({ timeout: 15_000 })
    await expect(r9Ledger).toContainText(sessionCode)
    await expect(r9Ledger).toContainText('AC-E2E-FIN')
    await page.screenshot({ path: `${shotDir}/05-r9-ledger-from-dashboard.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
