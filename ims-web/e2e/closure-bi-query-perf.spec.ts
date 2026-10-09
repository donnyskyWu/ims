import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * BI-002 筛选下钻、宽日期异步/终止、查询性能监控（纯 UI）。
 * 平台筛选收窄当前层；超过半年转异步；超过一年 1194；性能页见超 30 秒与慢报表并回到设计器。
 */
const shotDir = '/opt/cursor/artifacts/bi-query-perf'

test.describe('bi query perf and filter closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter drill, async span, 1194 and perf slow report', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const reportName = `E2E 查询性能 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')

    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await expect(reportModal).toBeVisible()
    await reportModal.locator('input.fld-in').first().fill(reportName)
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器', { timeout: 15_000 })

    await page.getByTestId('bi-open-drill').click()
    await expect(page.locator('h1')).toHaveText('预览与下钻', { timeout: 15_000 })

    await page.getByTestId('bi-filter-platform').selectOption('抖音')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-drill-value')).toHaveCount(1)
    await expect(page.getByTestId('bi-drill-value')).toContainText('抖音')
    await page.screenshot({ path: `${shotDir}/01-platform-filter.png` })

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('bi-export-csv').click(),
    ])
    expect(download.suggestedFilename()).toBe('bi_drill.csv')
    await expect(page.getByTestId('bi-export-note')).toContainText('抖音')

    await page.getByTestId('bi-filter-from').fill('2026-01-01')
    await page.getByTestId('bi-filter-to').fill('2026-10-03')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-async-card')).toContainText('V3-B6')
    await page.screenshot({ path: `${shotDir}/02-async-span.png` })

    await page.getByTestId('bi-filter-from').fill('2020-01-01')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-drill-toast')).toContainText('1194')
    await expect(page.getByTestId('bi-drill-toast')).toContainText('BR-204')
    await page.screenshot({ path: `${shotDir}/03-terminate-1194.png` })

    await page.getByTestId('bi-open-perf').click()
    await expect(page.locator('h1')).toHaveText('查询性能监控', { timeout: 15_000 })
    await expect(page.getByTestId('bi-perf-over30')).not.toHaveText('0')
    await expect(page.getByTestId('bi-perf-async')).not.toHaveText('0')
    await expect(page.getByTestId('bi-perf-alert')).toContainText('BR-204')
    const slowRow = page.getByTestId('bi-perf-slow-row').filter({ hasText: reportName })
    await expect(slowRow).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-perf-stats.png` })

    await slowRow.getByRole('button', { name: reportName }).click()
    await expect(page.locator('h1')).toContainText('报表设计器', { timeout: 15_000 })
    await expect(page.locator('.pg-h')).toContainText(reportName)
    await page.screenshot({ path: `${shotDir}/05-slow-report-designer.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
