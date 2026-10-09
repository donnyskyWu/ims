import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.use({ channel: 'chrome' })

const SHOTS = '/opt/cursor/artifacts/e2e-185-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
  await expect(page.getByTestId('acct-pool-event-type')).toBeVisible()
}

test.describe('account timeline type filter and empty states #185', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('pool and detail timelines explain a type with no events', async ({ page }) => {
    test.setTimeout(90_000)
    await loginAdmin(page)
    await openDouyin(page)

    const poolFiltered = page.waitForResponse(
      (r) =>
        r.url().includes('/account/timeline/events') &&
        r.url().includes('eventType=CANCEL') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('acct-pool-event-type').selectOption('CANCEL')
    const poolBody = (await (await poolFiltered).json()) as { code: number; data?: { list?: unknown[] } }
    expect(poolBody.code).toBe(0)
    if ((poolBody.data?.list || []).length === 0) {
      await expect(page.getByTestId('acct-pool-event-empty')).toContainText('当前没有「注销」动态')
    } else {
      await expect(page.getByTestId('acct-pool-event').first()).toContainText('注销')
    }
    await page.screenshot({ path: `${SHOTS}/01-pool-type-empty.png`, fullPage: true })

    await page.locator('input[placeholder="账号编号/昵称"]').fill('AC-E2E-POOL')
    const searchResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await searchResp
    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: 'AC-E2E-POOL' })
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    await expect(page.getByTestId('acct-timeline-type')).toBeVisible()

    const detailFiltered = page.waitForResponse(
      (r) =>
        r.url().includes('/account/timeline/') &&
        r.url().includes('eventTypes=CANCEL') &&
        !r.url().includes('/export') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-timeline-type').selectOption('CANCEL')
    const detailRes = await detailFiltered
    expect(detailRes.status()).toBe(200)
    const detailBody = (await detailRes.json()) as { code: number; data?: { list?: { eventType: string }[] } }
    expect(detailBody.code).toBe(0)
    const detailRows = detailBody.data?.list || []
    expect(detailRows.every((item) => item.eventType === 'CANCEL')).toBeTruthy()
    if (!detailRows.length) {
      await expect(page.getByTestId('acct-timeline-empty')).toContainText('当前没有「注销」事件')
    }
    await page.screenshot({ path: `${SHOTS}/02-timeline-type-empty.png`, fullPage: true })

    await page.getByTestId('acct-timeline-from').fill('2026-01-01')
    await expect(page.getByTestId('acct-timeline-range-hint')).toContainText('请同时填写开始和结束日期')
    await page.screenshot({ path: `${SHOTS}/03-timeline-partial-range.png`, fullPage: true })

    const ranged = page.waitForResponse(
      (r) =>
        r.url().includes('/account/timeline/') &&
        r.url().includes('timeRange=') &&
        r.url().includes('eventTypes=CANCEL') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-timeline-to').fill('2026-01-02')
    const rangedRes = await ranged
    expect(rangedRes.status()).toBe(200)
    const rangedBody = (await rangedRes.json()) as { code: number; data?: { list?: unknown[] } }
    expect(rangedBody.code).toBe(0)
    if (!(rangedBody.data?.list || []).length) {
      await expect(page.getByTestId('acct-timeline-empty')).toContainText('当前没有「注销」事件')
    }
    await page.screenshot({ path: `${SHOTS}/04-timeline-range-empty.png`, fullPage: true })
  })
})
