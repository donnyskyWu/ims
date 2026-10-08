import { test, expect } from '@playwright/test'

/** Checklist 逐步闭环 · S11 创建规则 → 试跑 → hitCount+1 + toast */
test.describe('alert rule create trial closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('create enabled rule trial then hit count increases', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    const code = `e2e.alert.${Date.now()}`

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 规则 ${code}`)
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const row = page.locator('tbody tr').filter({ hasText: code })
    await expect(row).toBeVisible({ timeout: 15_000 })
    const hitCell = row.locator('td.num').nth(1)
    await expect(hitCell).toHaveText('0')

    await row.getByRole('button', { name: '试跑' }).click()
    await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })
    await expect(hitCell).toHaveText('1', { timeout: 15_000 })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
