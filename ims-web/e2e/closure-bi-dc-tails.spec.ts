import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #150 · BI 预览 / DC 穿透的本地收尾（纯 UI）
 * 筛选记住、指标卡空态、下钻返回上卷、导出有效期提示、工作台来源链接。
 * 不覆盖已关闭的看板总览、布局新鲜度、查询性能。
 */
const shotDir = '/opt/cursor/artifacts/bi-dc-tails-150'

test.describe('bi dc local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('preview remembers filters, empties widgets, rolls up, and links workbench', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/bi/report/preview')
    await expect(page.locator('h1')).toHaveText('预览与下钻')
    await expect(page.getByTestId('bi-widget-kpi').first()).toBeVisible()
    await page.getByTestId('bi-filter-platform').selectOption('视频号')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-widget-kpi').first()).toBeVisible()

    await page.reload()
    await expect(page.getByTestId('bi-filter-restored')).toHaveText('已恢复上次筛选')
    await expect(page.getByTestId('bi-filter-platform')).toHaveValue('视频号')
    await expect(page.getByTestId('bi-filter-from')).toHaveValue('2026-09-01')
    await page.screenshot({ path: `${shotDir}/01-filter-restored.png` })

    await page.getByTestId('bi-filter-from').fill('2020-01-01')
    await page.getByTestId('bi-filter-to').fill('2020-01-02')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-widget-empty')).toContainText('当前筛选下暂无指标')
    await expect(page.getByTestId('bi-drill-value').first()).toContainText('抖音')
    await page.screenshot({ path: `${shotDir}/02-widget-empty.png` })

    await page.getByTestId('bi-filter-from').fill('2026-10-03')
    await page.getByTestId('bi-filter-to').fill('2026-09-01')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-filter-error')).toContainText('开始日期不能晚于结束日期')

    await page.getByTestId('bi-filter-from').fill('2026-09-01')
    await page.getByTestId('bi-filter-to').fill('2026-10-03')
    await page.getByTestId('bi-filter-platform').selectOption('')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-widget-kpi').first()).toBeVisible()
    await expect(page.getByTestId('bi-drill-dimension')).toHaveText('平台')
    await page.getByTestId('bi-drill-value').first().click()
    await expect(page.getByTestId('bi-crumb-PLATFORM')).toContainText('抖音')
    await expect(page.getByTestId('bi-crumb-sep').first()).toContainText('▸')
    await expect(page.getByTestId('bi-drill-dimension')).toHaveText('账号')
    await page.getByTestId('bi-drill-rollup').click()
    await expect(page.getByTestId('bi-drill-dimension')).toHaveText('平台')
    await expect(page.getByTestId('bi-drill-rollup')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-drill-rollup.png` })

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('bi-export-xlsx').click(),
    ])
    expect(download.suggestedFilename()).toBe('bi_drill.xlsx')
    await expect(page.getByTestId('bi-export-note')).toContainText('60 秒内有效')
    await expect(page.getByTestId('bi-export-note')).toContainText('抖音')
    await page.screenshot({ path: `${shotDir}/04-export-note.png` })

    await page.getByTestId('bi-workbench-link').click()
    await expect(page.locator('h1')).toHaveText('消息中心')
    await expect(page.getByTestId('wb-source-filter')).toContainText('来源 BI')
    await expect(page.getByTestId('wb-source-empty')).toContainText('来源 BI 暂无消息')
    await page.screenshot({ path: `${shotDir}/05-workbench-bi.png` })
    await page.getByTestId('wb-back-bi').click()
    await expect(page.locator('h1')).toHaveText('预览与下钻')

    await page.goto('/ims/dc/trace')
    await expect(page.locator('h1')).toHaveText('穿透查询')
    await expect(page.getByTestId('dc-trace-graph-empty')).toContainText('选择入口后查询')
    await page.screenshot({ path: `${shotDir}/06-dc-graph-empty.png` })
    await page.getByTestId('dc-trace-entry-type').selectOption('ACCOUNT')
    await page.getByTestId('dc-trace-keyword').fill('E2E-DC-TAIL-150')
    await page.getByTestId('dc-trace-date-from').fill('2026-01-01')
    await page.getByTestId('dc-trace-date-to').fill('2026-01-02')
    await page.getByTestId('dc-trace-search-entry').click()
    await expect(page.getByTestId('dc-trace-entry-empty')).toBeVisible()
    await expect(page.getByTestId('dc-trace-export')).toBeDisabled()

    await page.reload()
    await expect(page.getByTestId('dc-filter-restored')).toHaveText('已恢复上次筛选')
    await expect(page.getByTestId('dc-trace-keyword')).toHaveValue('E2E-DC-TAIL-150')
    await expect(page.getByTestId('dc-trace-date-from')).toHaveValue('2026-01-01')
    await expect(page.getByTestId('dc-trace-entry-type')).toHaveValue('ACCOUNT')
    await page.screenshot({ path: `${shotDir}/07-dc-filter-restored.png` })

    await page.getByTestId('dc-workbench-link').click()
    await expect(page.getByTestId('wb-source-filter')).toContainText('来源 DC')
    await expect(page.getByTestId('wb-source-empty')).toContainText('来源 DC 暂无消息')
    await page.screenshot({ path: `${shotDir}/08-workbench-dc.png` })
    await page.getByTestId('wb-back-dc').click()
    await expect(page.locator('h1')).toHaveText('穿透查询')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})