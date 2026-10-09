import fs from 'node:fs'
import { test, expect, type Page, type Request } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-230-screenshots'

function watchPosts(page: Page, part: string) {
  const hits: Request[] = []
  const onRequest = (req: Request) => {
    if (req.method() === 'POST' && req.url().includes(part)) hits.push(req)
  }
  page.on('request', onRequest)
  return {
    hits,
    stop() {
      page.off('request', onRequest)
    },
  }
}

/**
 * #230 组织基座本地表单边角（acceptance · 纯 UI）
 * 岗位供给规则字数、待配置角色、重复岗位与删除确认；角色岗位长度与本部门范围文案。
 */
test.describe('org form edges', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('position rule validation and role permission edge copy', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = String(Date.now()).slice(-6)
    const position = `E2E岗${stamp}`
    const ruleName = `${position}规则`
    const dingPos = `${position}钉`

    await loginAdmin(page)
    await page.goto('/ims/system/role')
    await expect(page.locator('h1')).toHaveText('角色权限', { timeout: 15_000 })

    const longRole = watchPosts(page, '/system/role/from-position')
    await page.getByTestId('role-position-input').fill('岗'.repeat(65))
    await page.getByRole('button', { name: '从岗位生成角色' }).click()
    await expect(page.getByTestId('role-form-error')).toHaveText('钉钉岗位不能超过 64 字')
    expect(longRole.hits).toHaveLength(0)
    longRole.stop()
    await page.screenshot({ path: `${SHOTS}/01-role-position-length.png`, fullPage: true })

    await page.getByTestId('role-position-input').fill(position)
    const created = page.waitForResponse(
      (r) => r.url().includes('/system/role/from-position') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '从岗位生成角色' }).click()
    expect(((await (await created).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('role-edge-note')).toHaveText('已生成待配置角色，权限为空，配置前不放行')
    await page.screenshot({ path: `${SHOTS}/02-role-created-pending.png`, fullPage: true })

    await page.getByTestId('role-position-input').fill(position)
    const again = page.waitForResponse(
      (r) => r.url().includes('/system/role/from-position') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '从岗位生成角色' }).click()
    const againBody = (await (await again).json()) as { data?: { created?: boolean } }
    expect(againBody.data?.created).toBe(false)
    await expect(page.getByTestId('role-edge-note')).toHaveText('该岗位已有角色，未重复创建')
    await page.screenshot({ path: `${SHOTS}/03-role-duplicate.png`, fullPage: true })

    await page.getByTestId('role-status-pending').click()
    const roleRow = page.getByTestId('role-row').filter({ hasText: position })
    await expect(roleRow).toBeVisible()
    await roleRow.getByTestId('role-edit').click()
    await expect(page.getByTestId('role-matrix-empty')).toBeVisible()
    await page.getByTestId('role-scope').selectOption('DEPT')
    await expect(page.getByTestId('role-dept-edge')).toHaveText('本部门只含本级，不含下级。')
    await page.screenshot({ path: `${SHOTS}/04-role-dept-edge.png`, fullPage: true })
    const scopeSaved = page.waitForResponse(
      (r) => r.url().includes('/data-scope') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('role-save').click()
    expect(((await (await scopeSaved).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('role-edge-note')).toContainText('未勾选功能点，保存后不放行任何权限')
    await expect(page.getByTestId('role-edge-note')).toContainText('数据范围为本部门，不含下级')
    await page.screenshot({ path: `${SHOTS}/05-role-save-edge.png`, fullPage: true })

    await page.goto('/ims/auth/position')
    await expect(page.locator('h1')).toContainText('岗位-角色供给规则')
    await expect(page.getByTestId('pos-create-role').locator('option', { hasText: '系统管理员' })).toHaveCount(1, {
      timeout: 15_000,
    })

    const longRule = watchPosts(page, '/auth/position/rule')
    await page.getByTestId('pos-create-name').fill('规'.repeat(65))
    await page.getByTestId('pos-create-position').fill(dingPos)
    await page.getByTestId('pos-create-submit').click()
    await expect(page.getByTestId('pos-form-error')).toHaveText('规则名不能超过 64 字')
    expect(longRule.hits).toHaveLength(0)
    longRule.stop()
    await page.screenshot({ path: `${SHOTS}/06-position-name-length.png`, fullPage: true })

    await page.getByTestId('pos-create-name').fill(ruleName)
    await page.getByTestId('pos-create-desc').fill('说'.repeat(201))
    await page.getByTestId('pos-create-submit').click()
    await expect(page.getByTestId('pos-form-error')).toHaveText('说明不能超过 200 字')

    await page.getByTestId('pos-create-desc').fill('本地说明')
    await page.getByTestId('pos-create-role').selectOption({ label: `${position}（待配置）` })
    await page.getByTestId('pos-create-submit').click()
    await expect(page.getByTestId('pos-form-error')).toContainText(`角色「${position}」尚未配置权限，用户将无任何权限`)
    await page.screenshot({ path: `${SHOTS}/07-position-pending-role.png`, fullPage: true })

    await page.getByTestId('pos-create-role').selectOption({ label: '系统管理员' })
    const createdRule = page.waitForResponse(
      (r) => r.url().includes('/auth/position/rule') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('pos-create-submit').click()
    expect(((await (await createdRule).json()) as { code: number }).code).toBe(0)
    const ruleRow = page.getByTestId('pos-rule-row').filter({ hasText: ruleName })
    await expect(ruleRow).toBeVisible()
    await expect(ruleRow).toContainText(dingPos)

    await page.getByTestId('pos-create-name').fill(`${ruleName}二`)
    await page.getByTestId('pos-create-position').fill(dingPos)
    await page.getByTestId('pos-create-desc').fill('')
    await page.getByTestId('pos-create-submit').click()
    await expect(page.getByTestId('pos-form-error')).toHaveText('该岗位已有启用版本')
    await expect(page.getByTestId('pos-rule-row').filter({ hasText: dingPos })).toHaveCount(1)
    await page.screenshot({ path: `${SHOTS}/08-position-duplicate.png`, fullPage: true })

    await ruleRow.getByTestId('pos-delete').click()
    await expect(page.getByTestId('pos-delete-card')).toBeVisible()
    await page.getByTestId('pos-delete-name').fill('不对')
    await page.getByTestId('pos-delete-confirm').click()
    await expect(page.getByTestId('pos-form-error')).toHaveText('请输入规则名以确认删除')
    await expect(ruleRow).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/09-position-delete-mismatch.png`, fullPage: true })

    await page.getByTestId('pos-delete-name').fill(ruleName)
    const removed = page.waitForResponse(
      (r) => r.url().includes('/auth/position/rule/') && r.request().method() === 'DELETE' && r.status() === 200,
    )
    await page.getByTestId('pos-delete-confirm').click()
    expect(((await (await removed).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('pos-rule-row').filter({ hasText: ruleName })).toHaveCount(0)

    await page.goto('/ims/auth/org')
    await expect(page.locator('h1')).toContainText('组织架构同步')
    const opener = page.getByTestId('org-user-open')
    if (await opener.count()) {
      await opener.first().click()
      const perms = page.getByTestId('org-detail-perms')
      await expect(perms).toBeVisible()
      const permText = (await perms.innerText()).trim()
      expect(permText).not.toBe('—')
      expect(permText.length).toBeGreaterThan(0)
      const roles = (await page.getByTestId('org-detail-roles').innerText()).trim()
      expect(roles).not.toBe('—')
      await expect(page.getByTestId('org-user-holdings')).toBeVisible()
    }
    await page.screenshot({ path: `${SHOTS}/10-org-user-edge.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
