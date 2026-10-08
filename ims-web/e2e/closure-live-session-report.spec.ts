import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S2 窄切片**（#56 · 纯 UI）
 * 登记 → 风控 → 下播提交/核准 · 19 位场次 ID · 列表可见
 */
test.describe('live session register report closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('register risk check report confirm shows session in list', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 88_000,
      refundAmount: 1_000,
    })

    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)

    await page.goto('/ims/live/sessions')
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const listBody = (await (await listResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; reportEntryStatus?: string }> }
    }
    expect(listBody.code).toBe(0)
    const hit = listBody.data?.list?.find((r) => r.sessionCode === sessionCode)
    expect(hit?.reportEntryStatus).toBe('CONFIRMED')

    const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(uiRow).toBeVisible({ timeout: 15_000 })
    await uiRow.locator('td.mono').first().click()
    const detailDrawer = page.locator('.drawer').filter({ hasText: sessionCode })
    await expect(detailDrawer).toBeVisible({ timeout: 15_000 })
    await expect(detailDrawer).toContainText('下播与 GMV')
    expect(pageErrors).toEqual([])
  })
})
