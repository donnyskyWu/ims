import { expect, test } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-C042 · IP 组名称下拉、种子明细、趋势图、导出和重置。 */
test.describe('bi metric analysis C042', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('tc_r9 runs analysis with ip group name, chart, export and reset', async ({ page }) => {
    test.setTimeout(120_000)
    const code = `C042_${Date.now()}`
    const name = `C042分析${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/bi/metric')
    await page.getByRole('button', { name: '新建指标' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await modal.getByTestId('bi-metric-name').fill(name)
    await modal.getByTestId('bi-metric-code').fill(code)
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })

    await page.goto('/ims/bi/analysis')
    await expect(page.locator('h1')).toContainText('指标分析')
    const ip = page.getByTestId('bi-analysis-ip')
    await expect(ip).toBeVisible()
    await expect(ip.locator('option', { hasText: '电竞一组' })).toHaveCount(1)
    await expect(page.getByText('IP 组 ID')).toHaveCount(0)

    const metricSelect = page.getByTestId('bi-analysis-metrics')
    const metricValue = await metricSelect.locator('option', { hasText: name }).getAttribute('value')
    expect(metricValue).toBeTruthy()
    await metricSelect.selectOption(metricValue!)
    await page.getByTestId('bi-analysis-from').fill('2026-09-01')
    await page.getByTestId('bi-analysis-to').fill('2026-09-30')
    await page.getByTestId('bi-analysis-run').click()

    const table = page.locator('tbody')
    await expect(table).toContainText('电竞一组')
    await expect(table).toContainText('体育二组')
    await expect(table).toContainText(name)
    await expect(table).toContainText('2026-09-30')
    await expect(page.getByTestId('bi-analysis-page')).toContainText('共 2 条')
    await expect(page.getByText('分析占位')).toHaveCount(0)
    await expect(page.getByText('未接 DW')).toHaveCount(0)

    await page.locator('.tab', { hasText: '指标趋势' }).click()
    const chart = page.getByTestId('bi-analysis-chart')
    await expect(chart.locator('svg')).toBeVisible()
    await page.getByTestId('bi-analysis-chart-type').selectOption('line')
    await expect(chart.locator('polyline')).toBeVisible()
    await page.getByTestId('bi-analysis-chart-type').selectOption('pie')
    await expect(chart.locator('circle').first()).toBeVisible()

    await ip.selectOption('电竞一组')
    await page.locator('.tab', { hasText: '指标明细' }).click()
    await page.getByTestId('bi-analysis-run').click()
    await expect(table).toContainText('电竞一组')
    await expect(table).not.toContainText('体育二组')

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('bi-analysis-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('指标分析')
    await expect(page.getByTestId('bi-analysis-toast')).toContainText('已导出')

    await page.getByRole('button', { name: '重置' }).click()
    await expect(page.getByTestId('bi-analysis-toast')).toContainText('已重置')
    await expect(page.getByText('请选择指标并运行分析')).toBeVisible()
  })
})
