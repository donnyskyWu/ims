import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S12-05 切片**（acceptance · **纯 UI** · #40）
 * Given: UI 新建报表 + 敏感分享链接
 * When: 「分享审批」Tab 通过 / 驳回
 * Then: 分享链接 Tab 可见「已通过」+ 复制 / 「已驳回」
 */
test.describe('bi share approval closure S12', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  async function createReportViaUi(page: import('@playwright/test').Page, reportName: string) {
    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await expect(reportModal).toBeVisible()
    await reportModal.locator('input.fld-in').first().fill(reportName)
    const createReportResp = page.waitForResponse(
      (r) => r.url().includes('/bi/report') && r.request().method() === 'POST' && r.status() === 200,
    )
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    const createReportBody = (await (await createReportResp).json()) as {
      code: number
      data?: { id: number }
    }
    expect(createReportBody.code).toBe(0)
    return createReportBody.data!.id
  }

  async function createSensitiveShareViaUi(
    page: import('@playwright/test').Page,
    reportId: number,
    reportName: string,
  ) {
    await page.goto('/ims/bi/report/subscribe?tab=share')
    await expect(page.locator('h1')).toContainText('订阅与分享')
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const shareModal = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await expect(shareModal).toBeVisible()
    await shareModal.locator('input[type="number"]').first().fill(String(reportId))
    await shareModal.locator('input[type="checkbox"]').check()
    const createShareResp = page.waitForResponse(
      (r) => r.url().includes('/share-link') && r.request().method() === 'POST' && r.status() === 200,
    )
    await shareModal.getByRole('button', { name: '生成' }).click()
    const shareBody = (await (await createShareResp).json()) as {
      code: number
      data?: { approvalStatus?: string }
    }
    expect(shareBody.code).toBe(0)
    expect(shareBody.data?.approvalStatus).toBe('PENDING')

    const shareRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(shareRow).toBeVisible({ timeout: 15_000 })
    await expect(shareRow).toContainText('待审批')
  }

  test('approve pending sensitive share in approval tab', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-approve-${Date.now()}`
    const reportName = `E2E 敏感分享 ${label}`

    await loginAdmin(page)
    const reportId = await createReportViaUi(page, reportName)
    await createSensitiveShareViaUi(page, reportId, reportName)

    await page.locator('.tab', { hasText: '分享审批' }).click()
    await expect(page.locator('.tab.on')).toContainText('分享审批')

    const pendingRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await expect(pendingRow).toContainText('待审批')

    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/share-approval/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await pendingRow.getByText('通过', { exact: true }).click()
    const approveBody = (await (await approveResp).json()) as {
      code: number
      data?: { approvalStatus?: string }
    }
    expect(approveBody.code).toBe(0)
    expect(approveBody.data?.approvalStatus).toBe('APPROVED')

    await expect(pendingRow).toHaveCount(0, { timeout: 15_000 })

    await page.locator('.tab', { hasText: '分享链接' }).click()
    const approvedRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(approvedRow).toContainText('已通过', { timeout: 15_000 })
    await expect(approvedRow.getByText('复制链接')).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('reject pending sensitive share in approval tab', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-reject-${Date.now()}`
    const reportName = `E2E 驳回分享 ${label}`

    await loginAdmin(page)
    const reportId = await createReportViaUi(page, reportName)
    await createSensitiveShareViaUi(page, reportId, reportName)

    await page.locator('.tab', { hasText: '分享审批' }).click()
    const pendingRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })

    await pendingRow.getByText('驳回', { exact: true }).click()
    const rejectModal = page.getByTestId('bi-share-reject-confirm')
    await expect(rejectModal).toBeVisible()
    await rejectModal.getByTestId('bi-share-reject-ok').click()
    await expect(rejectModal.getByTestId('bi-share-reject-error')).toContainText('驳回说明必填')
    await rejectModal.getByTestId('bi-share-reject-note-input').fill('成本口径未确认')
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/share-approval/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await rejectModal.getByTestId('bi-share-reject-ok').click()
    const rejectBody = (await (await rejectResp).json()) as {
      code: number
      data?: { approvalStatus?: string; approvalNote?: string }
    }
    expect(rejectBody.code).toBe(0)
    expect(rejectBody.data?.approvalStatus).toBe('REJECTED')
    expect(rejectBody.data?.approvalNote).toBe('成本口径未确认')

    await page.locator('.tab', { hasText: '分享链接' }).click()
    const rejectedRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(rejectedRow).toContainText('已驳回', { timeout: 15_000 })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
