import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-001 · 新建公司，并确认种子公司出现在列表
 */
test.describe('company create closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('seed company is listed and empty create prompts required fields', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/company')
    await expect(page.locator('h1')).toContainText('公司管理')
    await expect(page.locator('tr', { hasText: 'E2E内容公司' })).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('corp-company-create').click()
    const drawer = page.locator('.drawer.on', { hasText: '新建公司' })
    await drawer.getByTestId('corp-company-save').click()
    await expect(drawer.getByTestId('corp-company-error-name')).toHaveText('必填项，请填写')
    await expect(page.getByTestId('corp-company-toast')).toContainText('请先完成必填项')

    const stamp = Date.now().toString().slice(-6)
    const name = `UI公司${stamp}`
    await drawer.getByTestId('corp-company-name').fill(name)
    await drawer.getByTestId('corp-company-credit').fill(`91${stamp}MA0001`)
    await drawer.getByTestId('corp-company-capacity').fill('1')
    await drawer.getByTestId('corp-company-save').click()
    await expect(page.getByTestId('corp-company-toast')).toHaveText('公司已创建')
    const row = page.locator('tr', { hasText: name })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('0 / 1')
    await expect(row).toContainText('启用')
  })
})
