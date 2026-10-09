import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-106-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #106 FIN 残留：利润异常净利率 Tab + 利润反查聚合下钻 / 异常清单（纯 UI）
 * 两场标准成本作同行，一场投放 80000 拉低净利率，应只标出异常场次并高亮投流成本。
 */
test.describe('fin profit abnormal and aggregate closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('2σ abnormal tab and profit-trace aggregate highlight the outlier cost', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)

    const normalA = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E FIN 同行A ${Date.now()}`,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, normalA.sessionCode)

    const normalB = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E FIN 同行B ${Date.now()}`,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, normalB.sessionCode)

    const outlier = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E FIN 异常 ${Date.now()}`,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, outlier.sessionCode, { adCost: '80000' })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(outlier.sessionCode)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('tbody tr', { hasText: outlier.sessionCode }).first()).toContainText('6,400.00')
    await page.screenshot({ path: `${shotDir}/01-profit-list.png`, fullPage: true })

    await page.getByTestId('fin-profit-tab-abnormal').click()
    const abnormalRow = page.getByTestId(`fin-profit-abnormal-row-${outlier.sessionCode}`)
    await expect(abnormalRow).toBeVisible({ timeout: 15_000 })
    await expect(abnormalRow).toContainText('6.53%')
    await expect(abnormalRow).toContainText('83.06%')
    await expect(page.getByTestId(`fin-profit-abnormal-row-${normalA.sessionCode}`)).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-profit-abnormal-tab.png`, fullPage: true })

    await abnormalRow.getByTestId('fin-profit-abnormal-verify').click()
    const detail = page.getByTestId('fin-profit-detail-drawer')
    await expect(detail).toBeVisible()
    await expect(detail.getByTestId('fin-profit-abnormal-hint')).toContainText('2σ')
    await expect(detail).toContainText(outlier.sessionCode)
    await page.screenshot({ path: `${shotDir}/03-profit-verify-drawer.png`, fullPage: true })

    await page.goto('/ims/fin/profit-trace')
    await expect(page.locator('h1')).toHaveText('利润反查', { timeout: 15_000 })
    await page.getByTestId('fin-trace-tab-aggregate').click()
    await page.getByTestId('fin-trace-aggregate-ACCOUNT').click()
    const accountRow = page.locator('tr', { hasText: 'AC-E2E-FIN' }).first()
    await expect(accountRow).toBeVisible({ timeout: 15_000 })
    await accountRow.getByRole('button', { name: '展开' }).click()
    await expect(page.getByTestId('fin-trace-aggregate-table')).toContainText(outlier.sessionCode)
    await expect(page.getByTestId('fin-trace-aggregate-table')).toContainText(normalA.sessionCode)
    await page.screenshot({ path: `${shotDir}/04-trace-aggregate.png`, fullPage: true })

    await page.getByTestId('fin-trace-tab-abnormal').click()
    const traceRow = page.getByTestId(`fin-trace-abnormal-row-${outlier.sessionCode}`)
    await expect(traceRow).toBeVisible({ timeout: 15_000 })
    await expect(traceRow).toContainText('投流成本')
    await page.screenshot({ path: `${shotDir}/05-trace-abnormal-tab.png`, fullPage: true })

    await traceRow.getByTestId('fin-trace-abnormal-open').click()
    const drawer = page.getByTestId('fin-profit-trace-chain-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('BR-209')
    const highlighted = drawer.locator('[data-highlight="1"]')
    await expect(highlighted).toContainText('投流成本')
    await expect(highlighted).toContainText('80,000.00')
    await page.screenshot({ path: `${shotDir}/06-trace-highlight-cost.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})