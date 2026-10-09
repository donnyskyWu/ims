import fs from 'fs'
import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'DYCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const KS_SECRET = 'KSCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/e2e-96-screenshots'

test.describe('采集 C3 粉丝日统计', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('抖音粉丝成功与失败、快手粉丝日快照、账号采集 Tab', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const stamp = Date.now().toString(36)
    const okId = `DY_OK_FAN_${stamp}`
    const failId = `DY_FOLLOWER_FAIL_${stamp}`
    const ksId = `KS_OK_FAN_${stamp}`
    const okName = `E2E抖音粉丝号${stamp}`
    const ksName = `E2E快手粉丝号${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')
    await saveDouyin(page, okName, okId)
    const row = page.locator(`[data-testid="dy-row-${okId}"]`)
    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await row.getByRole('button', { name: '立即采集' }).click()
    await expect(row.getByTestId('dy-follower-latest')).toContainText('12880')
    await expect(page.getByTestId('dy-follower-daily')).toContainText('12880')
    await expect(page.getByTestId('dy-log-table').locator('tbody tr').first()).toContainText('成功')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/01-douyin-follower-success.png`, fullPage: true })

    await saveDouyin(page, `E2E抖音粉丝失败${stamp}`, failId)
    const failRow = page.locator(`[data-testid="dy-row-${failId}"]`)
    await failRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await failRow.getByRole('button', { name: '立即采集' }).click()
    const failLog = page.getByTestId('dy-log-table').locator('tbody tr').first()
    await expect(failLog).toContainText('部分成功')
    await expect(failLog).toContainText('粉丝统计失败')
    await expect(failRow.getByTestId('dy-follower-latest')).toContainText('—')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/02-douyin-follower-fail.png`, fullPage: true })

    await page.goto('/ims/collect/kuaishou')
    await expect(page.locator('h1')).toContainText('快手内部账号采集')
    await saveKuaishou(page, ksName, ksId)
    const ksRow = page.locator(`[data-testid="ks-row-${ksId}"]`)
    await ksRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('ks-notice')).toContainText('已导入 Collector')
    await ksRow.getByRole('button', { name: '立即采集' }).click()
    await expect(ksRow.getByTestId('ks-follower-latest')).toContainText('8600')
    await expect(page.getByTestId('ks-follower-daily')).toContainText('8600')
    await expect(page.locator('body')).not.toContainText(KS_SECRET)
    await page.screenshot({ path: `${SHOTS}/03-kuaishou-follower-success.png`, fullPage: true })

    await page.goto('/ims/corp/account/douyin')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(okName)
    await page.getByRole('button', { name: '查询' }).click()
    const acct = page.locator('.tbl-wrap tbody tr').filter({ hasText: okName })
    await acct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    await expect(page.getByTestId('dy-tab-follower')).toContainText('12880')
    await expect(page.getByTestId('dy-tab-follower-daily')).toContainText('12880')
    await expect(page.locator('.drawer.on')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/04-account-follower-tab.png`, fullPage: true })
  })
})

async function saveDouyin(page: import('@playwright/test').Page, name: string, platformId: string) {
  await page.getByTestId('dy-nickname').fill(name)
  await page.getByTestId('dy-company').selectOption({ label: 'E2E抖音采集公司' })
  await page.getByTestId('dy-ip-group').selectOption({ label: 'E2E抖音采集组' })
  await page.getByTestId('dy-platform-id').fill(platformId)
  await page.getByTestId('dy-credential').fill(SECRET)
  await page.getByTestId('dy-save').click()
  await expect(page.getByTestId('dy-notice')).toContainText('已保存')
}

async function saveKuaishou(page: import('@playwright/test').Page, name: string, platformId: string) {
  await page.getByTestId('ks-nickname').fill(name)
  await page.getByTestId('ks-company').selectOption({ label: 'E2E快手采集公司' })
  await page.getByTestId('ks-ip-group').selectOption({ label: 'E2E快手采集组' })
  await page.getByTestId('ks-platform-id').fill(platformId)
  await page.getByTestId('ks-credential').fill(KS_SECRET)
  await page.getByTestId('ks-save').click()
  await expect(page.getByTestId('ks-notice')).toContainText('已保存')
}
