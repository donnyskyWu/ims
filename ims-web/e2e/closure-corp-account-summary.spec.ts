import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SUM_NO = 'AC-E2E-SUM'
const SHOTS = '/opt/cursor/artifacts/e2e-70-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchSum(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(SUM_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: SUM_NO })
  await expect(row).toBeVisible()
  return row
}

async function registerRecharge(page: Page, row: Locator, amount: string, rechargeDate: string) {
  await row.getByRole('button', { name: '冲话费' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '登记冲话费' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-recharge-amount').fill(amount)
  await drawer.getByTestId('acct-recharge-date').fill(rechargeDate)
  const resp = page.waitForResponse(
    (r) =>
      r.url().includes('/account/recharge') &&
      !r.url().includes('/list') &&
      !r.url().includes('/verify') &&
      !r.url().includes('/summary') &&
      r.request().method() === 'POST',
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

async function querySummary(page: Page, month: string, groupBy: string) {
  await page.getByTestId('acct-summary-month').fill(month)
  await page.getByTestId('acct-summary-groupby').selectOption(groupBy)
  const resp = page.waitForResponse(
    (r) => r.url().includes('/account/recharge/summary') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('acct-summary-query').click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await page.getByTestId('acct-recharge-summary').scrollIntoViewIfNeeded()
}

test.describe('CORP account recharge cost summary S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('E2E-S4-10 recharge summary matches records by account dept and platform (#70)', async ({ page }) => {
    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchSum(page)

    await registerRecharge(page, row, '120.50', '2026-04-02')
    await registerRecharge(page, row, '79.50', '2026-04-18')
    await registerRecharge(page, row, '50', '2026-03-15')
    const list = page.getByTestId('acct-recharge-list')
    await expect(list).toContainText('120.50')
    await expect(list).toContainText('79.50')
    await expect(list).toContainText('50.00')
    await list.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/01-recharge-records.png`, fullPage: true })

    await querySummary(page, '2026-04', 'ACCOUNT')
    const table = page.getByTestId('acct-summary-table')
    const totals = page.getByTestId('acct-summary-totals')
    const accountRow = page.getByTestId('acct-summary-row').filter({ hasText: SUM_NO })
    await expect(accountRow).toContainText('¥200.00')
    await expect(accountRow).toContainText('E2E汇总抖音')
    await expect(totals).toContainText('¥200.00')
    await expect(totals).toContainText('2 笔')
    await expect(table).not.toContainText('50.00')
    await page.screenshot({ path: `${SHOTS}/02-summary-account.png`, fullPage: true })

    await querySummary(page, '2026-04', 'DEPT')
    const deptRow = page.getByTestId('acct-summary-row').filter({ hasText: '部门#70070' })
    await expect(deptRow).toContainText('¥200.00')
    await expect(totals).toContainText('¥200.00')
    await expect(totals).toContainText('2 笔')
    await page.screenshot({ path: `${SHOTS}/03-summary-dept.png`, fullPage: true })

    await querySummary(page, '2026-04', 'PLATFORM')
    const platformRow = page.getByTestId('acct-summary-row').filter({ hasText: '抖音' })
    await expect(platformRow).toContainText('¥200.00')
    await expect(totals).toContainText('¥200.00')
    await expect(totals).toContainText('2 笔')
    await page.screenshot({ path: `${SHOTS}/04-summary-platform.png`, fullPage: true })

    await querySummary(page, '2026-03', 'ACCOUNT')
    const marchRow = page.getByTestId('acct-summary-row').filter({ hasText: SUM_NO })
    await expect(marchRow).toContainText('¥50.00')
    await expect(totals).toContainText('¥50.00')
    await expect(totals).toContainText('1 笔')
    await expect(totals).not.toContainText('200.00')
    await page.screenshot({ path: `${SHOTS}/05-summary-march.png`, fullPage: true })
  })
})
