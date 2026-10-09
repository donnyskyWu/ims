import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-111-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

const zeroCosts = {
  rechargeCost: '0',
  fixedCost: '0',
  sampleCost: '0',
  shareDaren: '0',
  shareRealname: '0',
}

function uniqueDay() {
  const stamp = Date.now()
  const year = 2060 + (stamp % 25)
  const month = 1 + (Math.floor(stamp / 25) % 12)
  const day = 1 + (Math.floor(stamp / 400) % 27)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${year}-${pad(month)}-${pad(day)}`
}

/**
 * #111 FIN-002 利润列表口径切换排序（纯 UI）
 * 同一日期两场：高毛利负净利 vs 低毛利正净利。
 * 净利润 / 经营利润降序与毛利降序对调；负数净利润红括号。
 */
test.describe('fin profit metric sort closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('switching gross operating and net reorders the profit list', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const day = uniqueDay()
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode: highGross } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E 高毛利 ${day}`,
      gmv: 100_000,
      refundAmount: 0,
      actualStart: `${day}T20:00:00+08:00`,
      actualEnd: `${day}T22:00:00+08:00`,
    })
    await submitAndConfirmFinCostViaUi(page, highGross, { adCost: '120000', ...zeroCosts })

    const { sessionCode: highNet } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E 高净利 ${day}`,
      gmv: 30_000,
      refundAmount: 0,
      actualStart: `${day}T20:00:00+08:00`,
      actualEnd: `${day}T22:00:00+08:00`,
    })
    await submitAndConfirmFinCostViaUi(page, highNet, { adCost: '0', ...zeroCosts })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-date-from').fill(day)
    await page.getByTestId('fin-profit-date-to').fill(day)

    const netResp = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/profit/list') &&
        r.url().includes('profitType=NET') &&
        r.url().includes(`dateFrom=${day}`) &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const netBody = (await (await netResp).json()) as {
      code: number
      data?: { profitType?: string; list?: Array<{ sessionCode?: string; netProfit?: number }> }
    }
    expect(netBody.code).toBe(0)
    expect(netBody.data?.profitType).toBe('NET')
    expect(netBody.data?.list?.map((row) => row.sessionCode)).toEqual([highNet, highGross])

    const rows = page.locator('[data-testid="fin-profit-row"]')
    await expect(rows).toHaveCount(2)
    await expect(rows.nth(0)).toHaveAttribute('data-session', highNet)
    await expect(rows.nth(1)).toHaveAttribute('data-session', highGross)
    await expect(rows.nth(1).getByTestId('fin-profit-net')).toHaveClass(/neg/)
    await expect(rows.nth(1).getByTestId('fin-profit-net')).toContainText('(25,000.00)')
    await expect(rows.nth(0).getByTestId('fin-profit-net')).toContainText('28,500.00')
    await expect(page.getByTestId('fin-profit-sort-hint')).toContainText('按净利润降序')
    await expect(page.getByTestId('fin-profit-summary-label')).toHaveText('净利润合计')
    await expect(page.getByTestId('fin-profit-summary-shown')).toContainText('3,500.00')
    await page.screenshot({ path: `${shotDir}/01-sort-net.png`, fullPage: true })

    const grossResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.url().includes('profitType=GROSS') && r.status() === 200,
    )
    await page.getByTestId('fin-profit-metric-GROSS').click()
    const grossBody = (await (await grossResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; grossProfit?: number }> }
    }
    expect(grossBody.code).toBe(0)
    expect(grossBody.data?.list?.map((row) => row.sessionCode)).toEqual([highGross, highNet])
    await expect(rows.nth(0)).toHaveAttribute('data-session', highGross)
    await expect(rows.nth(0).getByTestId('fin-profit-gross')).toContainText('95,000.00')
    await expect(rows.nth(1).getByTestId('fin-profit-gross')).toContainText('28,500.00')
    await expect(page.getByTestId('fin-profit-sort-hint')).toContainText('按毛利降序')
    await expect(page.getByTestId('fin-profit-summary-label')).toHaveText('毛利合计')
    await expect(page.getByTestId('fin-profit-summary-shown')).toContainText('123,500.00')
    await expect(page.getByTestId('fin-profit-sort-GROSS')).toContainText('↓')
    await page.screenshot({ path: `${shotDir}/02-sort-gross.png`, fullPage: true })

    const operatingResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.url().includes('profitType=OPERATING') && r.status() === 200,
    )
    await page.getByTestId('fin-profit-sort-OPERATING').click()
    const operatingBody = (await (await operatingResp).json()) as {
      code: number
      data?: { profitType?: string; list?: Array<{ sessionCode?: string }> }
    }
    expect(operatingBody.code).toBe(0)
    expect(operatingBody.data?.profitType).toBe('OPERATING')
    expect(operatingBody.data?.list?.map((row) => row.sessionCode)).toEqual([highNet, highGross])
    await expect(rows.nth(0)).toHaveAttribute('data-session', highNet)
    await expect(rows.nth(1).getByTestId('fin-profit-operating')).toHaveClass(/neg/)
    await expect(rows.nth(1).getByTestId('fin-profit-operating')).toContainText('(25,000.00)')
    await expect(page.getByTestId('fin-profit-sort-hint')).toContainText('按经营利润降序')
    await expect(page.getByTestId('fin-profit-summary-shown')).toContainText('3,500.00')
    await page.screenshot({ path: `${shotDir}/03-sort-operating.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
