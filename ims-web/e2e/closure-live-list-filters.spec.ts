import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #206 · 纯 UI
 * 场次按账号/责任人筛选与空态、单侧日期提示、待录入责任人空态、告警时段与规则筛选空态。
 */
const shotDir = '/opt/cursor/artifacts/e2e-206-screenshots'
const SESSION = 'IMS20261008DYS0082'

fs.mkdirSync(shotDir, { recursive: true })

test.describe('live session and alarm list filter tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('account owner filters, date hint, pending owner, and alarm leftovers', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })

    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    const listed = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.url().includes(SESSION) && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    const listedBody = (await (await listed).json()) as {
      data?: { list?: Array<{ sessionCode?: string; accountId?: number; responsibleUserId?: number }> }
    }
    const row = listedBody.data?.list?.[0]
    expect(row?.sessionCode).toBe(SESSION)
    expect(row?.accountId).toBeTruthy()
    expect(row?.responsibleUserId).toBeTruthy()

    await page.getByTestId('live-filter-account').fill(String(row?.accountId))
    await page.getByTestId('live-filter-owner').fill(String(row?.responsibleUserId))
    const hit = page.waitForResponse((r) => {
      const url = r.url()
      return (
        url.includes('/live/sessions/list') &&
        url.includes(`accountId=${row?.accountId}`) &&
        url.includes(`responsibleUserId=${row?.responsibleUserId}`) &&
        r.status() === 200
      )
    })
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await hit
    await expect(page.locator('tbody tr', { hasText: SESSION })).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/01-account-owner-hit.png`, fullPage: true })

    await page.getByTestId('live-filter-account').fill('999999991')
    const miss = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.url().includes('accountId=999999991') && r.status() === 200,
    )
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await miss
    await expect(page.getByTestId('live-sessions-empty')).toContainText('暂无场次')
    await expect(page.getByTestId('live-sessions-empty-hint')).toContainText('没有符合当前账号、责任人或筛选条件的场次')
    await page.screenshot({ path: `${shotDir}/02-filter-miss.png`, fullPage: true })

    const reset = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '重置' }).click()
    await reset
    await page.getByTestId('live-filter-from').fill('2026-10-01')
    const oneSided = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    const oneSidedUrl = (await oneSided).url()
    expect(oneSidedUrl.includes('timeRange=')).toBe(false)
    await expect(page.getByTestId('live-filter-date-hint')).toContainText('开播起止要一起选')
    await page.screenshot({ path: `${shotDir}/03-date-one-side.png`, fullPage: true })

    const opened = page.waitForResponse(
      (r) => r.url().includes('/live/report/pending') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-view-pending').click()
    await opened
    await page.getByTestId('live-pending-owner').fill('999999991')
    const pending = page.waitForResponse(
      (r) =>
        r.url().includes('/live/report/pending') &&
        r.url().includes('responsibleUserId=999999991') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('live-pending-query').click()
    const pendingRes = await pending
    expect(pendingRes.status()).toBe(200)
    await expect(page.getByTestId('live-pending-empty')).toContainText('该责任人暂无待录入')
    await page.screenshot({ path: `${shotDir}/04-pending-owner-empty.png`, fullPage: true })

    const initialRules = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/rules') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警', { timeout: 15_000 })
    await initialRules
    await page.getByTestId('live-rule-keyword').fill('不存在的规则名-206')
    await page.getByTestId('live-rule-type').selectOption('EVENT')
    const rules = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/rules') && r.url().includes('ruleType=EVENT') && r.status() === 200,
    )
    await page.getByTestId('live-rule-query').click()
    const rulesBody = (await (await rules).json()) as { code: number; data?: { list?: unknown[] } }
    expect(rulesBody.code).toBe(0)
    expect(rulesBody.data?.list || []).toEqual([])
    await expect(page.getByTestId('live-rule-empty')).toContainText('没有符合条件的规则')
    await page.screenshot({ path: `${shotDir}/05-rule-filter-empty.png`, fullPage: true })

    await page.getByTestId('live-alarm-tab-records').click()
    await page.getByTestId('live-alarm-from').fill('1999-01-01')
    await expect(page.getByTestId('live-alarm-date-hint')).toContainText('告警起止要一起选')
    await page.getByTestId('live-alarm-to').fill('1999-01-02')
    const alarms = page.waitForResponse((r) => {
      const url = r.url()
      return url.includes('/live/alarm/records') && url.includes('timeRange=1999-01-01') && url.includes('timeRange=1999-01-02') && r.status() === 200
    })
    await page.getByTestId('live-alarm-query').click()
    const alarmBody = (await (await alarms).json()) as { code: number; data?: { list?: unknown[] } }
    expect(alarmBody.code).toBe(0)
    expect(alarmBody.data?.list || []).toEqual([])
    await expect(page.getByTestId('live-alarm-empty')).toContainText('该时段暂无风险告警')
    await page.screenshot({ path: `${shotDir}/06-alarm-time-empty.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
