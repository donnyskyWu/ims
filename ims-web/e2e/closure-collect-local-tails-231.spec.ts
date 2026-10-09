import path from 'node:path'
import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'LOG231-COOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/collect-local-tails-231'

test.describe('采集日志空态与 Cookie/引擎说明', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('筛选空态、健康说明，以及 Cookie 失效日志的本地说明', async ({ page }) => {
    test.setTimeout(120_000)
    const stamp = Date.now().toString(36)
    const name = `E2E日志边角${stamp}`
    await loginAdmin(page)

    await page.goto('/ims/collect/log')
    await expect(page.locator('h1')).toHaveText('采集日志')
    await expect(page.getByTestId('collect-health-note')).toContainText('本地')
    await expect(page.getByTestId('collect-failure-note')).toContainText('Cookie')
    await page.screenshot({ path: path.join(SHOTS, '01-health-notes.png'), fullPage: true })

    await page.getByTestId('log-status').selectOption('COOKIE_EXPIRED')
    await page.getByTestId('log-date-from').fill('2099-12-31')
    const cookieEmpty = page.waitForResponse(
      (r) => r.url().includes('/collect/log/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    expect(((await (await cookieEmpty).json()) as { data?: { total?: number } }).data?.total).toBe(0)
    await expect(page.getByTestId('log-empty')).toContainText('没有 Cookie 已失效的日志')
    await expect(page.getByTestId('log-empty-hint')).toContainText('本地 Collector')
    await expect(page.getByTestId('log-empty-hint')).toContainText('账号采集 Tab')
    await page.screenshot({ path: path.join(SHOTS, '02-cookie-filter-empty.png'), fullPage: true })

    await page.getByTestId('log-status').selectOption('ENGINE_UNAVAILABLE')
    const engineEmpty = page.waitForResponse(
      (r) => r.url().includes('/collect/log/page') && r.url().includes('ENGINE_UNAVAILABLE') && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await engineEmpty
    await expect(page.getByTestId('log-empty')).toContainText('没有浏览器引擎不可用的日志')
    await expect(page.getByTestId('log-empty-hint')).toContainText('真实浏览器')
    await page.screenshot({ path: path.join(SHOTS, '03-engine-filter-empty.png'), fullPage: true })

    await page.getByTestId('log-status').selectOption('')
    await page.getByTestId('log-date-from').fill('2099-02-02')
    await page.getByTestId('log-date-to').fill('2099-01-01')
    const inverted = page.waitForResponse(
      (r) => r.url().includes('/collect/log/page') && r.url().includes('dateTo') && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await inverted
    await expect(page.getByTestId('log-empty')).toContainText('没有符合筛选的日志')
    await expect(page.getByTestId('log-empty-hint')).toContainText('开始日期晚于结束日期')
    await page.screenshot({ path: path.join(SHOTS, '04-date-order-empty.png'), fullPage: true })

    await page.getByRole('button', { name: '手工补录' }).click()
    await expect(page.getByTestId('log-manual-note')).toContainText('不调用 Collector')
    await expect(page.getByTestId('log-manual-note')).toContainText('浏览器引擎')
    await page.screenshot({ path: path.join(SHOTS, '05-manual-fill-note.png'), fullPage: true })

    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')
    await page.getByTestId('dy-nickname').fill(name)
    await page.getByTestId('dy-company').selectOption({ label: 'E2E抖音采集公司' })
    await page.getByTestId('dy-ip-group').selectOption({ label: 'E2E抖音采集组' })
    await page.getByTestId('dy-platform-id').fill(`DY_COOKIE_EXPIRED_${stamp}`)
    await page.getByTestId('dy-credential').fill(SECRET)
    await page.getByTestId('dy-save').click()
    await expect(page.getByTestId('dy-notice')).toContainText('已保存')
    await expect(page.locator('body')).not.toContainText(SECRET)

    const row = page.locator(`[data-testid="dy-row-DY_COOKIE_EXPIRED_${stamp}"]`)
    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    const runResp = page.waitForResponse(
      (r) => r.url().includes('/collect/douyin/account/') && r.url().endsWith('/run') && r.request().method() === 'POST',
    )
    await row.getByRole('button', { name: '立即采集' }).click()
    const runBody = (await (await runResp).json()) as { code: number; data?: { status?: string } }
    expect(runBody.code).toBe(0)
    expect(runBody.data?.status).toBe('COOKIE_EXPIRED')
    await expect(page.locator('body')).not.toContainText(SECRET)

    await page.goto('/ims/collect/log')
    await page.getByTestId('log-status').selectOption('COOKIE_EXPIRED')
    await page.getByTestId('log-date-from').fill('')
    await page.getByTestId('log-date-to').fill('')
    const listed = page.waitForResponse(
      (r) => r.url().includes('/collect/log/page') && r.url().includes('COOKIE_EXPIRED') && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listed
    const logRow = page.locator('tbody tr', { hasText: name })
    await expect(logRow).toHaveCount(1)
    await expect(logRow.getByTestId('log-row-note')).toContainText('未连接真实平台')
    await logRow.getByRole('button', { name: '详情' }).click()
    await expect(page.getByTestId('log-detail-note')).toContainText('账号采集 Tab')
    await expect(page.getByTestId('log-repair')).toBeVisible()
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: path.join(SHOTS, '06-cookie-log-note.png'), fullPage: true })

    await page.getByTestId('log-repair').click()
    await expect(page).toHaveURL(/\/ims\/corp\/account\/douyin/)
    await expect(page).toHaveURL(/tab=collect/)
  })
})
