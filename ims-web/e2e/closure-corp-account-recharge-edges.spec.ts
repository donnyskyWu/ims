import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const POOL_NO = 'AC-E2E-POOL'
const REMARK = '本地备注191'
const SHOTS = '/opt/cursor/artifacts'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function poolRow(page: Page) {
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

async function openRegister(row: Locator) {
  await row.getByRole('button', { name: '冲话费' }).click()
  const drawer = row.page().locator('.drawer.on').filter({ hasText: '登记冲话费' })
  await expect(drawer).toBeVisible()
  return drawer
}

async function setDate(drawer: Locator, value: string) {
  await drawer.getByTestId('acct-recharge-date').evaluate((el, next) => {
    const input = el as HTMLInputElement
    input.value = next
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
  }, value)
}

test.describe('CORP recharge empty state and top-up edges', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('empty cost month, top-up edges, remark and detail stub (#191)', async ({ page }) => {
    await loginAdmin(page)
    await openDouyin(page)
    const day = Number(new Date().toISOString().slice(8, 10))
    const banner = page.getByTestId('acct-rc-r1')
    if (day >= 1 && day <= 5) await expect(banner).toContainText('请于 5 日前完成上月核对')
    else await expect(banner).toHaveCount(0)

    const row = await poolRow(page)
    const drawer = await openRegister(row)

    await drawer.getByTestId('acct-recharge-amount').fill('1.239')
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('金额最多两位小数')

    await drawer.getByTestId('acct-recharge-amount').fill('0')
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('金额格式不合法')

    await drawer.getByTestId('acct-recharge-amount').fill('12.50')
    await setDate(drawer, '2099-01-01')
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('充值日期不得晚于今日')

    await setDate(drawer, new Date().toISOString().slice(0, 10))
    await drawer.getByTestId('acct-recharge-remark').fill('备'.repeat(257))
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('备注过长')

    await drawer.getByTestId('acct-recharge-amount').fill('6000')
    await drawer.getByTestId('acct-recharge-voucher').fill('   ')
    await drawer.getByTestId('acct-recharge-remark').fill('')
    const blockedResp = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge') &&
        !r.url().includes('/list') &&
        !r.url().includes('/verify') &&
        !r.url().includes('/summary') &&
        r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const blocked = (await (await blockedResp).json()) as { code: number }
    expect(blocked.code).toBe(1025)
    await expect(drawer.getByTestId('acct-recharge-msg')).toContainText('1025')

    await drawer.getByTestId('acct-recharge-amount').fill('12.50')
    await drawer.getByTestId('acct-recharge-voucher').fill('')
    await drawer.getByTestId('acct-recharge-remark').fill(REMARK)
    const saved = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge') &&
        !r.url().includes('/list') &&
        !r.url().includes('/verify') &&
        !r.url().includes('/summary') &&
        r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const savedBody = (await (await saved).json()) as { code: number }
    expect(savedBody.code).toBe(0)
    await expect(drawer).toBeHidden()

    const list = page.getByTestId('acct-recharge-list')
    const savedRow = list.locator('[data-testid="acct-recharge-row"]').filter({ hasText: REMARK }).first()
    await expect(savedRow).toContainText('12.50')
    await expect(savedRow).toContainText('管理员')
    await expect(list.getByTestId('acct-recharge-empty')).toHaveCount(0)
    await expect(list.getByTestId('acct-recharge-total')).toContainText('共')

    await savedRow.getByTestId('acct-recharge-detail').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '核对详情' })
    await expect(detail.getByTestId('acct-recharge-platform-stub')).toContainText('平台消费额未在列表返回')
    await expect(detail).toContainText(REMARK)
    await detail.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/e2e-191-recharge-detail.png`, fullPage: true })
    await detail.getByRole('button', { name: '关闭' }).click()
    await expect(detail).toBeHidden()

    await savedRow.getByTestId('acct-recharge-voucher-view').click()
    const voucher = page.locator('.drawer.on').filter({ hasText: '核对详情' })
    await expect(voucher.getByTestId('acct-recharge-voucher-preview')).toHaveAttribute('data-focus', 'voucher')
    await expect(voucher.getByTestId('acct-recharge-voucher-preview')).toContainText('无凭证')
    await voucher.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('acct-summary-month').fill('2099-12')
    const summaryResp = page.waitForResponse(
      (r) => r.url().includes('/account/recharge/summary') && !r.url().includes('/export') && r.request().method() === 'GET',
    )
    await page.getByTestId('acct-summary-query').click()
    const summaryBody = (await (await summaryResp).json()) as { code: number }
    expect(summaryBody.code).toBe(0)
    const summary = page.getByTestId('acct-recharge-summary')
    await expect(summary.getByTestId('acct-summary-empty')).toHaveText('该月无冲话费记录')
    await expect(summary.getByTestId('acct-summary-totals')).toContainText('0 笔')
    await summary.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/e2e-191-summary-empty.png`, fullPage: true })
  })
})
