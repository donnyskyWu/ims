import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-053 · 侧栏和菜单搜索能进入离职归还，管理员可手动补建 */
test.describe('resign return navigation closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('menu search finds the return page and empty generate prompts required fields', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/home')
    const search = page.getByPlaceholder('搜索菜单…')
    await search.fill('离职')
    await page.locator('.nav-item', { hasText: '离职归还单' }).click()
    await expect(page.locator('h1')).toHaveText('离职归还', { timeout: 15_000 })
    await expect(page).toHaveURL(/\/ims\/account\/return/)

    await search.fill('归还单')
    await expect(page.locator('.nav-item', { hasText: '离职归还单' })).toBeVisible()

    await page.getByTestId('return-generate-open').click()
    const drawer = page.locator('.drawer.on', { hasText: '手动补建归还单' })
    await drawer.getByTestId('return-generate-user').selectOption('')
    await drawer.getByTestId('return-generate-date').fill('')
    await drawer.getByTestId('return-generate-save').click()
    await expect(drawer.getByTestId('return-generate-error')).toHaveText('必填项，请填写')
  })
})
