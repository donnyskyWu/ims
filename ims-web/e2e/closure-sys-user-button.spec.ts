import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

async function grantMenu(page: Page, roleName: string, permCode: string) {
  await page.goto('/ims/system/role')
  const row = page.getByTestId('role-row').filter({ hasText: roleName })
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.getByTestId('role-edit').click()
  const perm = page.getByTestId('role-perm-row').filter({ hasText: permCode })
  await perm.locator('input[type="checkbox"]').check()
  const saved = page.waitForResponse(
    (r) => r.url().includes('/perm-detail') && r.request().method() === 'PUT' && r.status() === 200,
  )
  await page.getByTestId('role-save').click()
  expect(((await (await saved).json()) as { code: number }).code).toBe(0)
}

/**
 * BUG-057：只授予用户·新增 / 用户·编辑时，用户页要出现对应按钮，
 * 并能为表单读到角色列表和组织人员，不要求角色菜单或组织菜单。
 */
test.describe('user add and edit buttons follow button perms', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('add and edit buttons show and dependency lists load', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = String(Date.now()).slice(-6)
    const roleName = `用户按钮${stamp}`
    const roleKey = `e2e_ub_${stamp}`
    const username = `按钮用户${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/system/role')
    await page.getByTestId('role-create-open').click()
    await page.getByTestId('role-create-name').fill(roleName)
    await page.getByTestId('role-create-key').fill(roleKey)
    await page.getByTestId('role-create-scope').selectOption('ALL')
    await page.getByTestId('role-create-save').click()
    await expect(page.getByTestId('role-row').filter({ hasText: roleKey })).toBeVisible()

    await grantMenu(page, roleName, 'system:user:query')
    await grantMenu(page, roleName, 'system:user:add')
    await grantMenu(page, roleName, 'system:user:edit')

    await page.goto('/ims/system/user')
    await page.getByTestId('sys-user-create-open').click()
    const drawer = page.locator('.drawer.on')
    await drawer.getByTestId('sys-user-form-username').fill(username)
    await drawer.getByTestId('sys-user-form-nickname').fill(username)
    await drawer.getByTestId('sys-user-form-mobile').fill(`137${stamp}01`)
    await drawer.getByTestId('sys-user-form-roles').selectOption([{ label: roleName }])
    await drawer.getByTestId('sys-user-form-password').fill('Admin@123')
    await drawer.getByTestId('sys-user-form-save').click()
    await expect(drawer).toBeHidden({ timeout: 15_000 })

    await logout(page)
    await loginAs(page, username)
    const roles = page.waitForResponse(
      (r) => r.url().includes('/system/role/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    const org = page.waitForResponse(
      (r) => r.url().includes('/auth/org/users') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/system/user')
    expect(((await (await roles).json()) as { code: number }).code).toBe(0)
    expect(((await (await org).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('sys-user-create-open')).toBeVisible()
    await expect(page.getByTestId('sys-user-edit').first()).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '角色' })).toHaveCount(0)
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '组织架构' })).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
