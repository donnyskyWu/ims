import fs from 'fs'
import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'DYCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const KS_SECRET = 'KSCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/e2e-97-screenshots'

test.describe('采集 C4 作品日快照', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('抖音与快手作品日快照可见，同一天重复采集不新增行', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const stamp = Date.now().toString(36)
    const dyId = `DY_OK_SNAP_${stamp}`
    const ksId = `KS_OK_SNAP_${stamp}`
    const dyName = `E2E抖音快照号${stamp}`
    const ksName = `E2E快手快照号${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')
    await expect(page.getByTestId('dy-video-snapshot')).toBeVisible()
    await saveDouyin(page, dyName, dyId)
    const row = page.locator(`[data-testid="dy-row-${dyId}"]`)
    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await row.getByRole('button', { name: '立即采集' }).click()
    const dySnap = page.getByTestId('dy-video-snapshot').locator('tbody tr', { hasText: dyName }).filter({ hasText: 'dyv-2001' })
    await expect(dySnap).toHaveCount(1)
    await expect(dySnap.getByTestId('dy-video-play')).toHaveText('2100')
    await expect(dySnap.getByTestId('dy-video-like')).toHaveText('40')
    await expect(dySnap.getByTestId('dy-video-comment')).toHaveText('6')
    await expect(dySnap.getByTestId('dy-video-share')).toHaveText('2')
    await expect(dySnap.getByTestId('dy-video-date')).toHaveText(/^\d{4}-\d{2}-\d{2}$/)
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/01-douyin-video-snapshot.png`, fullPage: true })

    await row.getByRole('button', { name: '立即采集' }).click()
    await expect(page.getByTestId('dy-log-table').locator('tbody tr').first()).toContainText('成功')
    await expect(dySnap).toHaveCount(1)
    await expect(dySnap.getByTestId('dy-video-play')).toHaveText('2100')
    await page.screenshot({ path: `${SHOTS}/02-douyin-snapshot-idempotent.png`, fullPage: true })

    await page.goto('/ims/collect/kuaishou')
    await expect(page.locator('h1')).toContainText('快手内部账号采集')
    await saveKuaishou(page, ksName, ksId)
    const ksRow = page.locator(`[data-testid="ks-row-${ksId}"]`)
    await ksRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('ks-notice')).toContainText('已导入 Collector')
    await ksRow.getByRole('button', { name: '立即采集' }).click()
    const ksSnap = page.getByTestId('ks-video-snapshot').locator('tbody tr', { hasText: ksName }).filter({ hasText: 'ksv-1001' })
    await expect(ksSnap).toHaveCount(1)
    await expect(ksSnap.getByTestId('ks-video-play')).toHaveText('1200')
    await expect(ksSnap.getByTestId('ks-video-like')).toHaveText('30')
    await expect(ksSnap.getByTestId('ks-video-comment')).toHaveText('4')
    await expect(ksSnap.getByTestId('ks-video-share')).toHaveText('1')
    await expect(page.locator('body')).not.toContainText(KS_SECRET)
    await page.screenshot({ path: `${SHOTS}/03-kuaishou-video-snapshot.png`, fullPage: true })

    await page.goto('/ims/corp/account/douyin')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(dyName)
    await page.getByRole('button', { name: '查询' }).click()
    const acct = page.locator('.tbl-wrap tbody tr').filter({ hasText: dyName })
    await acct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    const tabSnap = page.getByTestId('dy-tab-video-snapshot').locator('tbody tr', { hasText: 'dyv-2001' })
    await expect(tabSnap.getByTestId('dy-tab-video-play')).toHaveText('2100')
    await expect(page.locator('.drawer.on')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/04-account-video-snapshot.png`, fullPage: true })
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
