import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-012 · 资产登记后按当前筛选重载，不把关键字收成新编号
 */
test.describe('asset register reload closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('two office assets stay visible after the second save', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toBeVisible()
    const stamp = Date.now().toString().slice(-6)
    const first = `登记甲${stamp}`
    const second = `登记乙${stamp}`

    async function register(name: string) {
      await page.getByTestId('corp-asset-create-btn').click()
      const drawer = page.locator('.drawer.on', { hasText: '资产登记' })
      await drawer.getByTestId('corp-asset-name').fill(name)
      const saved = page.waitForResponse(
        (res) => res.url().includes('/asset/ledger') && res.request().method() === 'POST',
      )
      await drawer.getByRole('button', { name: '保存' }).click()
      expect((await (await saved).json()).code).toBe(0)
      await expect(drawer).toBeHidden()
    }

    await register(first)
    await register(second)
    await expect(page.locator('tr', { hasText: first })).toBeVisible()
    await expect(page.locator('tr', { hasText: second })).toBeVisible()
  })
})
