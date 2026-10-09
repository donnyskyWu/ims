import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #210 · 冲话费账号筛选认完整昵称，成本汇总关键字只筛当前表。
 * 纯 UI。月份 2024-11 / 2023-06，避开 #58/#64/#70/#120/#162 用过的月份。
 */
const POOL_NO = 'AC-E2E-POOL'
const POOL_NICK = 'E2E池内抖音'
const SUM_NO = 'AC-E2E-SUM'
const MONTH = '2024-11'
const EMPTY = '2023-06'
const POOL_AMOUNT = '18.71'
const SUM_AMOUNT = '19.73'
const SHOTS = '/opt/cursor/artifacts/corp-210'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchAccount(page: Page, accountNo: string) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(accountNo)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: accountNo })
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
      !r.url().includes('/unlock') &&
      r.request().method() === 'POST',
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

test.describe('CORP recharge nickname filter and summary keyword', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('nickname filter, ambiguous copy, and summary keyword (#210)', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await openDouyin(page)

    const pool = await searchAccount(page, POOL_NO)
    await registerRecharge(page, pool, POOL_AMOUNT, `${MONTH}-06`)
    const sum = await searchAccount(page, SUM_NO)
    await registerRecharge(page, sum, SUM_AMOUNT, `${MONTH}-08`)

    const list = page.getByTestId('acct-recharge-list')
    await expect(list).toContainText(POOL_AMOUNT)
    await expect(list).toContainText(SUM_AMOUNT)

    await page.getByTestId('acct-recharge-filter-account').fill(POOL_NICK)
    await page.getByTestId('acct-recharge-filter-month').fill(MONTH)
    const nickResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('acct-recharge-query').click()
    const nickUrl = (await nickResp).url()
    expect(nickUrl).toContain('accountId=')
    expect(nickUrl).toContain(`month=${MONTH}`)
    await expect(list).toContainText(POOL_AMOUNT)
    await expect(list).not.toContainText(SUM_AMOUNT)
    await list.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/01-nickname-filter.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-account').fill('E2E')
    await page.getByTestId('acct-recharge-query').click()
    await expect(page.getByTestId('acct-recharge-filter-msg')).toContainText('请输入完整账号编号或昵称')
    await expect(page.getByTestId('acct-recharge-empty')).toContainText('请输入完整账号编号或昵称')
    await expect(list).not.toContainText(POOL_AMOUNT)
    await page.screenshot({ path: `${SHOTS}/02-ambiguous-account.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-account').fill('NO-SUCH-NICK-210')
    await page.getByTestId('acct-recharge-query').click()
    await expect(page.getByTestId('acct-recharge-filter-msg')).toContainText('未找到该账号')

    const resetResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('acct-recharge-reset').click()
    const resetUrl = (await resetResp).url()
    expect(resetUrl).not.toContain('accountId=')
    expect(resetUrl).not.toContain('month=')
    await expect(list).toContainText(POOL_AMOUNT)
    await expect(list).toContainText(SUM_AMOUNT)

    await page.getByTestId('acct-summary-month').fill(MONTH)
    await page.getByTestId('acct-summary-groupby').selectOption('ACCOUNT')
    const summaryResp = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge/summary') &&
        !r.url().includes('/export') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-summary-query').click()
    expect(((await (await summaryResp).json()) as { code: number }).code).toBe(0)
    const summary = page.getByTestId('acct-recharge-summary')
    await expect(summary).toContainText(POOL_NO)
    await expect(summary).toContainText(SUM_NO)
    const totals = page.getByTestId('acct-summary-totals')
    const totalsText = await totals.innerText()

    await page.getByTestId('acct-summary-keyword').fill(POOL_NICK)
    await expect(page.getByTestId('acct-summary-filter-note')).toContainText('筛选后 1 行')
    await expect(page.getByTestId('acct-summary-filter-note')).toContainText('合计与导出仍为整月')
    await expect(summary.locator('[data-testid="acct-summary-row"]')).toHaveCount(1)
    await expect(summary).toContainText(POOL_NO)
    await expect(summary).not.toContainText(SUM_NO)
    await expect(totals).toHaveText(totalsText)
    await summary.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/03-summary-keyword.png`, fullPage: true })

    await page.getByTestId('acct-summary-keyword').fill('没有这个维度210')
    await expect(page.getByTestId('acct-summary-filter-empty')).toHaveText('没有符合筛选的汇总行')
    await expect(page.getByTestId('acct-summary-empty')).toHaveCount(0)
    await expect(page.getByTestId('acct-summary-filter-note')).toHaveCount(0)
    await expect(totals).toHaveText(totalsText)

    const [csv] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('acct-summary-export-csv').click(),
    ])
    expect(csv.suggestedFilename()).toBe(`recharge_summary_${MONTH}_ACCOUNT.csv`)
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('文件为整月，不含汇总关键字')
    const csvText = fs.readFileSync((await csv.path())!, 'utf8')
    expect(csvText).toContain(POOL_NO)
    expect(csvText).toContain(SUM_NO)
    await page.screenshot({ path: `${SHOTS}/04-summary-export-full-month.png`, fullPage: true })

    await page.getByTestId('acct-summary-month').fill(EMPTY)
    const emptyResp = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge/summary') &&
        !r.url().includes('/export') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-summary-query').click()
    expect(((await (await emptyResp).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('acct-summary-export-note')).toHaveCount(0)
    await expect(page.getByTestId('acct-summary-empty')).toHaveText('该月无冲话费记录')
    await expect(page.getByTestId('acct-summary-filter-empty')).toHaveCount(0)
    await summary.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/05-empty-month.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
