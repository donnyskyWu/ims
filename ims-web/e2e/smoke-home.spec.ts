import { test, expect } from '@playwright/test'

test.describe('home dashboard smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then home heading and four KPI cards', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')

    const kpiLabels = ['账号数', '今日作品', '待办任务', '采集异常']
    for (const label of kpiLabels) {
      const card = page.locator('.card.stat').filter({ hasText: label })
      await expect(card).toBeVisible()
      await expect(card.locator('.n')).not.toBeEmpty()
    }

    await expect(page.locator('.sec').filter({ hasText: '快捷入口' })).toBeVisible()
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
