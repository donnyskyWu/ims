import { test, expect } from '@playwright/test'

/** Checklist 逐步闭环 · 超时督办 urge → remindCount+1 */
test.describe('flow timeout urge closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('urge on timeout tab increments remind count', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    page.on('dialog', (d) => {
      if (d.type() === 'prompt') d.accept('E2E 督办')
      else d.accept()
    })

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await page.getByRole('button', { name: '超时督办' }).click()
    await expect(page.getByText('时长分布：')).toBeVisible({ timeout: 15_000 })

    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '提醒次数' }) })
    await expect(timeoutTable).toBeVisible()
    const firstRow = timeoutTable.locator('tbody tr').first()
    await expect(firstRow).not.toContainText('暂无')
    const remindCell = firstRow.locator('td').nth(5)
    const before = parseInt((await remindCell.innerText()).trim(), 10)

    const urgeResp = page.waitForResponse(
      (r) => r.url().includes('/flow/timeout/') && r.url().includes('/urge') && r.request().method() === 'PUT',
    )
    await firstRow.getByText('督办').click()
    const resp = await urgeResp
    expect((await resp.json()).code).toBe(0)
    await expect(remindCell).toHaveText(String(before + 1), { timeout: 15_000 })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
