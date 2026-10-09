import fs from 'fs'
import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'WXCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/e2e-100-screenshots'

test.describe('视频号内部账号采集 C5', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('配置掩码、粉丝与作品采集、Cookie 失效、账号采集 Tab', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const stamp = Date.now().toString(36)
    const okId = `WX_OK_E2E_${stamp}`
    const cookieId = `WX_COOKIE_EXPIRED_${stamp}`
    const okName = `E2E视频号成功号${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/collect/wechat-channels')
    await expect(page.locator('h1')).toContainText('视频号内部账号采集')
    await expect(page.locator('[data-testid=wx-company] option', { hasText: 'E2E视频号采集公司' })).toHaveCount(1)
    await expect(page.locator('[data-testid=wx-ip-group] option', { hasText: 'E2E视频号采集组' })).toHaveCount(1)

    await saveAccount(page, okName, okId)
    await expect(page.getByTestId('wx-notice')).toContainText('已保存')
    await expect(page.getByTestId('wx-notice')).not.toContainText(SECRET)
    const row = page.locator(`[data-testid="wx-row-${okId}"]`)
    await expect(row.getByTestId('wx-mask')).toContainText('****')
    await expect(row).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/01-credential-mask.png`, fullPage: true })

    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('wx-notice')).toContainText('已导入 Collector')
    await row.getByRole('button', { name: '测试连接' }).click()
    await expect(row.getByTestId('wx-health')).toContainText('连接正常')
    await row.getByRole('button', { name: '立即采集' }).click()
    const latestLog = page.getByTestId('wx-log-table').locator('tbody tr').first()
    await expect(latestLog).toContainText('成功')
    await expect(latestLog.getByTestId('wx-log-count')).toHaveText('3')
    await expect(row.getByTestId('wx-follower-latest')).toContainText('24600')
    await expect(page.getByTestId('wx-follower-daily')).toContainText('24600')
    await page.screenshot({ path: `${SHOTS}/02-collect-success.png`, fullPage: true })

    await page.goto('/ims/collect/wechat-channels')
    await saveAccount(page, `E2E视频号失效号${stamp}`, cookieId)
    const cookieRow = page.locator(`[data-testid="wx-row-${cookieId}"]`)
    await cookieRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('wx-notice')).toContainText('已导入 Collector')
    await cookieRow.getByRole('button', { name: '立即采集' }).click()
    await expect(page.getByTestId('wx-log-table').locator('tbody tr').first()).toContainText('Cookie 已失效')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/03-cookie-expired.png`, fullPage: true })

    await page.goto('/ims/corp/account/wechat-channels')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(okName)
    await page.getByRole('button', { name: '查询' }).click()
    const acct = page.locator('.tbl-wrap tbody tr').filter({ hasText: okName })
    await acct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    await expect(page.getByTestId('wx-tab-mask')).toContainText('****')
    await expect(page.getByTestId('wx-tab-follower')).toContainText('24600')
    await expect(page.getByTestId('wx-tab-logs')).toContainText('成功')
    await expect(page.getByTestId('wx-tab-log-count').first()).toHaveText('3')
    await expect(page.locator('.drawer.on')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/04-account-collect-tab.png`, fullPage: true })
  })
})

async function saveAccount(page: import('@playwright/test').Page, name: string, platformId: string) {
  await page.getByTestId('wx-nickname').fill(name)
  await page.getByTestId('wx-company').selectOption({ label: 'E2E视频号采集公司' })
  await page.getByTestId('wx-ip-group').selectOption({ label: 'E2E视频号采集组' })
  await page.getByTestId('wx-platform-id').fill(platformId)
  await page.getByTestId('wx-credential').fill(SECRET)
  await page.getByTestId('wx-save').click()
  await expect(page.getByTestId('wx-notice')).toContainText('已保存')
}
