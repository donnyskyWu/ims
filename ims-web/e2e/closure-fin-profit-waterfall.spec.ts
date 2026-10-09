import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-109-screenshots'

/**
 * #109 FIN-P-R2：利润详情三级口径瀑布（GMV 逐项扣到净利润 · BR-108）
 * 纯 UI：核准下播 → 成本核准 → 详情抽屉可见瀑布与计算快照表。
 */
test.describe('fin profit three-level waterfall', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('profit detail waterfall deducts GMV down to net profit', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await page.setViewportSize({ width: 1440, height: 1100 })
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const profitListResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const profitBody = (await (await profitListResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; netProfit?: number; grossProfit?: number; operatingProfit?: number }> }
    }
    expect(profitBody.code).toBe(0)
    const profitRow = profitBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(profitRow?.netProfit).toBe(81_400)
    expect(profitRow?.grossProfit).toBe(93_000)
    expect(profitRow?.operatingProfit).toBe(87_900)

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await uiRow.getByRole('button', { name: '详情' }).click()

    const drawer = page.getByTestId('fin-profit-detail-drawer')
    await expect(drawer).toBeVisible()
    const box = await drawer.boundingBox()
    const viewport = page.viewportSize()
    expect(box).toBeTruthy()
    expect(viewport).toBeTruthy()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.width / viewport!.width).toBeGreaterThan(0.75)

    const waterfall = page.getByTestId('fin-profit-waterfall')
    await expect(waterfall).toContainText('三级口径瀑布')
    await expect(page.getByTestId('fin-profit-wf-gmv')).toHaveAttribute('data-running', '100000')
    await expect(page.getByTestId('fin-profit-wf-gmv')).toContainText('100,000.00')
    await expect(page.getByTestId('fin-profit-wf-refund')).toContainText('退款')
    await expect(page.getByTestId('fin-profit-wf-refund')).toContainText('2,000.00')
    await expect(page.getByTestId('fin-profit-wf-commission')).toContainText('平台佣金')
    await expect(page.getByTestId('fin-profit-wf-commission')).toContainText('5,000.00')
    await expect(page.getByTestId('fin-profit-wf-gross')).toHaveAttribute('data-level', 'GROSS')
    await expect(page.getByTestId('fin-profit-wf-gross')).toHaveAttribute('data-running', '93000')
    await expect(page.getByTestId('fin-profit-wf-gross')).toContainText('93,000.00')
    await expect(page.getByTestId('fin-profit-wf-ad')).toContainText('投放成本')
    await expect(page.getByTestId('fin-profit-wf-recharge')).toContainText('冲话费')
    await expect(page.getByTestId('fin-profit-wf-operating')).toHaveAttribute('data-level', 'OPERATING')
    await expect(page.getByTestId('fin-profit-wf-operating')).toHaveAttribute('data-running', '87900')
    await expect(page.getByTestId('fin-profit-wf-operating')).toContainText('87,900.00')
    await expect(page.getByTestId('fin-profit-wf-fixed')).toContainText('固定成本')
    await expect(page.getByTestId('fin-profit-wf-sample')).toContainText('样品成本')
    await expect(page.getByTestId('fin-profit-wf-shareDaren')).toContainText('达人分成')
    await expect(page.getByTestId('fin-profit-wf-shareRealname')).toContainText('实名人分成')
    await expect(page.getByTestId('fin-profit-wf-net')).toHaveAttribute('data-level', 'NET')
    await expect(page.getByTestId('fin-profit-wf-net')).toHaveAttribute('data-running', '81400')
    await expect(page.getByTestId('fin-profit-wf-net')).toContainText('81,400.00')
    await expect(page.getByTestId('fin-profit-wf-net')).toHaveAttribute('title', /BR-108/)

    await page.getByTestId('fin-profit-wf-gross').hover()
    await expect(page.getByTestId('fin-profit-wf-gross').locator('.wf-tip')).toBeVisible()
    await expect(page.getByTestId('fin-profit-wf-gross').locator('.wf-tip')).toContainText('毛利 = GMV')

    await expect(page.getByTestId('fin-profit-formula')).toContainText('netProfit = revenue - refund - totalCost')
    await expect(page.getByTestId('fin-profit-formula')).toContainText('operatingProfit = grossProfit - adCost - rechargeCost')
    await expect(page.getByTestId('fin-profit-param-sampleCost')).toContainText('样品成本')
    await expect(page.getByTestId('fin-profit-param-sampleCost')).toContainText('500.00')
    await expect(page.getByTestId('fin-profit-param-totalCost')).toContainText('16,600.00')
    await expect(page.getByTestId('fin-profit-level-net')).toContainText('81,400.00')

    await waterfall.screenshot({ path: `${SHOTS}/01-waterfall.png` })
    await page.getByTestId('fin-profit-snapshot').screenshot({ path: `${SHOTS}/02-snapshot.png` })
    await page.screenshot({ path: `${SHOTS}/03-profit-detail.png` })

    expect(pageErrors).toEqual([])
  })
})
