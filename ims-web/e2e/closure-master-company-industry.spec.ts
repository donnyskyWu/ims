import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * Checklist MASTER 公司行业字典边角（acceptance · 纯 UI · #192）
 * When: 字典 dict_industry 可见，公司台账按行业筛选
 * Then: 无匹配时空态；重置后回到全部公司
 */
test.describe('master company industry dict filter closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('industry dictionary filters the company ledger to an empty state', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/system/dict')
    await expect(page.locator('h1')).toContainText('字典管理')
    const industryType = page.locator('tr', { hasText: 'dict_industry' })
    await expect(industryType).toBeVisible()
    await industryType.click()
    await expect(page.getByRole('cell', { name: 'SPORT', exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: '体育', exact: true })).toBeVisible()
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-industry-dict.png',
      fullPage: true,
    })

    await page.goto('/ims/corp/resource/company')
    await expect(page.locator('h1')).toContainText('公司管理')
    await expect(page.getByTestId('master-company-industry-hint')).toContainText('dict_industry')
    const industry = page.getByTestId('master-company-industry')
    await expect(industry.locator('option', { hasText: '体育' })).toHaveCount(1)
    await industry.selectOption({ label: '体育' })
    const filtered = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/resource/company/page') &&
        response.url().includes('industry=SPORT') &&
        response.status() === 200,
    )
    await page.locator('form.qbar button[type="submit"]').click()
    await filtered
    await expect(page.locator('.empty .et')).toContainText('没有符合筛选的记录')
    await expect(page.locator('.empty .es')).toContainText('这个行业下没有公司')
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-company-industry-empty.png',
      fullPage: true,
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-company-industry-empty-mobile.png',
      fullPage: true,
    })
    await page.setViewportSize({ width: 1280, height: 800 })

    const reset = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/resource/company/page') &&
        !response.url().includes('industry=') &&
        response.status() === 200,
    )
    await page.locator('form.qbar button', { hasText: '重置' }).click()
    await reset
    await expect(page.locator('.empty .et', { hasText: '没有符合筛选的记录' })).toHaveCount(0)
    await expect(page.locator('table')).toBeVisible()
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-company-industry-reset.png',
      fullPage: true,
    })
  })
})
