import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #180 · 补录空态红框 + 24h 督办钉钉/短信本地桩 + 未提交下播「待录入」
 * 不重做开播/取消/黄红，也不重做台账筛选。
 */
const shotDir = '/opt/cursor/artifacts'
const OVERDUE_SESSION = 'IMS20261006DYS1048'

fs.mkdirSync(shotDir, { recursive: true })

test.describe('live backfill empty and 24h urge stub', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('supplement empty state, overdue urge stub, and unfiled report empty', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })

    await page.getByTestId('live-supplement-open').click()
    const drawer = page.locator('.drawer').filter({ hasText: '历史补录' })
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('live-supplement-empty')).toBeVisible()
    await expect(drawer.getByTestId('live-supplement-empty')).toContainText('补录说明')
    await expect(drawer.getByTestId('live-supplement-reason')).toHaveAttribute('data-missing', '1')
    await expect(drawer.getByTestId('live-supplement-account')).toHaveAttribute('data-missing', '1')
    await page.screenshot({ path: `${shotDir}/live-180-supplement-empty.png`, fullPage: true })

    const missingResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/supplement') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('live-supplement-submit').click()
    expect(((await (await missingResp).json()) as { code: number }).code).toBe(1049)
    await expect(drawer.getByTestId('live-supplement-error')).toContainText('1049')
    await expect(drawer.getByTestId('live-supplement-reason')).toHaveAttribute('data-missing', '1')
    await page.screenshot({ path: `${shotDir}/live-180-supplement-1049.png`, fullPage: true })
    await drawer.locator('.dr-x').click()

    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/live/report/pending') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-view-pending').click()
    const pendingBody = (await (await pendingResp).json()) as {
      code: number
      data?: {
        overdueCount?: number
        list?: Array<{ sessionCode?: string; overdue?: boolean; urgeChannels?: string[] }>
      }
    }
    expect(pendingBody.code).toBe(1048)
    expect(pendingBody.data?.overdueCount).toBeGreaterThan(0)
    const hit = pendingBody.data?.list?.find((row) => row.sessionCode === OVERDUE_SESSION)
    expect(hit?.overdue).toBe(true)
    expect(hit?.urgeChannels).toEqual(['IN_APP', 'DINGTALK', 'SMS'])
    await expect(page.getByTestId('live-pending-count')).toBeVisible()
    const row = page.getByTestId('live-pending-row').filter({ hasText: OVERDUE_SESSION })
    await expect(row.getByTestId('live-pending-overdue')).toHaveText('超 24h')
    await expect(row.getByTestId('live-urge-stub')).toContainText('钉钉/短信本地桩')
    await page.screenshot({ path: `${shotDir}/live-180-pending-urge-stub.png`, fullPage: true })

    await row.locator('td').first().click()
    const detail = page.locator('.drawer').filter({ hasText: OVERDUE_SESSION })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(detail.getByTestId('live-report-empty')).toContainText('待录入')
    await page.screenshot({ path: `${shotDir}/live-180-report-empty.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
