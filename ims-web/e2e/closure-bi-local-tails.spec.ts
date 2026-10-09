import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #198 · BI 下钻空态、报表中心筛选边界、订阅取消与未推送快照（纯 UI）
 * 不覆盖 #176 分享撤销/立即推送确认，也不覆盖 #139 查询性能。
 */
const shotDir = '/opt/cursor/artifacts/bi-local-tails-198'

test.describe('bi drill report subscribe local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('denied drill, report edges, and subscribe leftovers', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/bi/report/preview?reportId=999999')
    await expect(page.locator('h1')).toHaveText('预览与下钻')
    await expect(page.getByTestId('bi-denied-empty')).toContainText('您无权查看该报表')
    await expect(page.getByTestId('bi-drill-value')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/01-denied-empty.png` })

    await page.goto('/ims/bi/report/preview')
    await expect(page.getByTestId('bi-widget-kpi').first()).toBeVisible()
    await page.getByTestId('bi-filter-platform').selectOption('快手')
    await page.getByTestId('bi-filter-run').click()
    await expect(page.getByTestId('bi-drill-empty')).toContainText('当前筛选下该层暂无数据')
    await page.screenshot({ path: `${shotDir}/02-drill-filter-empty.png` })

    await page.goto('/ims/bi/report')
    await expect(page.locator('h1')).toHaveText('报表中心')
    await expect(page.getByTestId('bi-report-row').first()).toBeVisible()
    await page.getByTestId('bi-report-platform').selectOption('KUAISHOU')
    await page.getByTestId('bi-report-run').click()
    await expect(page.getByTestId('bi-report-empty')).toContainText('当前平台下暂无数据')
    await page.screenshot({ path: `${shotDir}/03-report-platform-empty.png` })

    await page.getByTestId('bi-report-from').fill('2026-09-20')
    await page.getByTestId('bi-report-to').fill('2026-09-01')
    await page.getByTestId('bi-report-run').click()
    await expect(page.getByTestId('bi-report-error')).toContainText('开始日期不能晚于结束日期')

    await page.getByTestId('bi-report-platform').selectOption('')
    await page.getByTestId('bi-report-from').fill('')
    await page.getByTestId('bi-report-to').fill('')
    await page.getByTestId('bi-report-card-roi').click()
    await page.getByTestId('bi-report-platform').selectOption('DOUYIN')
    await page.getByTestId('bi-report-run').click()
    await expect(page.getByTestId('bi-report-filter-note')).toContainText('本报表不含平台列')
    await expect(page.getByTestId('bi-report-row')).toHaveCount(2)
    await page.screenshot({ path: `${shotDir}/04-report-no-platform.png` })

    const label = `e2e-bi-tail-${Date.now()}`
    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(`尾报表 ${label}`)
    const createReportResp = page.waitForResponse(
      (r) => r.url().includes('/bi/report') && r.request().method() === 'POST' && r.status() === 200,
    )
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    const reportBody = (await (await createReportResp).json()) as { code: number; data?: { id: number } }
    expect(reportBody.code).toBe(0)
    const reportId = reportBody.data!.id

    await page.goto('/ims/bi/report/subscribe')
    await page.getByRole('button', { name: '订阅推送' }).click()
    const subModal = page.locator('.modal-mask .card').filter({ hasText: '新建订阅' })
    await subModal.locator('input.fld-in').first().fill(label)
    await subModal.locator('input[type="number"]').fill(String(reportId))
    await subModal.locator('select').selectOption('DAILY')
    const createSubResp = page.waitForResponse(
      (r) => r.url().includes('/bi/subscribe') && r.request().method() === 'POST' && !r.url().includes('share') && r.status() === 200,
    )
    await subModal.getByRole('button', { name: '保存' }).click()
    expect(((await (await createSubResp).json()) as { code: number }).code).toBe(0)

    const created = page.locator('tbody tr', { hasText: label })
    await expect(created.getByTestId('bi-sub-next')).toHaveText('明日 09:00')
    await created.getByTestId('bi-sub-snapshot-open').click()
    await expect(page.getByTestId('bi-sub-snapshot-empty')).toContainText('尚未推送，暂无快照')
    await page.screenshot({ path: `${shotDir}/05-snapshot-empty.png` })
    await created.getByTestId('bi-sub-cancel').click()
    await expect(created).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/06-subscribe-cancelled.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
