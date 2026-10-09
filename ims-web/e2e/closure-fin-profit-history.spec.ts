import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-107-screenshots'
mkdirSync(SHOTS, { recursive: true })

/**
 * #107 · 利润重算版本历史（纯 UI）
 * 成本核准 → 详情时间轴 V1 → 手动重算生成 V2，旧版净利润仍可见，列表版本号更新
 */
test.describe('fin profit history closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')
  test.setTimeout(90_000)

  test('detail timeline keeps prior version after manual recalc', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
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
      data?: { list?: Array<{ sessionCode?: string; calcVersion?: number; netProfit?: number }> }
    }
    expect(profitBody.code).toBe(0)
    const profitRow = profitBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(profitRow?.calcVersion).toBe(1)
    expect(profitRow?.netProfit).toBe(81_400)

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow.getByTestId('fin-profit-calc-version')).toHaveText('V1')

    const historyResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/history/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await uiRow.getByRole('button', { name: '详情' }).click()
    const historyBody = (await (await historyResp).json()) as {
      code: number
      data?: Array<{ calcVersion?: number; triggerType?: string; netProfit?: number }>
    }
    expect(historyBody.code).toBe(0)
    expect(historyBody.data?.[0]?.calcVersion).toBe(1)
    expect(historyBody.data?.[0]?.triggerType).toBe('AUTO_CONFIRM')
    expect(historyBody.data?.[0]?.netProfit).toBe(81_400)

    const drawer = page.getByTestId('fin-profit-detail-drawer')
    await expect(drawer).toBeVisible()
    const v1 = drawer.getByTestId('fin-profit-history-v1')
    await expect(v1).toContainText('成本核准')
    await expect(v1).toContainText('81,400.00')
    await page.screenshot({ path: `${SHOTS}/01-history-v1.png`, fullPage: true })

    await drawer.getByTestId('fin-profit-recalc-open').click()
    const dialog = page.getByTestId('fin-profit-recalc-dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('新版本 V2')
    await expect(dialog).toContainText('旧结果留痕')
    await page.screenshot({ path: `${SHOTS}/02-recalc-confirm.png`, fullPage: true })

    const recalcResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/recalc/') && r.request().method() === 'POST' && r.status() === 200,
    )
    const historyAfter = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/history/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-recalc-submit').click()
    const recalcBody = (await (await recalcResp).json()) as {
      code: number
      data?: { calcVersion?: number; calcStatus?: string }
    }
    expect(recalcBody.code).toBe(0)
    expect(recalcBody.data?.calcVersion).toBe(2)
    expect(recalcBody.data?.calcStatus).toBe('RECALCULATED')
    const afterBody = (await (await historyAfter).json()) as {
      code: number
      data?: Array<{ calcVersion?: number; triggerType?: string; netProfit?: number }>
    }
    expect(afterBody.code).toBe(0)
    expect(afterBody.data?.map((row) => row.calcVersion)).toEqual([2, 1])
    expect(afterBody.data?.[0]?.triggerType).toBe('MANUAL')
    expect(afterBody.data?.[0]?.netProfit).toBe(81_400)
    expect(afterBody.data?.[1]?.netProfit).toBe(81_400)

    await expect(drawer.getByTestId('fin-profit-history-v2')).toContainText('手动')
    await expect(drawer.getByTestId('fin-profit-history-v1')).toContainText('成本核准')
    await expect(drawer.getByTestId('fin-profit-history-v1')).toContainText('81,400.00')
    await expect(drawer).toContainText('当前版本 V2')
    await page.screenshot({ path: `${SHOTS}/03-history-v1-v2.png`, fullPage: true })

    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()
    const refreshed = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(refreshed.getByTestId('fin-profit-calc-version')).toHaveText('V2')
    await expect(refreshed).toContainText('81,400.00')
    await page.screenshot({ path: `${SHOTS}/04-list-version-v2.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
