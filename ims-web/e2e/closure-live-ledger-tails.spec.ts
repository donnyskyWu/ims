import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #156 · 纯 UI
 * 台账筛选（平台/风险/补录/当日日期）、更正单空态、超时督办卡片、导出回执领取。
 */
const shotDir = '/opt/cursor/artifacts/e2e-156-screenshots'
const SESSION = 'IMS20261008DYS0082'
const OVERDUE = 'IMS20261006DYS1048'

fs.mkdirSync(shotDir, { recursive: true })

test.describe('live ledger filter export and supervise tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filters, empty correction slips, overdue cards, and export claim', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })

    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    await page.getByTestId('live-filter-platform').selectOption('DOUYIN')
    await page.getByTestId('live-filter-risk').selectOption('GREEN')
    await page.getByTestId('live-filter-supplement').selectOption('false')
    await page.getByTestId('live-filter-from').fill('2026-10-08')
    await page.getByTestId('live-filter-to').fill('2026-10-08')
    const hitResp = page.waitForResponse((r) => {
      const url = r.url()
      return (
        url.includes('/live/sessions/list') &&
        url.includes('platform=DOUYIN') &&
        url.includes('riskLevel=GREEN') &&
        url.includes('isSupplement=false') &&
        url.includes('timeRange=2026-10-08') &&
        r.request().method() === 'GET' &&
        r.status() === 200
      )
    })
    await page.getByRole('button', { name: '查询' }).click()
    await hitResp
    await expect(page.locator('tbody tr', { hasText: SESSION })).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/01-filters-hit.png`, fullPage: true })

    await page.getByTestId('live-filter-platform').selectOption('KUAISHOU')
    const missResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.url().includes('platform=KUAISHOU') && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await missResp
    await expect(page.locator('tbody tr', { hasText: SESSION })).toHaveCount(0)
    await expect(page.locator('.empty .et')).toContainText('暂无场次')
    await page.screenshot({ path: `${shotDir}/02-filters-miss.png`, fullPage: true })

    await page.getByRole('button', { name: '重置' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    const again = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.url().includes(SESSION) && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await again
    await page.locator('tbody tr', { hasText: SESSION }).getByRole('button', { name: '详情' }).click()
    const detail = page.locator('.drawer.on')
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(detail.getByTestId('live-correction-empty')).toContainText('暂无更正单')
    await expect(detail.getByTestId('live-correction-slip')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-correction-empty.png`, fullPage: true })
    await detail.locator('.dr-x').click()
    await expect(page.locator('.drawer.on')).toHaveCount(0)

    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/live/report/pending') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-view-pending').click()
    const pendingBody = (await (await pendingResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; overdue?: boolean; superviseChannel?: string }> }
    }
    expect(pendingBody.code).toBe(1048)
    const hit = pendingBody.data?.list?.find((row) => row.sessionCode === OVERDUE)
    expect(hit?.overdue).toBe(true)
    expect(hit?.superviseChannel).toBe('IN_APP')
    const card = page.getByTestId('live-overdue-card').filter({ hasText: OVERDUE })
    await expect(card).toBeVisible({ timeout: 15_000 })
    await expect(card.getByTestId('live-overdue-stub')).toContainText('已记入站内督办')
    await expect(page.getByTestId('live-pending-row').filter({ hasText: OVERDUE })).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-overdue-card.png`, fullPage: true })

    await page.getByTestId('live-view-sessions').click()
    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('tbody tr', { hasText: SESSION })).toBeVisible({ timeout: 15_000 })
    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('live-ledger-export').click()
    const exportBody = (await (await exportResp).json()) as {
      code: number
      data?: { message?: string; exportTaskId?: string; fileName?: string }
    }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.message).toContain('导出任务已提交')
    expect(exportBody.data?.fileName).toBe('live_ledger.xlsx')
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('live_ledger.xlsx')
    await expect(page.getByTestId('live-export-note')).toContainText('导出任务已提交')
    await expect(page.getByTestId('live-export-receipt')).toContainText(String(exportBody.data?.exportTaskId))
    const claimDownload = page.waitForEvent('download')
    await page.getByTestId('live-export-claim').click()
    expect((await claimDownload).suggestedFilename()).toBe('live_ledger.xlsx')
    await page.screenshot({ path: `${shotDir}/05-export-receipt.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
