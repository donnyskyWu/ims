import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S12-05 EXPIRED 切片**（acceptance · **纯 UI** · #41）
 * Given: UI 新建报表 + 敏感分享 → 审批通过
 * When: 「分享链接」Tab「撤销」并确认
 * Then: 行可见「已过期」· 无「复制链接」
 */
test.describe('bi share expired closure S12', () => {
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

  test('mark approved sensitive share as expired', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-expired-${Date.now()}`
    const reportName = `E2E 过期分享 ${label}`

    await loginAdmin(page)
    const reportId = await createReportViaUi(page, reportName)
    await createSensitiveShareViaUi(page, reportId, reportName)

    await page.locator('.tab', { hasText: '分享审批' }).click()
    const pendingRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
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

    await page.locator('.tab', { hasText: '分享链接' }).click()
    const approvedRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName })
    await expect(approvedRow).toContainText('已通过', { timeout: 15_000 })
    await expect(approvedRow.getByText('复制链接')).toBeVisible()
    await expect(approvedRow.getByTestId('bi-share-revoke')).toBeVisible()

    await approvedRow.getByTestId('bi-share-revoke').click()
    const revokeConfirm = page.getByTestId('bi-share-revoke-confirm')
    await expect(revokeConfirm).toBeVisible()
    await revokeConfirm.getByRole('button', { name: '取消' }).click()
    await expect(revokeConfirm).toBeHidden()
    await expect(approvedRow.getByText('复制链接')).toBeVisible()

    const expireResp = page.waitForResponse(
      (r) => r.url().includes('/share-approval/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await approvedRow.getByTestId('bi-share-revoke').click()
    await page.getByTestId('bi-share-revoke-ok').click()
    const expireBody = (await (await expireResp).json()) as {
      code: number
      data?: { approvalStatus?: string }
    }
    expect(expireBody.code).toBe(0)
    expect(expireBody.data?.approvalStatus).toBe('EXPIRED')

    await expect(approvedRow).toContainText('已过期', { timeout: 15_000 })
    await expect(approvedRow.getByText('复制链接')).toHaveCount(0)
    await expect(approvedRow).toContainText('链接已失效')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
