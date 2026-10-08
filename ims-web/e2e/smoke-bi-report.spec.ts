import { test, expect } from '@playwright/test'

test.describe('bi report center smoke S12 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then report center heading', async ({ page }) => {
    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })
    await page.goto('/ims/bi/report')
    await expect(page.locator('h1')).toContainText('报表中心')
  })
})
