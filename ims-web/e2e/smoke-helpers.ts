import { expect, type Page } from '@playwright/test'

const ADMIN_USER = 'admin'
const ADMIN_PASS = 'Admin@123'

/** 登录后进列表页：h1 + 表格可见；仅断言未捕获 pageerror（避免 API 噪声 console.error）。 */
export async function smokeListAfterLogin(
  page: Page,
  path: string,
  heading: string | RegExp,
) {
  const pageErrors: string[] = []
  page.on('pageerror', (err) => pageErrors.push(err.message))

  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill(ADMIN_USER)
  await page.locator('input[type="password"]').fill(ADMIN_PASS)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL(/\/ims\//, { timeout: 30_000 })

  await page.goto(path)
  const h1 = page.locator('h1')
  if (typeof heading === 'string') {
    await expect(h1).toContainText(heading)
  } else {
    await expect(h1).toHaveText(heading)
  }
  await expect(page.locator('.tbl-wrap table')).toBeVisible()

  expect(pageErrors, pageErrors.join('\n')).toEqual([])
}
