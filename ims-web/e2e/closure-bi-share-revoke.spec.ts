import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist 切片（acceptance · 纯 UI · #176）
 * Given: 分享链接列表与一枚生效链接
 * When: 关键字无命中、有效期越界、撤销确认、用令牌打开预览
 * Then: 空列表、1197 红字、撤销后「已过期」、预览空态（空令牌 / 未知 / 待审批 / 已过期）
 */
test.describe('bi share revoke and empty closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty filter, expire bound, revoke, and token gates', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-revoke-${Date.now()}`
    const reportName = `E2E 撤销分享 ${label}`

    await loginAdmin(page)
    await page.goto('/ims/bi/report/subscribe?tab=share')
    await expect(page.locator('h1')).toContainText('订阅与分享')
    await page.getByTestId('bi-share-keyword').fill('no-such-share-zzz')
    await expect(page.getByTestId('bi-share-empty')).toContainText('暂无分享链接')
    await page.getByTestId('bi-share-keyword').fill('')

    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(reportName)
    const createReportResp = page.waitForResponse(
      (r) => r.url().includes('/bi/report') && r.request().method() === 'POST' && r.status() === 200,
    )
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    const createReportBody = (await (await createReportResp).json()) as { code: number; data?: { id: number } }
    expect(createReportBody.code).toBe(0)
    const reportId = createReportBody.data!.id

    await page.goto('/ims/bi/report/subscribe?tab=share')
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const shareModal = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await shareModal.locator('input[type="number"]').first().fill(String(reportId))
    await shareModal.locator('input[type="number"]').nth(1).fill('3')
    await shareModal.getByRole('button', { name: '生成' }).click()
    await expect(page.getByTestId('bi-share-expire-error')).toContainText('1197')
    await expect(shareModal).toBeVisible()

    await shareModal.locator('input[type="number"]').nth(1).fill('7')
    await shareModal.locator('input[type="checkbox"]').check()
    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/share-link') && r.request().method() === 'POST' && r.status() === 200,
    )
    await shareModal.getByRole('button', { name: '生成' }).click()
    const pendingBody = (await (await pendingResp).json()) as {
      code: number
      data?: { approvalStatus?: string; linkToken?: string }
    }
    expect(pendingBody.code).toBe(0)
    expect(pendingBody.data?.approvalStatus).toBe('PENDING')
    const pendingToken = pendingBody.data!.linkToken!

    await page.goto(`/ims/bi/report/preview?token=${pendingToken}`)
    await expect(page.getByTestId('bi-share-gate')).toContainText('待审批', { timeout: 15_000 })

    await page.goto('/ims/bi/report/subscribe?tab=share')
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const approvedModal = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await approvedModal.locator('input[type="number"]').first().fill(String(reportId))
    await approvedModal.locator('input[type="number"]').nth(1).fill('7')
    const approvedResp = page.waitForResponse(
      (r) => r.url().includes('/share-link') && r.request().method() === 'POST' && r.status() === 200,
    )
    await approvedModal.getByRole('button', { name: '生成' }).click()
    const approvedBody = (await (await approvedResp).json()) as {
      code: number
      data?: { approvalStatus?: string; linkToken?: string }
    }
    expect(approvedBody.code).toBe(0)
    expect(approvedBody.data?.approvalStatus).toBe('APPROVED')
    const token = approvedBody.data!.linkToken!

    await page.goto(`/ims/bi/report/preview?token=${token}`)
    await expect(page.getByTestId('bi-share-scope-hint')).toContainText('数据权限', { timeout: 15_000 })
    await expect(page.getByTestId('bi-share-gate')).toHaveCount(0)

    await page.goto('/ims/bi/report/subscribe?tab=share')
    const row = page.locator('.tbl-wrap tbody tr', { hasText: reportName }).filter({ hasText: '已通过' }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByTestId('bi-share-revoke').click()
    const confirm = page.getByTestId('bi-share-revoke-confirm')
    await confirm.getByRole('button', { name: '取消' }).click()
    await expect(row.getByText('复制链接')).toBeVisible()

    const revokeResp = page.waitForResponse(
      (r) => r.url().includes('/share-approval/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await row.getByTestId('bi-share-revoke').click()
    await page.getByTestId('bi-share-revoke-ok').click()
    const revokeBody = (await (await revokeResp).json()) as { code: number; data?: { approvalStatus?: string } }
    expect(revokeBody.code).toBe(0)
    expect(revokeBody.data?.approvalStatus).toBe('EXPIRED')
    const expiredRow = page.locator('.tbl-wrap tbody tr', { hasText: reportName }).filter({ hasText: '已过期' }).first()
    await expect(expiredRow).toBeVisible({ timeout: 15_000 })
    await expect(expiredRow).toContainText('链接已失效')
    await expect(expiredRow.getByText('复制链接')).toHaveCount(0)

    await page.goto(`/ims/bi/report/preview?token=${token}`)
    await expect(page.getByTestId('bi-share-gate')).toContainText('已过期', { timeout: 15_000 })

    await page.goto('/ims/bi/report/preview?token=')
    await expect(page.getByTestId('bi-share-gate')).toContainText('分享链接为空')

    await page.goto('/ims/bi/report/preview?token=missing-token-xyz')
    await expect(page.getByTestId('bi-share-gate')).toContainText('分享链接不存在')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
