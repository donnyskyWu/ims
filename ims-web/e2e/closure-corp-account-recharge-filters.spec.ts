import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #162 · 冲话费列表筛选（既有 list 参数）+ 空月份导出提示。
 * 纯 UI。月份 2025-07 / 2025-08 / 2099-12，避开 #58/#64/#70/#120 用过的月份。
 */
const POOL_NO = 'AC-E2E-POOL'
const JULY = '2025-07'
const AUGUST = '2025-08'
const EMPTY = '2099-12'
const SHOTS = '/opt/cursor/artifacts/e2e-162-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchPool(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(POOL_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })
  await expect(row).toBeVisible()
  return row
}

async function registerRecharge(page: Page, row: Locator, amount: string, rechargeDate: string, channelLabel: string) {
  await row.getByRole('button', { name: '冲话费' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '登记冲话费' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-recharge-amount').fill(amount)
  await drawer.getByTestId('acct-recharge-channel').selectOption({ label: channelLabel })
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

async function filterList(page: Page) {
  const resp = page.waitForResponse(
    (r) => r.url().includes('/account/recharge/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('acct-recharge-query').click()
  const url = (await resp).url()
  return url
}

test.describe('CORP recharge list filters and empty export', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('filter recharge rows and show an empty export note (#162)', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchPool(page)

    await registerRecharge(page, row, '11.11', `${JULY}-03`, '支付宝')
    await registerRecharge(page, row, '22.22', `${AUGUST}-04`, '微信')
    const list = page.getByTestId('acct-recharge-list')
    await expect(list).toContainText('11.11')
    await expect(list).toContainText('22.22')
    await page.getByTestId('acct-recharge-list').scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/01-unfiltered.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-account').fill(POOL_NO)
    await page.getByTestId('acct-recharge-filter-month').fill(JULY)
    await page.getByTestId('acct-recharge-filter-status').selectOption('UNVERIFIED')
    await page.getByTestId('acct-recharge-filter-channel').selectOption('ALIPAY')
    const julyUrl = await filterList(page)
    expect(julyUrl).toContain('verifyStatus=UNVERIFIED')
    expect(julyUrl).toContain(`month=${JULY}`)
    expect(julyUrl).toContain('channel=ALIPAY')
    expect(julyUrl).toContain('accountId=')
    await expect(list).toContainText('11.11')
    await expect(list).not.toContainText('22.22')
    await page.screenshot({ path: `${SHOTS}/02-july-alipay.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-month').fill(AUGUST)
    await page.getByTestId('acct-recharge-filter-channel').selectOption('WECHAT')
    await page.getByTestId('acct-recharge-filter-status').selectOption('')
    const augustUrl = await filterList(page)
    expect(augustUrl).toContain(`month=${AUGUST}`)
    expect(augustUrl).toContain('channel=WECHAT')
    await expect(list).toContainText('22.22')
    await expect(list).not.toContainText('11.11')
    await page.screenshot({ path: `${SHOTS}/03-august-wechat.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-status').selectOption('MATCHED')
    await filterList(page)
    await expect(page.getByTestId('acct-recharge-filter-msg')).toContainText('没有符合筛选条件的冲话费记录')
    await expect(page.getByTestId('acct-recharge-empty')).toBeVisible()
    await expect(list).not.toContainText('22.22')
    await page.screenshot({ path: `${SHOTS}/04-no-match.png`, fullPage: true })

    await page.getByTestId('acct-recharge-filter-account').fill('NO-SUCH-ACCT-162')
    await page.getByTestId('acct-recharge-query').click()
    await expect(page.getByTestId('acct-recharge-filter-msg')).toContainText('未找到该账号')
    await expect(page.getByTestId('acct-recharge-empty')).toContainText('未找到该账号')
    await page.screenshot({ path: `${SHOTS}/05-unknown-account.png`, fullPage: true })

    const resetResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('acct-recharge-reset').click()
    const resetUrl = (await resetResp).url()
    expect(resetUrl).not.toContain('accountId=')
    expect(resetUrl).not.toContain('month=')
    await expect(list).toContainText('11.11')
    await expect(list).toContainText('22.22')

    await page.getByTestId('acct-summary-month').fill(EMPTY)
    await page.getByTestId('acct-summary-groupby').selectOption('ACCOUNT')
    const summaryResp = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge/summary') &&
        !r.url().includes('/export') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-summary-query').click()
    expect(((await (await summaryResp).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('acct-summary-empty')).toContainText('该月无冲话费记录')
    await page.getByTestId('acct-recharge-summary').scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/06-empty-summary.png`, fullPage: true })

    const [csv] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('acct-summary-export-csv').click(),
    ])
    expect(csv.suggestedFilename()).toBe(`recharge_summary_${EMPTY}_ACCOUNT.csv`)
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('该月无冲话费记录')
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('已导出空表')
    const csvPath = await csv.path()
    const csvText = fs.readFileSync(csvPath!, 'utf8')
    expect(csvText).toContain('合计')
    expect(csvText).toContain('0.00')
    await page.screenshot({ path: `${SHOTS}/07-empty-export.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
