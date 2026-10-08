import { test, expect } from '@playwright/test'
import { loginAdmin, loginAs } from './closure-helpers'

const POOL_NO = 'AC-E2E-POOL'
const VOUCHER = 'RC-E2E-VOUCHER-58'
const FINANCE_USER = 'e2e_acct_r3'

test.describe('CORP account recharge voucher gate S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('E2E-S4-05/06 recharge under 5000, 1025 without voucher, finance-only voucher (#58)', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/account/douyin')
    await expect(page.locator('h1')).toContainText('抖音')

    await page.locator('input[placeholder="账号编号/昵称"]').fill(POOL_NO)
    const searchResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await searchResp

    const row = page.locator('.tbl-block').first().locator('tbody tr').filter({ hasText: POOL_NO })
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: '冲话费' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '登记冲话费' })
    await expect(drawer).toBeVisible()

    await drawer.getByTestId('acct-recharge-amount').fill('1000')
    await drawer.getByTestId('acct-recharge-voucher').fill('')
    const smallResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const smallBody = (await (await smallResp).json()) as { code: number }
    expect(smallBody.code).toBe(0)
    const list = page.getByTestId('acct-recharge-list')
    await expect(list).toContainText('1000.00')
    await expect(list).toContainText(POOL_NO)

    await row.getByRole('button', { name: '冲话费' }).click()
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('acct-recharge-amount').fill('6000')
    await drawer.getByTestId('acct-recharge-voucher').fill('')
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const blockedBody = (await (await blockedResp).json()) as { code: number }
    expect(blockedBody.code).toBe(1025)
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('1025')

    await drawer.getByTestId('acct-recharge-voucher').fill(VOUCHER)
    const paidResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const paidBody = (await (await paidResp).json()) as { code: number }
    expect(paidBody.code).toBe(0)
    await expect(list).toContainText('6000.00')
    await expect(list).toContainText('仅财务可见')
    await expect(list).not.toContainText(VOUCHER)

    await loginAs(page, FINANCE_USER)
    const finList = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/corp/account/douyin')
    await finList
    await expect(page.getByTestId('acct-recharge-list')).toContainText(VOUCHER)
    await expect(page.getByTestId('acct-recharge-list')).toContainText('6000.00')
  })
})
