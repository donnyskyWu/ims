import { test, expect } from '@playwright/test'

test.describe('master overview smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then master heading and KPI cards', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/master')
    await expect(page.locator('h1')).toContainText('主数据台账')

    const labels = ['公司主体', '实名人', 'SIM 卡', '证件档案', '工作手机', '平台账号']
    for (const label of labels) {
      const card = page.locator('a.card.il', { hasText: label })
      await expect(card).toBeVisible()
      await expect(card.locator('.num')).not.toBeEmpty()
    }

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
