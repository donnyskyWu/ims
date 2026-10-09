import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

/**
 * #239 · 空表导出、慢查询提示、下播负数红框、更正原因空态、规则名与告警处置刷新。
 * 不重做 #180 补录空态、#197 风控空清单、#206 筛选，也不重做 #219 的 UV/起止/严重横幅。
 */
const shotDir = '/opt/cursor/artifacts/live-239'

fs.mkdirSync(shotDir, { recursive: true })

async function fillStable(page: Page, testId: string, value: string) {
  const field = page.getByTestId(testId)
  const deadline = Date.now() + 4_000
  let last = ''
  while (Date.now() < deadline) {
    await field.fill(value)
    await page.waitForTimeout(200)
    last = await field.inputValue()
    if (last === value) return
  }
  throw new Error(`${testId} 未保持为 ${value}，当前 ${last}`)
}

test.describe('live local empty and edge copy', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty export and slow session query', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })

    await page.locator('input[placeholder="场次 ID"]').fill('IMS19990101DYS0000')
    const emptyList = page.waitForResponse(
      (r) =>
        r.url().includes('/live/sessions/list') &&
        r.url().includes('sessionCode=IMS19990101DYS0000') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const emptyBody = (await (await emptyList).json()) as { code: number; data?: { total?: number } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.total).toBe(0)
    await expect(page.locator('.pg-total')).toHaveText('共 0 条')

    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-ledger-export').click()
    const exportBody = (await (await exportResp).json()) as { code: number; data?: { message?: string } }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.message).toBe('当前筛选没有场次，已导出空表（仅表头）')
    await expect(page.getByTestId('live-export-note')).toHaveText('当前筛选没有场次，已导出空表（仅表头）')
    await page.screenshot({ path: `${shotDir}/01-empty-export.png`, fullPage: true })

    await page.route('**/live/sessions/list**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 3200))
      await route.continue()
    })
    const slowList = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '重置' }).click()
    await slowList
    await expect(page.getByTestId('live-slow-query')).toHaveText('查询超过 3 秒，请缩小开播日期区间后再查。')
    await page.screenshot({ path: `${shotDir}/02-slow-query.png`, fullPage: true })
    await page.unroute('**/live/sessions/list**')
    expect(pageErrors).toEqual([])
  })

  test('negative refund and blank correction reason', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)

    await page.goto('/ims/live/sessions')
    await page.getByRole('button', { name: '新建场次登记' }).click()
    const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
    await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
    await drawer.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
    await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
    await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(`E2E 239 ${Date.now()}`)
    const regResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const regBody = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(regBody.code).toBe(0)
    const sessionCode = regBody.data?.sessionCode || ''
    expect(sessionCode).toMatch(/^IMS\d{8}[A-Z]{3}\d{4}$/)

    const detail = page.locator('.drawer').filter({ hasText: sessionCode })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    const reportLoad = page.waitForResponse(
      (r) => r.url().includes(`/live/report/${sessionCode}`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await reportLoad
    await fillStable(page, 'live-report-refund', '-1')
    const negativeResp = page.waitForResponse(
      (r) => r.url().includes(`/live/report/${sessionCode}`) && r.request().method() === 'POST' && r.status() === 200,
    )
    await detail.getByTestId('live-report-submit').click()
    const negativeBody = (await (await negativeResp).json()) as { code: number; data?: { field?: string } }
    expect(negativeBody.code).toBe(1001)
    expect(negativeBody.data?.field).toBe('refundAmount')
    await expect(detail.getByTestId('live-report-error')).toContainText('数值不能为负（退款）')
    await expect(detail.getByTestId('live-report-refund')).toHaveCSS('border-color', 'rgb(255, 59, 48)')
    await page.screenshot({ path: `${shotDir}/03-negative-refund.png`, fullPage: true })

    await fillStable(page, 'live-report-refund', '0')
    const submitResp = page.waitForResponse(
      (r) => r.url().includes(`/live/report/${sessionCode}`) && r.request().method() === 'POST' && r.status() === 200,
    )
    await detail.getByTestId('live-report-submit').click()
    expect(((await (await submitResp).json()) as { code: number }).code).toBe(0)
    await detail.getByTestId('live-report-confirm').click()
    await expect(detail.getByTestId('live-report-headline')).toContainText('CONFIRMED')
    await detail.getByTestId('live-report-correction-open').click()
    await expect(detail.getByTestId('live-correction-reason-hint')).toContainText('更正原因必填')
    await detail.getByTestId('live-report-correction-submit').click()
    await expect(detail.getByTestId('live-report-error')).toContainText('更正原因必填')
    await expect(detail.getByTestId('live-report-correction-reason')).toHaveAttribute('data-missing', '1')
    await page.screenshot({ path: `${shotDir}/04-correction-reason.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('rule name, stats retry, and handled refresh', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警', { timeout: 15_000 })

    await page.getByTestId('live-alarm-rule-open').click()
    const ruleDrawer = page.getByTestId('live-alarm-rule-drawer')
    await expect(ruleDrawer).toBeVisible()
    await ruleDrawer.getByTestId('live-alarm-rule-save').click()
    await expect(ruleDrawer.getByTestId('live-alarm-rule-error')).toHaveText('规则名必填')
    await expect(ruleDrawer.getByTestId('live-alarm-rule-name')).toHaveCSS('border-color', 'rgb(255, 59, 48)')
    await page.screenshot({ path: `${shotDir}/05-rule-name.png`, fullPage: true })
    await ruleDrawer.getByRole('button', { name: '关闭' }).click()

    await page.route('**/live/alarm/stats**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 5005, msg: '统计暂不可用', data: null }),
      })
    })
    await page.getByTestId('live-alarm-tab-stats').click()
    await expect(page.getByTestId('live-alarm-stats-missing')).toContainText('统计没有加载出来')
    await expect(page.getByTestId('live-alarm-stats-retry')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/06-stats-retry.png`, fullPage: true })
    await page.unroute('**/live/alarm/stats**')
    const statsResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/stats') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('live-alarm-stats-retry').click()
    const statsBody = (await (await statsResp).json()) as { code: number }
    expect(statsBody.code).toBe(0)
    await expect(page.getByTestId('live-alarm-stats-l1')).toBeVisible()

    await page.route('**/live/alarm/record/**/handle', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1001, msg: '告警已处置，请刷新', data: null }),
      })
    })
    await page.getByTestId('live-alarm-tab-records').click()
    const recordsResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('live-alarm-query').click()
    await recordsResp
    await page.getByTestId('live-alarm-handle').first().click()
    const handleDrawer = page.getByTestId('live-alarm-handle-drawer')
    await handleDrawer.getByTestId('live-alarm-handle-submit').click()
    await expect(handleDrawer.getByTestId('live-alarm-handle-error')).toContainText('告警已处置，请刷新')
    await expect(handleDrawer.getByTestId('live-alarm-handle-refresh')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/07-handle-refresh.png`, fullPage: true })
    await handleDrawer.getByTestId('live-alarm-handle-refresh').click()
    await expect(handleDrawer).toBeHidden()
    await page.unroute('**/live/alarm/record/**/handle')
    expect(pageErrors).toEqual([])
  })
})
