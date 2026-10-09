import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-118-screenshots'

/**
 * #118 FIN-P-R3 · 利润详情抽屉底部手动重算确认
 * 纯 UI：确认后 POST /fin/profit/recalc/{sessionCode} → RECALCULATED · 新版本
 * 期间 LOCKED：按钮置灰 + 1142 提示
 */
test.describe('fin profit drawer manual recalc', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('detail drawer confirm creates the next profit version', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const stamp = Date.now()
    const year = 3200 + (stamp % 400)
    const month = String((Math.floor(stamp / 400) % 12) + 1).padStart(2, '0')
    const planStartTime = `${year}-${month}-15T20:00:00+08:00`

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E profit recalc ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const listBody = (await (await listResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; calcVersion?: number; calcStatus?: string }> }
    }
    expect(listBody.code).toBe(0)
    const before = listBody.data?.list?.find((row) => row.sessionCode === sessionCode)
    expect(before?.calcStatus).toBe('CALCULATED')
    const beforeVersion = before?.calcVersion ?? 1

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await uiRow.getByRole('button', { name: '详情' }).click()
    const drawer = page.getByTestId('fin-profit-detail-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('netProfit = revenue - refund - totalCost')
    await expect(drawer).toContainText(`版本 V${beforeVersion}`)
    const openBtn = drawer.getByTestId('fin-profit-recalc-open')
    await expect(openBtn).toBeEnabled()
    await openBtn.click()

    const dialog = page.getByTestId('fin-profit-recalc-confirm')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText(`重算将生成新版本 V${beforeVersion + 1}，旧结果留痕`)
    await expect(dialog).toContainText('重算生成新版本，旧结果留痕（FIN-P-R3）')
    await page.screenshot({ path: `${SHOT_DIR}/01-recalc-confirm.png`, fullPage: true })

    const recalcResp = page.waitForResponse(
      (r) => r.url().includes(`/fin/profit/recalc/${sessionCode}`) && r.request().method() === 'POST',
    )
    await dialog.getByTestId('fin-profit-recalc-submit').click()
    const recalcBody = (await (await recalcResp).json()) as {
      code: number
      data?: { calcVersion?: number; calcStatus?: string }
    }
    expect(recalcBody.code).toBe(0)
    expect(recalcBody.data?.calcStatus).toBe('RECALCULATED')
    expect(recalcBody.data?.calcVersion).toBe(beforeVersion + 1)

    await expect(dialog).not.toBeVisible()
    await expect(drawer).toContainText('RECALCULATED')
    await expect(drawer).toContainText(`版本 V${beforeVersion + 1}`)
    await expect(drawer.getByTestId('fin-profit-recalc-done')).toContainText('利润已重算')
    await expect(uiRow).toContainText(`V${beforeVersion + 1}`)
    await page.screenshot({ path: `${SHOT_DIR}/02-recalc-done.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })

  test('locked period disables drawer recalc and shows 1142 hint', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const stamp = Date.now()
    const year = 4100 + (stamp % 400)
    const month = String((Math.floor(stamp / 400) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    const planStartTime = `${periodMonth}-15T20:00:00+08:00`

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E profit lock recalc ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.getByTestId('fin-period-month').fill(periodMonth)
    await page.getByTestId('fin-period-month').blur()
    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/fin/period/close') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('fin-period-close').click()
    const closeBody = (await (await closeResp).json()) as { code: number; data?: { financeStatus?: string } }
    expect(closeBody.code).toBe(0)
    expect(closeBody.data?.financeStatus).toBe('LOCKED')

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await uiRow.getByRole('button', { name: '详情' }).click()
    const drawer = page.getByTestId('fin-profit-detail-drawer')
    await expect(drawer).toBeVisible()
    const openBtn = drawer.getByTestId('fin-profit-recalc-open')
    await expect(openBtn).toBeDisabled()
    await expect(openBtn).toHaveAttribute('title', '财务期间已结账，重算冻结（1142）')
    await expect(drawer.getByTestId('fin-profit-recalc-locked')).toContainText('财务期间已结账，重算冻结（1142）')
    await page.screenshot({ path: `${SHOT_DIR}/03-locked-recalc-disabled.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
