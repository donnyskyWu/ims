import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * #173 · 核对后继续编辑，以及空月份核对空态、非管理员解锁被拦住。
 * 纯 UI。月份 2026-01 / 2019-07，避开 #64/#70/#120 用过的月份。
 */
const TAIL_NO = 'AC-E2E-TAIL'
const FINANCE_USER = 'e2e_acct_r3'
const EMPTY_MONTH = '2019-07'
const EDIT_MONTH = '2026-01'
const AMOUNT = '73.41'
const CORRECTED = '73.99'
const SHOTS = '/opt/cursor/artifacts/e2e-173-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchTail(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(TAIL_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: TAIL_NO })
  await expect(row).toBeVisible()
  return row
}

function tailRecord(page: Page, amount: string) {
  return page.getByTestId('acct-recharge-row').filter({ hasText: TAIL_NO }).filter({ hasText: amount }).first()
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
  const body = (await (await resp).json()) as { code: number; msg?: string; data?: { verifyStatus?: string } }
  return { drawer, body }
}

test.describe('CORP reconcile unlock tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('empty reconcile month, finance cannot unlock, admin continues into edit (#173)', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchTail(page)

    const empty = await verifyMonth(page, row, EMPTY_MONTH, '100')
    expect(empty.body.code).toBe(1001)
    expect(empty.body.msg || '').toContain('该月无冲话费记录')
    await expect(empty.drawer.getByTestId('acct-verify-empty')).toBeVisible()
    await expect(empty.drawer.getByTestId('acct-verify-msg')).toContainText('该月无冲话费记录')
    await expect(empty.drawer.getByTestId('acct-verify-empty')).toContainText('请先登记该月冲话费')
    await expect(empty.drawer.getByTestId('acct-verify-result')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/01-verify-empty.png`, fullPage: true })
    await empty.drawer.getByRole('button', { name: '关闭' }).click()
    await expect(empty.drawer).toBeHidden()

    await registerRecharge(page, row, AMOUNT, `${EDIT_MONTH}-20`)
    const created = tailRecord(page, AMOUNT)
    await expect(created).toContainText('未核对')
    const passed = await verifyMonth(page, row, EDIT_MONTH, AMOUNT)
    expect(passed.body.code).toBe(0)
    expect(passed.body.data?.verifyStatus).toBe('MATCHED')
    await expect(passed.drawer.getByTestId('acct-verify-result')).toContainText('一致')
    await expect(passed.drawer.getByTestId('acct-verify-empty')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/02-verified-matched.png`, fullPage: true })
    await passed.drawer.getByRole('button', { name: '关闭' }).click()

    await loginAs(page, FINANCE_USER)
    await openDouyin(page)
    const locked = tailRecord(page, AMOUNT)
    await expect(locked).toContainText('一致')
    await locked.getByTestId('acct-recharge-unlock').click()
    const blockedDrawer = page.locator('.drawer.on').filter({ hasText: '解锁已核对记录' })
    await expect(blockedDrawer.getByTestId('acct-unlock-status')).toContainText('一致')
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/unlock') && r.request().method() === 'POST',
    )
    await blockedDrawer.getByTestId('acct-unlock-submit').click()
    const blockedBody = (await (await blockedResp).json()) as { code: number; msg?: string }
    expect(blockedBody.code).toBe(1008)
    await expect(blockedDrawer.getByTestId('acct-unlock-blocked')).toContainText('仅管理员')
    await expect(blockedDrawer.getByTestId('acct-unlock-edit')).toHaveCount(0)
    await expect(blockedDrawer.getByTestId('acct-unlock-status')).toContainText('一致')
    await page.screenshot({ path: `${SHOTS}/03-finance-unlock-blocked.png`, fullPage: true })
    await blockedDrawer.getByRole('button', { name: '关闭' }).click()

    await loginAdmin(page)
    await openDouyin(page)
    const stillLocked = tailRecord(page, AMOUNT)
    await stillLocked.getByTestId('acct-recharge-unlock').click()
    const unlockDrawer = page.locator('.drawer.on').filter({ hasText: '解锁已核对记录' })
    const unlockResp = page.waitForResponse(
      (r) => r.url().includes('/unlock') && r.request().method() === 'POST',
    )
    await unlockDrawer.getByTestId('acct-unlock-submit').click()
    const unlockBody = (await (await unlockResp).json()) as { code: number; data?: { verifyStatus?: string } }
    expect(unlockBody.code).toBe(0)
    expect(unlockBody.data?.verifyStatus).toBe('UNVERIFIED')
    await expect(unlockDrawer.getByTestId('acct-unlock-msg')).toContainText('已解锁')
    await expect(unlockDrawer.getByTestId('acct-unlock-status')).toContainText('未核对')
    await expect(unlockDrawer.getByTestId('acct-unlock-edit')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/04-unlocked-continue.png`, fullPage: true })

    await unlockDrawer.getByTestId('acct-unlock-edit').click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑冲话费' })
    await expect(editDrawer).toBeVisible()
    await expect(editDrawer.getByTestId('acct-recharge-amount')).toHaveValue(AMOUNT)
    await editDrawer.getByTestId('acct-recharge-amount').fill(CORRECTED)
    const editResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/') && r.request().method() === 'PUT',
    )
    await editDrawer.getByRole('button', { name: '保存更正' }).click()
    const editBody = (await (await editResp).json()) as { code: number }
    expect(editBody.code).toBe(0)
    await expect(editDrawer).toBeHidden()

    const corrected = tailRecord(page, CORRECTED)
    await expect(corrected).toContainText('未核对')
    await expect(corrected.getByTestId('acct-recharge-edit')).toBeVisible()
    await expect(corrected.getByTestId('acct-recharge-unlock')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/05-edited-after-unlock.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
