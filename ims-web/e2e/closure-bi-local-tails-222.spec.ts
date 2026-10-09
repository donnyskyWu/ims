import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #222 · BI 本地边角（纯 UI）
 * 筛选无命中空态、单侧日期、分析窗外空结果、空大屏与缺失大屏、订阅名称与复制提示。
 * 不覆盖 #176 撤销确认，也不覆盖 #198 标准报表筛选 / 下钻拒绝 / 订阅取消与快照空态。
 */
const shotDir = '/opt/cursor/artifacts/bi-local-tails-222'

test.describe('bi local tails 222', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter empties, date edges, blank screen, subscribe hint', async ({ page, context }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(shotDir, { recursive: true })
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-222-${Date.now()}`
    const screenName = `E2E 空大屏 ${label}`
    const metricName = `E2E 指标 ${label}`

    await loginAdmin(page)

    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')
    await page.getByTestId('bi-report-keyword').fill('no-such-report-222')
    await page.getByTestId('bi-report-search').click()
    await expect(page.getByTestId('bi-report-list-empty')).toContainText('当前筛选下暂无报表')
    await page.screenshot({ path: `${shotDir}/01-report-filter-empty.png` })

    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.getByRole('button', { name: '大屏' }).click()
    await reportModal.locator('input.fld-in').first().fill(screenName)
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器', { timeout: 15_000 })
    const reportId = new URL(page.url()).searchParams.get('reportId')
    expect(reportId).toBeTruthy()
    await page.getByTestId('bi-save').click()
    await expect(page.getByTestId('bi-save-status')).toContainText('已保存')

    await page.goto('/ims/bi/screen-config')
    await expect(page.locator('h1')).toContainText('大屏配置')
    await page.getByTestId('bi-screen-keyword').fill('no-such-screen-222')
    await page.getByTestId('bi-screen-search').click()
    await expect(page.getByTestId('bi-screen-empty')).toContainText('当前筛选下暂无大屏')
    await page.screenshot({ path: `${shotDir}/02-screen-filter-empty.png` })

    await page.getByTestId('bi-screen-keyword').fill(screenName)
    await page.getByTestId('bi-screen-search').click()
    const screenRow = page.locator('.tbl-wrap tbody tr', { hasText: screenName })
    await expect(screenRow).toBeVisible({ timeout: 15_000 })
    await screenRow.getByRole('button', { name: '配置预览' }).click()
    await expect(page.getByTestId('bi-screen-widget-empty')).toContainText('暂无组件')
    await page.screenshot({ path: `${shotDir}/03-screen-widgets-empty.png` })
    await screenRow.getByRole('link', { name: '全屏展示' }).click()
    await expect(page.getByTestId('bi-screen-view-empty')).toContainText('暂无组件', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/04-screen-view-empty.png` })

    await page.goto('/ims/bi/screen/999999999/view')
    await expect(page.getByTestId('bi-screen-gate')).toContainText('大屏不存在')
    await page.screenshot({ path: `${shotDir}/05-screen-missing.png` })

    await page.goto('/ims/bi/metric')
    await expect(page.locator('h1')).toContainText('指标管理')
    await page.getByRole('button', { name: '新建指标' }).click()
    const metricModal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await metricModal.locator('input.fld-in').first().fill(metricName)
    await metricModal.getByRole('button', { name: '保存' }).click()
    await expect(metricModal).toBeHidden({ timeout: 15_000 })
    await page.getByTestId('bi-metric-keyword').fill('no-such-metric-222')
    await page.getByTestId('bi-metric-search').click()
    await expect(page.getByTestId('bi-metric-empty')).toContainText('当前筛选下暂无指标')
    await page.screenshot({ path: `${shotDir}/06-metric-filter-empty.png` })
    await page.getByTestId('bi-metric-keyword').fill(metricName)
    await page.getByTestId('bi-metric-search').click()
    await expect(page.locator('tbody tr', { hasText: metricName })).toBeVisible()

    await page.goto('/ims/bi/analysis')
    await expect(page.locator('h1')).toContainText('指标分析')
    await page.getByTestId('bi-analysis-metrics').selectOption({ label: new RegExp(metricName) })
    await page.getByTestId('bi-analysis-from').fill('2026-09-20')
    await page.getByTestId('bi-analysis-to').fill('2026-09-01')
    await page.getByTestId('bi-analysis-run').click()
    await expect(page.getByTestId('bi-analysis-error')).toContainText('开始日期不能晚于结束日期')
    await page.getByTestId('bi-analysis-to').fill('')
    await page.getByTestId('bi-analysis-run').click()
    await expect(page.getByTestId('bi-analysis-error')).toContainText('请同时填写开始和结束日期')
    await page.getByTestId('bi-analysis-from').fill('2020-01-01')
    await page.getByTestId('bi-analysis-to').fill('2020-01-02')
    await page.getByTestId('bi-analysis-run').click()
    await expect(page.getByTestId('bi-analysis-empty')).toContainText('当前日期下暂无分析数据')
    await page.screenshot({ path: `${shotDir}/07-analysis-empty.png` })
    await page.getByTestId('bi-analysis-from').fill('2026-09-01')
    await page.getByTestId('bi-analysis-to').fill('2026-09-30')
    await page.getByTestId('bi-analysis-run').click()
    await expect(page.locator('tbody tr', { hasText: metricName })).toBeVisible()

    await page.goto('/ims/bi/report/preview')
    await expect(page.locator('h1')).toHaveText('预览与下钻')
    await page.getByTestId('bi-filter-to').fill('')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-filter-error')).toContainText('请同时填写开始和结束日期')
    await page.screenshot({ path: `${shotDir}/08-preview-one-sided-date.png` })

    await page.goto('/ims/bi/query/perf')
    await expect(page.locator('h1')).toHaveText('查询性能监控')
    await page.getByTestId('bi-perf-to').fill('')
    await page.getByTestId('bi-perf-refresh').click()
    await expect(page.getByTestId('bi-perf-error')).toContainText('请同时填写开始和结束日期')
    await page.getByTestId('bi-perf-from').fill('2026-10-03')
    await page.getByTestId('bi-perf-to').fill('2026-09-01')
    await page.getByTestId('bi-perf-refresh').click()
    await expect(page.getByTestId('bi-perf-error')).toContainText('开始日期不能晚于结束日期')
    await page.screenshot({ path: `${shotDir}/09-perf-date-edge.png` })

    await page.goto('/ims/bi/report/subscribe')
    await page.getByRole('button', { name: '订阅推送' }).click()
    const subModal = page.locator('.modal-mask .card').filter({ hasText: '新建订阅' })
    await subModal.getByTestId('bi-sub-save').click()
    await expect(subModal.getByTestId('bi-sub-form-error')).toContainText('订阅名称必填')
    await subModal.getByTestId('bi-sub-name').fill(`E2E 订阅 ${label}`)
    await subModal.getByTestId('bi-sub-save').click()
    await expect(subModal.getByTestId('bi-sub-form-error')).toContainText('请填写报表 ID')
    await subModal.getByTestId('bi-sub-report').fill(String(reportId))
    await subModal.getByTestId('bi-sub-save').click()
    await expect(page.getByTestId('bi-sub-created')).toContainText('订阅成功，下次推送')
    await page.screenshot({ path: `${shotDir}/10-subscribe-created.png` })

    await page.goto('/ims/bi/report/subscribe?tab=share')
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const shareModal = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await shareModal.locator('input[type="number"]').first().fill(String(reportId))
    await shareModal.getByRole('button', { name: '生成' }).click()
    const shareRow = page.locator('.tbl-wrap tbody tr', { hasText: screenName }).filter({ hasText: '已通过' })
    await expect(shareRow).toBeVisible({ timeout: 15_000 })
    await shareRow.getByTestId('bi-share-copy').click()
    await expect(page.getByTestId('bi-share-copy-note')).toContainText(/已复制链接|复制失败/)
    await page.screenshot({ path: `${shotDir}/11-share-copy-note.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
