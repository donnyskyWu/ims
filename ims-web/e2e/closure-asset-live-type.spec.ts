import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-023 · 直播设备登记类型必填，只能选直播或拍摄
 */
test.describe('live asset type required closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty type blocks save, then shooting device can be registered', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/device/live')
    await page.getByTestId('corp-asset-create-btn').click()
    const drawer = page.locator('.drawer.on', { hasText: '资产登记' })
    const type = drawer.getByTestId('corp-asset-type')
    await expect(type).toHaveValue('')
    await expect(type.locator('option')).toHaveCount(3)
    await drawer.getByTestId('corp-asset-name').fill(`直播类型${Date.now().toString().slice(-6)}`)
    await drawer.getByTestId('corp-asset-save').click()
    await expect(drawer.getByTestId('corp-asset-type-error')).toHaveText('必填项，请填写')
    await type.selectOption('SHOOT')
    const saved = page.waitForResponse(
      (res) => res.url().includes('/asset/ledger') && res.request().method() === 'POST',
    )
    await drawer.getByTestId('corp-asset-save').click()
    const body = await (await saved).json()
    expect(body.code).toBe(0)
    expect(body.data.assetType).toBe('SHOOT')
    expect(body.data.status).toBe('PENDING_REVIEW')
  })
})
