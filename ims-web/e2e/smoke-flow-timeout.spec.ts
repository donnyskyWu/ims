import { test, expect } from '@playwright/test'

test.describe('flow timeout tab smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then timeout tab metrics and table', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '超时督办' }).click()

    await expect(page.getByText('月度超时率')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/超时节点/)).toBeVisible()

    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '实例单号' }) })
    await expect(timeoutTable).toBeVisible()
    await expect(timeoutTable.locator('thead th', { hasText: '超时时长(分)' })).toBeVisible()

    const bodyText = await timeoutTable.locator('tbody').innerText()
    expect(bodyText.length).toBeGreaterThan(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
