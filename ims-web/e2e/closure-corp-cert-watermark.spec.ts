import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/** Checklist **E2E-S6-03**（#55 · 纯 UI）· 证件查看带水印、不出原图 */
test.describe('corp certificate watermark closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('certificate view shows masked number and admin watermark', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    const listResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/resource/certificate/page') &&
        r.url().includes('holderName=E2E-Cert-Watermark') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.locator('input[placeholder="持有人"]').fill('E2E-Cert-Watermark')
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    const listBody = (await (await listResp).json()) as {
      code: number
      data?: { list?: Array<{ holderName?: string; certNoMasked?: string }> }
    }
    expect(listBody.code).toBe(0)
    expect(listBody.data?.list?.some((r) => r.holderName === 'E2E-Cert-Watermark')).toBe(true)

    const row = page.locator('tbody tr', { hasText: 'E2E-Cert-Watermark' }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    const viewResp = page.waitForResponse(
      (r) => r.url().includes('/certificate/') && r.url().includes('/view') && r.status() === 200,
    )
    await row.getByTestId('corp-cert-view-btn').click()
    const viewBody = (await (await viewResp).json()) as {
      code: number
      data?: { watermarkText?: string; indexInfo?: { certNoMasked?: string } }
    }
    expect(viewBody.code).toBe(0)
    expect(viewBody.data?.watermarkText).toMatch(/admin/i)
    const masked = viewBody.data?.indexInfo?.certNoMasked ?? ''
    expect(masked.length).toBeGreaterThan(0)
    expect(masked).not.toBe('110101199888011234')

    const drawer = page.locator('.drawer.on').filter({ hasText: '证件查看' })
    await expect(drawer).toBeVisible()
    const hint = page.getByTestId('corp-cert-watermark-hint')
    await expect(hint).toContainText('admin')
    await expect(hint).toContainText('本接口不返回原图')
    expect(pageErrors).toEqual([])
  })
})
