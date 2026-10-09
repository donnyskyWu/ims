import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #240 · BI 本地余项（纯 UI）
 * 自定义查询：行数上限、单侧/颠倒日期、筛选空态、条件无命中空结果。
 * 订阅：无法识别的推送时刻。分享：非整有效期、驳回说明必填。
 * 不覆盖 #176 撤销确认、#198 下钻拒绝/标准报表筛选、#222 单侧日期（预览/性能/分析）与筛选空态。
 */
const shotDir = '/opt/cursor/artifacts/bi-local-tails-240'

test.describe('bi local tails 240', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('query edges, push clock, and reject note', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-240-${Date.now()}`
    const reportName = `E2E 切片240 ${label}`

    await loginAdmin(page)

    await page.goto('/ims/bi/query')
    await expect(page.locator('h1')).toContainText('自定义查询')
    await page.getByTestId('bi-query-limit').fill('0')
    await page.getByRole('button', { name: '执行查询' }).click()
    await expect(page.getByTestId('bi-query-form-error')).toContainText('行数上限须为 1~1000')
    await page.screenshot({ path: `${shotDir}/01-query-limit.png` })

    await page.getByTestId('bi-query-limit').fill('100')
    await page.getByTestId('bi-query-from').fill('2026-09-20')
    await page.getByRole('button', { name: '执行查询' }).click()
    await expect(page.getByTestId('bi-query-form-error')).toContainText('请同时填写开始和结束日期')
    await page.screenshot({ path: `${shotDir}/02-query-one-sided-date.png` })

    await page.getByTestId('bi-query-to').fill('2026-09-01')
    await page.getByRole('button', { name: '执行查询' }).click()
    await expect(page.getByTestId('bi-query-form-error')).toContainText('开始日期不能晚于结束日期')
    await page.screenshot({ path: `${shotDir}/03-query-flipped-date.png` })

    await page.locator('.tab', { hasText: '我的查询' }).click()
    await expect(page.getByTestId('bi-query-mine-empty')).toContainText('暂无保存的查询')
    await page.getByTestId('bi-query-name').fill('no-such-query-240')
    await page.getByTestId('bi-query-mine-search').click()
    await expect(page.getByTestId('bi-query-mine-empty')).toContainText('当前筛选下暂无查询')
    await page.screenshot({ path: `${shotDir}/04-query-filter-empty.png` })

    await page.goto('/ims/collect/metadata')
    await expect(page.locator('h1')).toContainText('元数据维护')
    await page.getByRole('button', { name: '新建实体' }).click()
    const createDrawer = page.locator('.drawer').filter({ hasText: '新建实体' })
    await createDrawer.locator('select').selectOption('oa_platform_account')
    await createDrawer.getByRole('button', { name: '创建' }).click()
    await expect(createDrawer).toBeHidden({ timeout: 15_000 })
    const entityRow = page.locator('tbody tr', { hasText: 'PLATFORM_ACCOUNT' })
    await expect(entityRow).toBeVisible()
    await entityRow.getByRole('button', { name: '字段配置' }).click()
    const fieldDrawer = page.locator('.drawer').filter({ hasText: '字段配置' })
    await fieldDrawer.locator('input[placeholder="列名"]').fill('account_no')
    await fieldDrawer.locator('input[placeholder="fieldCode"]').fill('account_no')
    await fieldDrawer.locator('input[placeholder="显示名"]').fill('账号编号')
    await fieldDrawer.getByRole('button', { name: '保存字段' }).click()
    await expect(fieldDrawer).toBeHidden({ timeout: 15_000 })

    await page.goto('/ims/bi/query')
    await page.locator('select').first().selectOption('PLATFORM_ACCOUNT')
    await expect(page.locator('label.chip').first()).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('bi-query-cond').fill('NO-SUCH-240')
    await page.getByRole('button', { name: '执行查询' }).click()
    await expect(page.getByTestId('bi-query-result-empty')).toContainText('当前条件下暂无数据', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/05-query-result-empty.png` })

    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(reportName)
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
    await subModal.locator('input.fld-in').first().fill(`时刻 ${label}`)
    await subModal.locator('input[type="number"]').fill(String(reportId))
    await subModal.getByTestId('bi-sub-push-time').fill('25:99')
    await subModal.getByRole('button', { name: '保存' }).click()
    await expect(subModal.getByTestId('bi-sub-push-error')).toContainText('推送时刻应为 HH:mm')
    await page.screenshot({ path: `${shotDir}/06-push-clock.png` })
    await subModal.getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/bi/report/subscribe?tab=share')
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const shareModal = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await shareModal.locator('input[type="number"]').first().fill(String(reportId))
    await shareModal.locator('input[type="number"]').nth(1).fill('7.5')
    await shareModal.getByRole('button', { name: '生成' }).click()
    await expect(page.getByTestId('bi-share-expire-error')).toContainText('1197')
    await page.screenshot({ path: `${shotDir}/07-share-fractional-days.png` })
    await shareModal.locator('input[type="number"]').nth(1).fill('7')
    await shareModal.locator('input[type="checkbox"]').check()
    await shareModal.getByRole('button', { name: '生成' }).click()
    await expect(page.locator('.tab.on')).toContainText('分享审批', { timeout: 15_000 })

    const pendingRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(pendingRow).toBeVisible()
    await pendingRow.getByTestId('bi-share-reject').click()
    const rejectModal = page.getByTestId('bi-share-reject-confirm')
    await rejectModal.getByTestId('bi-share-reject-ok').click()
    await expect(rejectModal.getByTestId('bi-share-reject-error')).toContainText('驳回说明必填')
    await rejectModal.getByTestId('bi-share-reject-note-input').fill('成本口径未确认')
    await rejectModal.getByTestId('bi-share-reject-ok').click()
    await expect(rejectModal).toBeHidden({ timeout: 15_000 })

    await page.locator('.tab', { hasText: '分享链接' }).click()
    const rejectedRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName }).filter({ hasText: '已驳回' })
    await expect(rejectedRow).toBeVisible({ timeout: 15_000 })
    await expect(rejectedRow.getByTestId('bi-share-reject-note')).toContainText('成本口径未确认')
    await page.screenshot({ path: `${shotDir}/08-share-reject-note.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
