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

  test('filter edges on company credit, sim phone, and phone model', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/master')
    await expect(page.locator('h1')).toContainText('主数据台账')
    await expect(page.getByTestId('master-overview-updated')).toBeVisible()
    await expect(page.locator('a.card.il .csub').first()).not.toBeEmpty()

    await page.goto('/ims/corp/resource/company')
    await expect(page.locator('h1')).toContainText('公司管理')
    await page.getByTestId('master-company-credit').fill('___no_such_credit___')
    const companyFiltered = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/company/page') && r.url().includes('creditCode=') && r.status() === 200,
    )
    await page.locator('form.qbar button[type="submit"]').click()
    await companyFiltered
    await expect(page.locator('.empty .et')).toContainText('没有符合筛选的记录')
    const companyReset = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/company/page') && !r.url().includes('creditCode=') && r.status() === 200,
    )
    await page.locator('form.qbar button', { hasText: '重置' }).click()
    await companyReset
    await expect(page.locator('.empty .et', { hasText: '没有符合筛选的记录' })).toHaveCount(0)

    await page.goto('/ims/corp/resource/realname')
    await page.getByTestId('master-realname-idtype').selectOption({ label: '护照' })
    const personFiltered = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/realname/page') && r.url().includes('idType=PASSPORT') && r.status() === 200,
    )
    await page.locator('form.qbar button[type="submit"]').click()
    await personFiltered

    await page.goto('/ims/corp/resource/sim-card')
    await expect(page.getByTestId('master-sim-operator')).toBeVisible()
    await expect(page.getByTestId('master-sim-status')).toBeVisible()
    await page.locator('input[placeholder="完整手机号"]').fill('12345')
    await page.locator('form.qbar button[type="submit"]').click()
    await expect(page.locator('.empty .et')).toContainText('请输入完整 11 位手机号')

    await page.goto('/ims/corp/device/phone')
    await expect(page.locator('input[placeholder="设备编号 / 型号"]')).toBeVisible()
    await page.getByTestId('master-phone-model').fill('___no_such_model___')
    const phoneFiltered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/phone/page') && r.url().includes('phoneModel=') && r.status() === 200,
    )
    await page.locator('form.qbar button[type="submit"]').click()
    await phoneFiltered
    await expect(page.locator('.empty .et')).toContainText('没有符合筛选的记录')
  })
})
