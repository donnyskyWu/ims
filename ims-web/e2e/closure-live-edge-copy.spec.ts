import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

/**
 * #219 · 下播 UV/时长与冲话费提示、待录入起止、告警空态与处置说明。
 * 不覆盖 #206 列表筛选，也不覆盖 #197 风控空清单与零分母。
 */
const shotDir = '/opt/cursor/artifacts/live-219'

fs.mkdirSync(shotDir, { recursive: true })

async function registerSession(page: Page, topic: string) {
  const ids = await resolveLiveFinRegisterIdsViaUi(page)
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  await page.getByRole('button', { name: '新建场次登记' }).click()
  const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
  await expect(drawer).toBeVisible()
  await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
  await drawer.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
  await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
  await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(topic)
  const regResp = page.waitForResponse(
    (r) => r.url().includes('/live/register') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const regBody = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
  expect(regBody.code).toBe(0)
  const sessionCode = regBody.data?.sessionCode
  expect(sessionCode).toBeTruthy()
  const detail = page.locator('.drawer').filter({ hasText: '场次' })
  await expect(detail).toBeVisible({ timeout: 15_000 })
  return { detail, sessionCode: sessionCode! }
}

test.describe('live report alarm pending edge copy', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('derived copy, pending range, and alarm edges', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.route(/\/live\/alarm\/records/, (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{"msg":"告警列表失败"}' }),
    )
    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警', { timeout: 15_000 })
    await expect(page.getByTestId('live-alarm-retry')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/01-alarm-load-error.png`, fullPage: true })
    await page.unroute(/\/live\/alarm\/records/)
    await page.getByTestId('live-alarm-retry').click()
    await page.getByTestId('live-alarm-tab-records').click()
    await expect(page.getByTestId('live-alarm-severe-banner')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('live-alarm-unhandled-badge')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-alarm-severe-banner.png`, fullPage: true })

    await page.getByTestId('live-alarm-session').fill('NONE-219')
    await page.getByTestId('live-alarm-query').click()
    await expect(page.getByTestId('live-alarm-empty')).toContainText('没有符合当前场次、级别或处置状态的告警')
    await page.screenshot({ path: `${shotDir}/03-alarm-empty.png`, fullPage: true })

    await page.getByTestId('live-alarm-session').fill('')
    await page.getByTestId('live-alarm-query').click()
    await page.getByTestId('live-alarm-handle').first().click()
    await expect(page.getByTestId('live-alarm-remark-hint')).toHaveText('已处理请附结果说明。')
    await page.getByTestId('live-alarm-handle-status').selectOption('FALSE_ALARM')
    await expect(page.getByTestId('live-alarm-remark-hint')).toHaveText('误报请写明依据。')
    await page.screenshot({ path: `${shotDir}/04-alarm-remark.png`, fullPage: true })
    await page.locator('.drawer').filter({ hasText: '处置告警' }).getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('live-alarm-tab-rules').click()
    await page.getByTestId('live-alarm-rule-open').click()
    const ruleDrawer = page.getByTestId('live-alarm-rule-drawer')
    await ruleDrawer.getByTestId('live-alarm-rule-name').fill(`窗口非法 ${Date.now()}`)
    await ruleDrawer.getByTestId('live-alarm-rule-window').fill('0')
    await ruleDrawer.getByTestId('live-alarm-rule-save').click()
    await expect(page.getByTestId('live-alarm-rule-error')).toContainText('1009')
    await expect(page.getByTestId('live-alarm-rule-window')).toHaveCSS('border-color', 'rgb(255, 59, 48)')
    await page.screenshot({ path: `${shotDir}/05-alarm-window-1009.png`, fullPage: true })

    const topic = `E2E 边角 ${Date.now()}`
    const { detail, sessionCode } = await registerSession(page, topic)
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(detail.getByTestId('live-report-uv')).toHaveText('2.00')
    await expect(detail.getByTestId('live-report-duration')).toHaveText('120 分钟')
    await expect(detail.getByTestId('live-ad-cost-hint')).toContainText('冲话费')
    await detail.getByTestId('live-report-viewers').fill('0')
    await expect(detail.getByTestId('live-report-uv')).toHaveText('—')
    await detail.getByTestId('live-report-end').fill('2026-10-06T19:00:00+08:00')
    await expect(detail.getByTestId('live-report-duration')).toContainText('—')
    await page.screenshot({ path: `${shotDir}/06-report-derived.png`, fullPage: true })

    await detail.locator('.tab', { hasText: '关联' }).click()
    await expect(detail.getByTestId('live-related-alarm-empty')).toContainText('本场次还没有风险命中')
    await page.screenshot({ path: `${shotDir}/07-related-empty.png`, fullPage: true })

    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await detail.getByTestId('live-start-btn').click()
    await expect(page.getByText('已确认开播')).toBeVisible()
    await page.locator('.drawer.on .dr-x').click()
    await page.getByTestId('live-view-pending').click()
    const mine = page.getByTestId('live-pending-row').filter({ hasText: sessionCode })
    await expect(mine).toBeVisible({ timeout: 15_000 })
    await expect(mine.getByTestId('live-pending-unrecorded')).toHaveText('待录入')
    const recorded = page.getByTestId('live-pending-row').filter({ hasText: 'E2E超时督办' })
    await expect(recorded.getByTestId('live-pending-range')).toContainText('120 分钟')
    await page.screenshot({ path: `${shotDir}/08-pending-range.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
