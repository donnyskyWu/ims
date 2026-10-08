import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * Checklist **MASTER overview** 切片（acceptance · **纯 UI** · #43）
 * When: `/ims/master` KPI 卡片点击
 * Then: 跳转资源管理子路由 · h1 可见
 */
test.describe('master overview KPI navigation closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('company and platform account drill-down from overview', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/master')
    await expect(page.locator('h1')).toContainText('主数据台账')

    const companyCard = page.locator('a.card.il', { hasText: '公司主体' })
    await expect(companyCard.locator('.num')).not.toBeEmpty()
    await companyCard.click()
    await page.waitForURL(/\/ims\/corp\/resource\/company/, { timeout: 30_000 })
    await expect(page.locator('h1')).toBeVisible()

    await page.goto('/ims/master')
    const acctCard = page.locator('a.card.il', { hasText: '平台账号' })
    await acctCard.click()
    await page.waitForURL(/\/ims\/corp\/account\/douyin/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('抖音')
  })
})
