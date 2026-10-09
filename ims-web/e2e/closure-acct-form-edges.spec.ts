import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.use({ channel: 'chrome' })

const SHOTS = '/opt/cursor/artifacts/acct-236'

function shanghaiToday() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function addDays(iso: string, days: number) {
  const [year, month, day] = iso.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function poolRow(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill('AC-E2E-POOL')
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: 'AC-E2E-POOL' })
  await expect(row).toBeVisible()
  return row
}

test.describe('account form and timeline edge copy #236', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('checkout, recharge, and timeline stop on local edge rules', async ({ page }) => {
    test.setTimeout(90_000)
    await loginAdmin(page)
    await openDouyin(page)
    const row = await poolRow(page)

    await row.getByRole('button', { name: '领用' }).click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '发起账号领用' })
    await expect(checkout).toBeVisible()
    const today = shanghaiToday()
    await expect(checkout.getByTestId('acct-checkout-start')).toHaveValue(today)
    await expect(checkout.getByTestId('acct-checkout-end')).toHaveValue(addDays(today, 30))

    await checkout.getByTestId('acct-checkout-purpose').fill('')
    await checkout.getByRole('button', { name: '提交申请' }).click()
    await expect(checkout.getByTestId('acct-checkout-msg')).toContainText('用途说明必填')
    await page.screenshot({ path: `${SHOTS}/01-checkout-purpose.png`, fullPage: true })

    await checkout.getByTestId('acct-checkout-purpose').fill('用'.repeat(257))
    await checkout.getByRole('button', { name: '提交申请' }).click()
    await expect(checkout.getByTestId('acct-checkout-msg')).toContainText('用途说明不超过 256 字')

    await checkout.getByTestId('acct-checkout-purpose').fill('本地领用边界')
    await checkout.getByTestId('acct-checkout-end').fill(today)
    await checkout.getByRole('button', { name: '提交申请' }).click()
    await expect(checkout.getByTestId('acct-checkout-msg')).toContainText('计划结束须晚于计划开始')
    await page.screenshot({ path: `${SHOTS}/02-checkout-plan.png`, fullPage: true })
    await checkout.getByRole('button', { name: '取消' }).click()

    await row.getByRole('button', { name: '冲话费' }).click()
    const recharge = page.locator('.drawer.on').filter({ hasText: '登记冲话费' })
    await expect(recharge.getByTestId('acct-recharge-date')).toHaveValue(today)
    await expect(recharge.getByTestId('acct-recharge-date-note')).toContainText('北京时间')
    await recharge.getByTestId('acct-recharge-amount').fill('12.345')
    await recharge.getByRole('button', { name: '提交登记' }).click()
    await expect(recharge.getByTestId('acct-recharge-msg')).toContainText('金额最多两位小数')
    await page.screenshot({ path: `${SHOTS}/03-recharge-amount.png`, fullPage: true })

    await recharge.getByTestId('acct-recharge-amount').fill('12.50')
    await recharge.getByTestId('acct-recharge-date').evaluate((el, next) => {
      const input = el as HTMLInputElement
      input.value = next
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
    }, addDays(today, 1))
    await recharge.getByRole('button', { name: '提交登记' }).click()
    await expect(recharge.getByTestId('acct-recharge-msg')).toContainText('充值日期不得晚于今日')
    await expect(recharge).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/04-recharge-date.png`, fullPage: true })
    await recharge.getByRole('button', { name: '取消' }).click()

    await row.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    await page.getByTestId('acct-timeline-from').fill('2026-10-10')
    await page.getByTestId('acct-timeline-to').fill('2026-10-01')
    await expect(page.getByTestId('acct-timeline-range-hint')).toContainText('结束日期不能早于开始日期')
    await page.getByTestId('acct-timeline-export').click()
    await expect(page.getByTestId('acct-timeline-export-note')).toContainText('结束日期不能早于开始日期')
    await page.screenshot({ path: `${SHOTS}/05-timeline-order.png`, fullPage: true })
  })
})
