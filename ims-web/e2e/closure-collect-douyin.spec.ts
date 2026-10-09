import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'DYCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/e2e-94-screenshots'

test.describe('抖音内部账号采集 C2', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('配置掩码、成功采集、Cookie 失效与引擎不可用', async ({ page }) => {
    test.setTimeout(120_000)
    const stamp = Date.now().toString(36)
    const okId = `DY_OK_E2E_${stamp}`
    const cookieId = `DY_COOKIE_EXPIRED_${stamp}`
    const engineId = `DY_ENGINE_DOWN_${stamp}`
    const okName = `E2E抖音成功号${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')
    await expect(page.locator('[data-testid=dy-company] option', { hasText: 'E2E抖音采集公司' })).toHaveCount(1)
    await expect(page.locator('[data-testid=dy-ip-group] option', { hasText: 'E2E抖音采集组' })).toHaveCount(1)

    await saveAccount(page, okName, okId)
    await expect(page.getByTestId('dy-notice')).toContainText('已保存')
    await expect(page.getByTestId('dy-notice')).not.toContainText(SECRET)
    const row = page.locator(`[data-testid="dy-row-${okId}"]`)
    await expect(row.getByTestId('dy-mask')).toContainText('****')
    await expect(row).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/01-credential-mask.png`, fullPage: true })

    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await row.getByRole('button', { name: '测试连接' }).click()
    await expect(row.getByTestId('dy-health')).toContainText('连接正常')
    await row.getByRole('button', { name: '立即采集' }).click()
    const latestLog = page.getByTestId('dy-log-table').locator('tbody tr').first()
    await expect(latestLog).toContainText('成功')
    await expect(latestLog.getByTestId('dy-log-count')).toHaveText('5')
    await page.screenshot({ path: `${SHOTS}/02-collect-success.png`, fullPage: true })

    await page.goto('/ims/collect/douyin')
    await saveAccount(page, `E2E抖音失效号${stamp}`, cookieId)
    const cookieRow = page.locator(`[data-testid="dy-row-${cookieId}"]`)
    await cookieRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await cookieRow.getByRole('button', { name: '立即采集' }).click()
    await expect(page.getByTestId('dy-log-table').locator('tbody tr').first()).toContainText('Cookie 已失效')
    await page.screenshot({ path: `${SHOTS}/03-cookie-expired.png`, fullPage: true })

    await saveAccount(page, `E2E抖音引擎号${stamp}`, engineId)
    const engineRow = page.locator(`[data-testid="dy-row-${engineId}"]`)
    await engineRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await engineRow.getByRole('button', { name: '立即采集' }).click()
    await expect(page.getByTestId('dy-log-table').locator('tbody tr').first()).toContainText('浏览器引擎不可用')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/04-engine-unavailable.png`, fullPage: true })

    await page.goto('/ims/corp/account/douyin')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(okName)
    await page.getByRole('button', { name: '查询' }).click()
    const acct = page.locator('.tbl-wrap tbody tr').filter({ hasText: okName })
    await acct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    await expect(page.getByTestId('dy-tab-mask')).toContainText('****')
    await expect(page.getByTestId('dy-tab-logs')).toContainText('成功')
    await expect(page.getByTestId('dy-tab-log-count').first()).toHaveText('5')
    await expect(page.locator('.drawer.on')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/05-account-collect-tab.png`, fullPage: true })
  })
})

async function saveAccount(page: import('@playwright/test').Page, name: string, platformId: string) {
  await page.getByTestId('dy-nickname').fill(name)
  await page.getByTestId('dy-company').selectOption({ label: 'E2E抖音采集公司' })
  await page.getByTestId('dy-ip-group').selectOption({ label: 'E2E抖音采集组' })
  await page.getByTestId('dy-platform-id').fill(platformId)
  await page.getByTestId('dy-credential').fill(SECRET)
  await page.getByTestId('dy-save').click()
  await expect(page.getByTestId('dy-notice')).toContainText('已保存')
}
