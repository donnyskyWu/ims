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
 * BUG-01 / BUG-02：侧栏与按钮按角色权限过滤；无角色 fail-closed；角色页可新建。
 * 数据全部从页面创建。
 */
test.describe('system permission and role create', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('admin keeps menus, no-role is closed, union and new role form', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = String(Date.now()).slice(-6)
    const userCode = `e2e_u_${stamp}`
    const roleCode = `e2e_r_${stamp}`
    const noneCode = `e2e_n_${stamp}`
    const noneName = `无角色${stamp}`
    const unionName = `并集${stamp}`

    await loginAdmin(page)
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '用户' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '直播管理' })).toBeVisible()
    await expect(page.getByTestId('sys-user-create-open')).toBeVisible()

    await page.goto('/ims/system/role')
    await expect(page.getByTestId('role-create-open')).toBeVisible()
    await page.getByTestId('role-create-open').click()
    await page.getByTestId('role-create-save').click()
    await expect(page.getByTestId('role-create-error')).toHaveText('请先完成必填项')
    await expect(page.getByTestId('role-create-name-error')).toHaveText('必填项，请填写')
    await expect(page.getByTestId('role-create-key-error')).toHaveText('必填项，请填写')

    await page.getByTestId('role-create-name').fill(`菜单用户${stamp}`)
    await page.getByTestId('role-create-key').fill(userCode)
    await page.getByTestId('role-create-scope').selectOption('ALL')
    const createdUserRole = page.waitForResponse(
      (r) => r.url().includes('/system/role') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('role-create-save').click()
    expect(((await (await createdUserRole).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('role-row').filter({ hasText: userCode })).toBeVisible()

    await page.getByTestId('role-create-open').click()
    await page.getByTestId('role-create-name').fill('重复编码')
    await page.getByTestId('role-create-key').fill(userCode)
    await page.getByTestId('role-create-save').click()
    await expect(page.getByTestId('role-create-error')).toHaveText('角色编码已存在')
    await expect(page.getByTestId('role-create-key-error')).toHaveText('角色编码已存在')
    await page.locator('.drawer.on').getByRole('button', { name: '取消' }).click()

    await page.getByTestId('role-create-open').click()
    await page.getByTestId('role-create-name').fill(`菜单角色${stamp}`)
    await page.getByTestId('role-create-key').fill(roleCode)
    await page.getByTestId('role-create-scope').selectOption('ALL')
    await page.getByTestId('role-create-remark').fill('并集用')
    await page.getByTestId('role-create-save').click()
    await expect(page.getByTestId('role-row').filter({ hasText: roleCode })).toBeVisible()

    await grantMenu(page, `菜单用户${stamp}`, 'system:user:query')
    await grantMenu(page, `菜单角色${stamp}`, 'system:role:query')

    await page.goto('/ims/system/user')
    await page.getByTestId('sys-user-create-open').click()
    const drawer = page.locator('.drawer.on')
    await drawer.getByTestId('sys-user-form-username').fill(noneName)
    await drawer.getByTestId('sys-user-form-nickname').fill(noneName)
    await drawer.getByTestId('sys-user-form-mobile').fill(`138${stamp}01`)
    await drawer.getByTestId('sys-user-form-password').fill('Admin@123')
    await drawer.getByTestId('sys-user-form-save').click()
    await expect(drawer).toBeHidden({ timeout: 15_000 })
    await page.locator('input[placeholder="用户名 / 手机"]').fill(noneName)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('sys-user-row').filter({ hasText: noneName })).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('sys-user-create-open').click()
    const unionDrawer = page.locator('.drawer.on')
    await unionDrawer.getByTestId('sys-user-form-username').fill(unionName)
    await unionDrawer.getByTestId('sys-user-form-nickname').fill(unionName)
    await unionDrawer.getByTestId('sys-user-form-mobile').fill(`138${stamp}02`)
    await unionDrawer.getByTestId('sys-user-form-roles').selectOption([
      { label: `菜单用户${stamp}（手工）` },
      { label: `菜单角色${stamp}（手工）` },
    ])
    await unionDrawer.getByTestId('sys-user-form-password').fill('Admin@123')
    await unionDrawer.getByTestId('sys-user-form-save').click()
    await expect(unionDrawer).toBeHidden({ timeout: 15_000 })
    await page.locator('input[placeholder="用户名 / 手机"]').fill(unionName)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('sys-user-row').filter({ hasText: unionName })).toBeVisible({ timeout: 15_000 })

    await logout(page)
    await loginAs(page, noneName)
    await expect(page).toHaveURL(/\/ims\/workbench/)
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '个人工作台' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '用户' })).toHaveCount(0)
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '直播管理' })).toHaveCount(0)
    await page.goto('/ims/system/user')
    await expect(page).toHaveURL(/\/ims\/workbench/)

    await logout(page)
    await loginAs(page, unionName)
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '用户' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '角色' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '直播管理' })).toHaveCount(0)
    await page.goto('/ims/system/user')
    await expect(page.getByTestId('sys-user-create-open')).toHaveCount(0)
    await expect(page.getByTestId('sys-user-edit')).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})