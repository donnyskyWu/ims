import { test, expect } from '@playwright/test'

test.describe('alert rule trial smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then alert rule page and optional trial toast', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')
    await expect(page.locator('.tbl-wrap table')).toBeVisible()
    await expect(page.locator('.tbl-wrap thead th', { hasText: '操作' })).toBeVisible()

    const trialBtn = page.locator('tbody button.btn-txt').filter({ hasText: '试跑' }).and(page.locator(':not([disabled])'))
    const trialCount = await trialBtn.count()
    if (trialCount > 0) {
      await trialBtn.first().click()
      await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })
    }

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
