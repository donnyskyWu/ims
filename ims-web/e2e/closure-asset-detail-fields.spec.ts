import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-013 · 资产编号可点开详情，信息卡含类型和绑定账号数 */
test.describe('asset detail fields closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('clicking the asset code opens a detail card with type and bind count', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    const stamp = Date.now().toString().slice(-6)
    const code = `AS-DTL-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on', { hasText: '资产登记' })
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`详情设备${stamp}`)
    const saved = page.waitForResponse(
      (res) => res.url().includes('/asset/ledger') && res.request().method() === 'POST' && res.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect(((await (await saved).json()) as { code: number }).code).toBe(0)

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await row.getByTestId('corp-asset-code-link').click()
    const detail = page.locator('.drawer.on', { hasText: '资产详情' })
    await expect(detail.getByTestId('corp-asset-detail-type')).toHaveText('办公设备')
    await expect(detail.getByTestId('corp-asset-detail-bind')).toHaveText('绑定账号（0）')
    await expect(detail).toContainText(code)
    await expect(detail).toContainText('待审核')
  })
})
