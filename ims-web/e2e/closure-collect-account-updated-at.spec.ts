import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * B069：数据采集 · 竞品账号配置「更新时间」按北京时间显示。
 * 纯 UI 新建一行，核对 yyyy-MM-dd HH:mm 与当前东八区时刻。
 */
test.describe('collect account updatedAt shanghai', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('new competitor account shows Beijing update time', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = `b069-${Date.now().toString(36)}`

    await loginAdmin(page)
    await page.goto('/ims/collect/external/account')
    await expect(page.locator('h1')).toHaveText('竞品账号配置')

    await page.getByTestId('acct-create').click()
    const drawer = page.locator('.drawer.on')
    await drawer.getByTestId('acct-form-name').fill(stamp)
    await drawer.getByTestId('acct-form-id').fill(`id-${stamp}`)
    await drawer.getByTestId('acct-save').click()

    await page.getByTestId('acct-name').fill(stamp)
    await page.getByTestId('acct-query').click()
    const row = page.locator('tr', { hasText: stamp })
    const updated = row.getByTestId('acct-updated')
    await expect(updated).toHaveText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    const shown = (await updated.innerText()).trim()
    const matched = shown.match(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$/)
    expect(matched).toBeTruthy()
    const shownMs = Date.parse(`${matched![1]}T${matched![2]}:00+08:00`)
    expect(Math.abs(Date.now() - shownMs)).toBeLessThan(3 * 60 * 1000)

    expect(pageErrors).toEqual([])
  })
})
