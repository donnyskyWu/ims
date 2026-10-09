import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-115-screenshots'

/**
 * #115 FIN-P-R3（纯 UI）
 * 利润列表操作列「重算」确认 → POST /fin/profit/recalc/{sessionCode}
 * 新版本留痕；期间 LOCKED 时按钮置灰（1142）
 */
test.describe('fin profit list recalc confirm', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('list recalc confirm bumps version and keeps net profit', async ({ page }) => {
    fs.mkdirSync(SHOT_DIR, { recursive: true })
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
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const listBody = (await (await listResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; calcStatus?: string; calcVersion?: number; netProfit?: number; financeStatus?: string }> }
    }
    expect(listBody.code).toBe(0)
    const before = listBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(before?.calcStatus).toBe('CALCULATED')
    expect(before?.financeStatus).toBe('OPEN')
    expect(before?.netProfit).toBe(81_400)
    const beforeVersion = before?.calcVersion ?? 0
    expect(beforeVersion).toBeGreaterThan(0)

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await expect(uiRow).toContainText('81,400.00')
    await expect(uiRow).toContainText(`V${beforeVersion}`)
    const recalcBtn = uiRow.getByTestId('fin-profit-recalc')
    await expect(recalcBtn).toBeEnabled()
    await recalcBtn.click()

    const dialog = page.getByTestId('fin-profit-recalc-confirm')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText(`V${beforeVersion + 1}`)
    await expect(dialog).toContainText('旧结果留痕')
    await expect(dialog).toContainText('FIN-P-R3')
    await page.screenshot({ path: `${SHOT_DIR}/01-recalc-confirm.png`, fullPage: true })

    const recalcResp = page.waitForResponse(
      (r) => r.url().includes(`/fin/profit/recalc/${sessionCode}`) && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-recalc-ok').click()
    const recalcBody = (await (await recalcResp).json()) as {
      code: number
      data?: { calcVersion?: number; calcStatus?: string; message?: string }
    }
    expect(recalcBody.code).toBe(0)
    expect(recalcBody.data?.calcStatus).toBe('RECALCULATED')
    expect(recalcBody.data?.calcVersion).toBe(beforeVersion + 1)

    await expect(dialog).toBeHidden()
    await expect(page.getByTestId('fin-profit-recalc-msg')).toContainText('利润已重算')
    await expect(page.getByTestId('fin-profit-recalc-msg')).toContainText(`V${beforeVersion + 1}`)
    await expect(uiRow).toContainText(`V${beforeVersion + 1}`)
    await expect(uiRow).toContainText('81,400.00')
    await expect(uiRow).toContainText('结算中')
    await page.screenshot({ path: `${SHOT_DIR}/02-recalculated.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })

  test('locked period disables profit recalc', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const stamp = Date.now()
    const year = 8000 + (stamp % 1000)
    const month = String((Math.floor(stamp / 4000) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    const planStartTime = `${periodMonth}-15T20:00:00+08:00`

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E profit recalc lock ${stamp}`,
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
    const listBody = (await (await listResp).json()) as {
      data?: { list?: Array<{ financeStatus?: string }> }
    }
    expect(listBody.data?.list?.[0]?.financeStatus).toBe('LOCKED')

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    const recalcBtn = uiRow.getByTestId('fin-profit-recalc')
    await expect(recalcBtn).toBeDisabled()
    await expect(recalcBtn).toHaveAttribute('title', '财务期间已结账，重算冻结（1142）')
    await page.screenshot({ path: `${SHOT_DIR}/03-recalc-locked.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
