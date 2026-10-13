import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

/**
 * BUG-060：没有角色编辑权限时，角色页右上角不出现钉钉岗位输入。
 * 来源展示为「手工」，钉钉同步来源为「钉钉自动」。
 */
test.describe('role page position input follows edit permission', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('reader does not see the position input, admin still does', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = String(Date.now()).slice(-6)
    const roleName = `角色只读${stamp}`
    const roleKey = `e2e_rr_${stamp}`
    const username = `只读角色${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/system/role')
    await expect(page.getByTestId('role-position-input')).toBeVisible()
    await expect(page.getByTestId('role-filter-source').locator('option[value="MANUAL"]')).toHaveText('手工')
    await expect(page.getByTestId('role-filter-source').locator('option[value="DINGTALK_AUTO"]')).toHaveText('钉钉自动')
    await expect(page.getByTestId('role-row').filter({ hasText: 'sys:admin' })).toContainText('手工')

    await page.getByTestId('role-create-open').click()
    await page.getByTestId('role-create-name').fill(roleName)
    await page.getByTestId('role-create-key').fill(roleKey)
    await page.getByTestId('role-create-scope').selectOption('ALL')
    await page.getByTestId('role-create-save').click()
    await expect(page.getByTestId('role-row').filter({ hasText: roleKey })).toBeVisible()

    const row = page.getByTestId('role-row').filter({ hasText: roleName })
    await row.getByTestId('role-edit').click()
    const perm = page.getByTestId('role-perm-row').filter({ hasText: 'system:role:query' })
    await perm.locator('input[type="checkbox"]').check()
    const saved = page.waitForResponse(
      (r) => r.url().includes('/perm-detail') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('role-save').click()
    expect(((await (await saved).json()) as { code: number }).code).toBe(0)

    await page.goto('/ims/system/user')
    await page.getByTestId('sys-user-create-open').click()
    const drawer = page.locator('.drawer.on')
    await drawer.getByTestId('sys-user-form-username').fill(username)
    await drawer.getByTestId('sys-user-form-nickname').fill(username)
    await drawer.getByTestId('sys-user-form-mobile').fill(`137${stamp}02`)
    await drawer.getByTestId('sys-user-form-roles').selectOption([{ label: `${roleName}（手工）` }])
    await drawer.getByTestId('sys-user-form-password').fill('Admin@123')
    await drawer.getByTestId('sys-user-form-save').click()
    await expect(drawer).toBeHidden({ timeout: 15_000 })

    await logout(page)
    await loginAs(page, username)
    await page.goto('/ims/system/role')
    await expect(page.getByTestId('role-row').first()).toBeVisible()
    await expect(page.getByTestId('role-position-input')).toHaveCount(0)
    await expect(page.getByTestId('role-filter-source').locator('option[value="MANUAL"]')).toHaveText('手工')
    await expect(page.getByTestId('role-filter-source').locator('option[value="DINGTALK_AUTO"]')).toHaveText('钉钉自动')
    await expect(page.getByTestId('role-create-open')).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
