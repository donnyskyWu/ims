import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * #227 · 账实核对边角：平台消费格式、未来月份、高低方向、刚好 2.00%。
 * 不重做 #191 登记边界，也不重做 #210 昵称筛选。月份用时间戳错开，避免和 #64/#120 共用月份。
 */
const RECYCLE_NO = 'AC-E2E-RECYCLE'
const SHOTS = '/opt/cursor/artifacts/corp-227'

function pastMonths() {
  const offset = Math.floor(Date.now() / 1000) % 160
  const start = new Date(Date.UTC(2000, offset, 15))
  return [0, 1, 2, 3].map((step) => {
    const day = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + step, 15))
    const iso = day.toISOString()
    return { month: iso.slice(0, 7), day: iso.slice(0, 10) }
  })
}

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchRecycle(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(RECYCLE_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: RECYCLE_NO })
  await expect(row).toBeVisible()
  return row
}

async function openVerify(row: Locator) {
  await row.getByRole('button', { name: '账实核对' }).click()
  const drawer = row.page().locator('.drawer.on').filter({ hasText: '月度账实核对' })
  await expect(drawer).toBeVisible()
  return drawer
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

test.describe('CORP verify edge copy', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('platform scale, future month, side copy and exact 2.00% (#227)', async ({ page }) => {
    test.setTimeout(120_000)
    let verifyPosts = 0
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/account/recharge/verify')) verifyPosts += 1
    })

    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchRecycle(page)
    const drawer = await openVerify(row)
    await expect(drawer.getByTestId('acct-verify-rules')).toContainText('最多两位小数')
    await expect(drawer.getByTestId('acct-verify-rules')).toContainText('不能核对未来月份')
    await page.screenshot({ path: `${SHOTS}/01-verify-rules.png`, fullPage: true })

    await drawer.getByTestId('acct-verify-month').fill('2020-01')
    await drawer.getByTestId('acct-verify-platform').fill('1.239')
    await drawer.getByTestId('acct-verify-submit').click()
    await expect(drawer.getByTestId('acct-verify-msg')).toContainText('最多两位小数')
    await page.screenshot({ path: `${SHOTS}/02-platform-decimals.png`, fullPage: true })

    await drawer.getByTestId('acct-verify-platform').fill('abc')
    await drawer.getByTestId('acct-verify-submit').click()
    await expect(drawer.getByTestId('acct-verify-msg')).toContainText('格式不合法')

    await drawer.getByTestId('acct-verify-platform').fill('0')
    await drawer.getByTestId('acct-verify-submit').click()
    await expect(drawer.getByTestId('acct-verify-msg')).toContainText('须大于 0')

    await drawer.getByTestId('acct-verify-platform').fill('   ')
    await drawer.getByTestId('acct-verify-submit').click()
    await expect(drawer.getByTestId('acct-verify-msg')).toContainText('请填写平台实际消费')

    await drawer.getByTestId('acct-verify-month').fill('2099-12')
    await drawer.getByTestId('acct-verify-platform').fill('100')
    await drawer.getByTestId('acct-verify-submit').click()
    await expect(drawer.getByTestId('acct-verify-msg')).toContainText('不能核对未来月份')
    await expect(drawer.getByTestId('acct-verify-empty')).toHaveCount(0)
    expect(verifyPosts).toBe(0)
    await page.screenshot({ path: `${SHOTS}/03-future-month.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()

    const [higherPlatform, higherRecharge, equal, exact] = pastMonths()

    await registerRecharge(page, row, '100.00', higherPlatform.day)
    const higherDrawer = await openVerify(row)
    await higherDrawer.getByTestId('acct-verify-month').fill(higherPlatform.month)
    await higherDrawer.getByTestId('acct-verify-platform').fill('100.50')
    const higherResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/verify') && r.request().method() === 'POST',
    )
    await higherDrawer.getByTestId('acct-verify-submit').click()
    const higherBody = (await (await higherResp).json()) as { code: number; data?: { diffRateText?: string } }
    expect(higherBody.code).toBe(0)
    await expect(higherDrawer.getByTestId('acct-verify-side')).toHaveText('平台消费高于冲话费')
    await expect(higherDrawer.getByTestId('acct-verify-result')).toContainText('一致')
    await expect(higherDrawer.getByTestId('acct-verify-exact')).toHaveCount(0)
    await expect(higherDrawer.getByTestId('acct-verify-item')).toContainText(RECYCLE_NO)
    await expect(higherDrawer.getByTestId('acct-verify-item')).toContainText('100.50')
    await page.screenshot({ path: `${SHOTS}/04-platform-higher.png`, fullPage: true })
    await higherDrawer.getByRole('button', { name: '关闭' }).click()

    await registerRecharge(page, row, '101.00', higherRecharge.day)
    const rechargeDrawer = await openVerify(row)
    await rechargeDrawer.getByTestId('acct-verify-month').fill(higherRecharge.month)
    await rechargeDrawer.getByTestId('acct-verify-platform').fill('100')
    await rechargeDrawer.getByTestId('acct-verify-submit').click()
    await expect(rechargeDrawer.getByTestId('acct-verify-side')).toHaveText('冲话费高于平台消费')
    await expect(rechargeDrawer.getByTestId('acct-verify-result')).toContainText('一致')
    await rechargeDrawer.getByRole('button', { name: '关闭' }).click()

    await registerRecharge(page, row, '80.00', equal.day)
    const equalDrawer = await openVerify(row)
    await equalDrawer.getByTestId('acct-verify-month').fill(equal.month)
    await equalDrawer.getByTestId('acct-verify-platform').fill('80')
    await equalDrawer.getByTestId('acct-verify-submit').click()
    await expect(equalDrawer.getByTestId('acct-verify-side')).toHaveText('冲话费与平台消费一致')
    await expect(equalDrawer.getByTestId('acct-verify-item')).toContainText('0.00')
    await equalDrawer.getByRole('button', { name: '关闭' }).click()

    await registerRecharge(page, row, '102.00', exact.day)
    const exactDrawer = await openVerify(row)
    await exactDrawer.getByTestId('acct-verify-month').fill(exact.month)
    await exactDrawer.getByTestId('acct-verify-platform').fill('100')
    const exactResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/verify') && r.request().method() === 'POST',
    )
    await exactDrawer.getByTestId('acct-verify-submit').click()
    const exactBody = (await (await exactResp).json()) as { code: number; data?: { diffRateText?: string } }
    expect(exactBody.code).toBe(1026)
    expect(exactBody.data?.diffRateText).toBe('2.00%')
    await expect(exactDrawer.getByTestId('acct-verify-msg')).toContainText('1026')
    await expect(exactDrawer.getByTestId('acct-verify-exact')).toHaveText('刚好达到 2.00%，按超阈值处理')
    await expect(exactDrawer.getByTestId('acct-verify-side')).toHaveText('冲话费高于平台消费')
    await expect(exactDrawer.getByTestId('acct-verify-ticket')).toContainText('财务核查工单')
    await expect(exactDrawer.getByTestId('acct-verify-item')).toContainText('2.00')
    await page.screenshot({ path: `${SHOTS}/05-exact-200.png`, fullPage: true })
  })
})
