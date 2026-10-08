import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.describe('HOME dashboard KPI closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('refresh KPIs, account drill-down, work-task shortcut', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')

    const worksCard = page.locator('.card.stat').filter({ hasText: '今日作品' })
    await expect(worksCard.locator('.n')).toContainText('数据延迟')
    await expect(worksCard.locator('.d')).toContainText('Football')

    const refresh = page.getByRole('button', { name: '刷新' })
    await expect(refresh).toBeVisible()
    const dashResp = page.waitForResponse(
      (r) => r.url().includes('/home/dashboard') && r.request().method() === 'GET' && r.status() === 200,
    )
    await refresh.click()
    await dashResp

    const accountsCard = page.locator('.card.stat').filter({ hasText: '账号数' })
    await accountsCard.click()
    await page.waitForURL(/\/ims\/corp\/account\/douyin/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('抖音')

    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')

    const shortcut = page.locator('.card.hov').filter({ hasText: '登记工作任务' })
    await expect(shortcut).toBeVisible()
    await shortcut.click()
    await page.waitForURL(/\/ims\/content\/work-task/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('工作任务登记')
  })
})
