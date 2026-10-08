import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const RECON_NO = 'AC-E2E-RECON'
const SHOTS = '/opt/cursor/artifacts/e2e-64-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchRecon(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(RECON_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: RECON_NO })
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
    (r) => r.url().includes('/account/recharge') && !r.url().includes('/list') && !r.url().includes('/verify') && r.request().method() === 'POST',
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

async function verifyMonth(page: Page, row: Locator, month: string, platform: string) {
  await row.getByRole('button', { name: '账实核对' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '月度账实核对' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-verify-month').fill(month)
  await drawer.getByTestId('acct-verify-platform').fill(platform)
  const resp = page.waitForResponse(
    (r) => r.url().includes('/account/recharge/verify') && r.request().method() === 'POST',
  )
  await drawer.getByTestId('acct-verify-submit').click()
  const body = (await (await resp).json()) as { code: number; msg?: string; data?: { diffRateText?: string } }
  return { drawer, body }
}

test.describe('CORP account recharge reconcile S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('E2E-S4-07 reconcile 1.99% pass and 2.00% returns 1026 (#64)', async ({ page }) => {
    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchRecon(page)

    await registerRecharge(page, row, '101.99', '2026-09-15')
    await expect(page.getByTestId('acct-recharge-list')).toContainText('101.99')
    await page.screenshot({ path: `${SHOTS}/01-recharge-10199.png`, fullPage: true })

    const passed = await verifyMonth(page, row, '2026-09', '100')
    expect(passed.body.code).toBe(0)
    expect(passed.body.data?.diffRateText).toBe('1.99%')
    await expect(passed.drawer.getByTestId('acct-verify-rate')).toContainText('1.99%')
    await expect(passed.drawer.getByTestId('acct-verify-result')).toContainText('一致')
    await expect(passed.drawer.getByTestId('acct-verify-msg')).not.toContainText('1026')
    await page.screenshot({ path: `${SHOTS}/02-verify-1.99-pass.png`, fullPage: true })
    await passed.drawer.getByRole('button', { name: '关闭' }).click()
    await expect(passed.drawer).toBeHidden()

    await registerRecharge(page, row, '102', '2026-08-15')
    const over = await verifyMonth(page, row, '2026-08', '100')
    expect(over.body.code).toBe(1026)
    expect(over.body.data?.diffRateText).toBe('2.00%')
    await expect(over.drawer.getByTestId('acct-verify-msg')).toContainText('1026')
    await expect(over.drawer.getByTestId('acct-verify-rate')).toContainText('2.00%')
    await expect(over.drawer.getByTestId('acct-verify-result')).toContainText('差异')
    await expect(over.drawer.getByTestId('acct-verify-ticket')).toContainText('财务核查工单')
    await page.screenshot({ path: `${SHOTS}/03-verify-2.00-1026.png`, fullPage: true })
    await over.drawer.getByRole('button', { name: '关闭' }).click()

    const list = page.getByTestId('acct-recharge-list')
    await expect(list).toContainText('101.99')
    await expect(list).toContainText('一致')
    await expect(list).toContainText('102.00')
    await expect(list).toContainText('差异')
    await page.screenshot({ path: `${SHOTS}/04-recharge-verify-status.png`, fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.locator('body')).toContainText('账实核对 2.00%（1026）')
    await page.screenshot({ path: `${SHOTS}/05-workbench-1026.png`, fullPage: true })
  })
})
