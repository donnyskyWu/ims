import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/fin-179'

/**
 * #179 台账跳转空态、期间锁提示、成本/利润空筛选。
 * 纯 UI。不改分成规则，不改 R9 脱敏。
 */
test.describe('fin ledger jump empty and filter tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('ledger jump shows missing books, lock banner, and empty filters', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/fin/ledger')
    await expect(page.locator('h1')).toHaveText('台账对账', { timeout: 15_000 })
    await expect(page.getByTestId('fin-ledger-jump-empty')).toContainText('按场次核对四账')
    await page.screenshot({ path: `${SHOT_DIR}/01-ledger-jump-empty.png`, fullPage: true })

    await page.getByTestId('fin-ledger-query').fill('IMS209901019990001')
    await page.getByTestId('fin-ledger-search').click()
    await expect(page.getByTestId('fin-ledger-missing')).toContainText('未找到场次', { timeout: 15_000 })
    await page.screenshot({ path: `${SHOT_DIR}/02-ledger-session-missing.png`, fullPage: true })

    const stamp = Date.now()
    const year = 3000 + (stamp % 5000)
    const month = String((Math.floor(stamp / 5000) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    const planStartTime = `${periodMonth}-15T20:00:00+08:00`
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E ledger empty ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    await page.locator('.tab', { hasText: '待录入清单' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await pendingResp
    const pendingRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await pendingRow.getByTestId('fin-cost-ledger-jump').click()
    await expect(page).toHaveURL(new RegExp(`/ims/fin/ledger\\?sessionCode=${sessionCode}`))
    await expect(page.getByTestId('fin-ledger-consistent')).toHaveText('四账未齐', { timeout: 15_000 })
    await expect(page.getByTestId('fin-ledger-cost-empty')).toHaveText('—')
    await expect(page.getByTestId('fin-ledger-profit-empty')).toHaveText('—')
    await expect(page.getByTestId('fin-ledger-share-empty')).toHaveText('—')
    await expect(page.getByTestId('fin-ledger-cost')).toContainText('成本未录入')
    await expect(page.getByTestId('fin-ledger-period-lock')).toHaveCount(0)
    await page.screenshot({ path: `${SHOT_DIR}/03-ledger-books-empty.png`, fullPage: true })

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
    await expect(page.getByTestId('fin-period-status')).toHaveText('LOCKED')
    await expect(page.getByTestId('fin-period-lock-banner')).toContainText('财务期间已结账')
    await page.screenshot({ path: `${SHOT_DIR}/04-period-lock-banner.png`, fullPage: true })

    await page.locator('.tab', { hasText: '已录入管理' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const enteredResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await enteredResp
    const enteredRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await enteredRow.getByTestId('fin-cost-ledger-jump').click()
    await expect(page.getByTestId('fin-ledger-period-lock')).toContainText('录入、核准、更正均冻结', { timeout: 15_000 })
    await expect(page.getByTestId('fin-ledger-period-lock')).toContainText(periodMonth)
    await expect(page.getByTestId('fin-ledger-consistent')).toHaveText('未对齐')
    await expect(page.getByTestId('fin-ledger-cost')).toContainText('16,600.00')
    await expect(page.getByTestId('fin-ledger-profit')).toContainText('81,400.00')
    await page.screenshot({ path: `${SHOT_DIR}/05-ledger-period-lock.png`, fullPage: true })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.getByTestId('fin-profit-filter-platform').fill('NO-SUCH-PLAT')
    const profitResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await profitResp
    await expect(page.getByTestId('fin-profit-list-empty')).toHaveText('当前筛选无利润数据')
    await page.screenshot({ path: `${SHOT_DIR}/06-profit-filter-empty.png`, fullPage: true })
    const profitReset = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-filter-reset').click()
    await profitReset

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    const enteredTab = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.tab', { hasText: '已录入管理' }).click()
    await enteredTab
    await page.locator('input[placeholder="场次 ID"]').fill('NO-SUCH-SESSION')
    const emptyEntered = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await emptyEntered
    await expect(page.getByTestId('fin-cost-entered-empty')).toHaveText('当前筛选无已录入成本')
    const pendingTab = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.tab', { hasText: '待录入清单' }).click()
    await pendingTab
    await page.locator('input[placeholder="场次 ID"]').fill('NO-SUCH-SESSION')
    const emptyPending = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await emptyPending
    await expect(page.getByTestId('fin-cost-pending-empty')).toHaveText('当前筛选无待录入场次')
    await page.screenshot({ path: `${SHOT_DIR}/07-cost-filter-empty.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
