import { test, expect } from '@playwright/test'

test.describe('workbench smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then workbench greeting and flowTodoCount card', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)

    const flowCard = page.locator('.card.stat').filter({ hasText: '流程待办' })
    await expect(flowCard).toBeVisible()
    await expect(flowCard.locator('.n')).toHaveText(/\d+/)

    await expect(page.getByText('流程待办', { exact: true }).first()).toBeVisible()
    await expect(page.locator('.tbl-wrap table').first()).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
