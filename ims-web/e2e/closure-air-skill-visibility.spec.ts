import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist E2E-S8-01 / E2E-S8-10 / E2E-S8-04 的页面侧（acceptance · 纯 UI）。
 * 网关 skills.list 可见性与未授权 403 在 pytest（test_air_skill_visibility.py）。
 */
const shotDir = '/opt/cursor/artifacts/e2e-89-screenshots'

test.describe('air skill visibility closure S8', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('publish, grant on three axes, then disable', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/air/skill')
    await expect(page.locator('h1')).toHaveText('技能库', { timeout: 15_000 })

    const skillName = `E2E技能可见${Date.now()}`
    await page.getByTestId('air-skill-create').click()
    const form = page.getByTestId('air-skill-form')
    await form.getByTestId('air-skill-name').fill(skillName)
    const created = page.waitForResponse(
      (response) => response.url().includes('/air/skill') && response.request().method() === 'POST',
    )
    await form.getByTestId('air-skill-save').click()
    expect((await (await created).json()).code).toBe(0)

    await page.locator('input[placeholder="技能名称"]').fill(skillName)
    const listed = page.waitForResponse(
      (response) => response.url().includes('/air/skill/list') && response.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listed
    const row = page.locator('tbody tr').filter({ hasText: skillName })
    await expect(row.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'DRAFT')
    await page.screenshot({ path: `${shotDir}/01-skill-draft.png`, fullPage: true })

    const submitted = page.waitForResponse((response) => response.url().includes('/submit-audit'))
    await row.getByTestId('air-skill-submit').click()
    expect((await (await submitted).json()).code).toBe(0)
    await expect(row.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'PENDING')
    await page.screenshot({ path: `${shotDir}/02-skill-pending.png`, fullPage: true })

    const approved = page.waitForResponse(
      (response) => response.url().includes('/audit') && response.request().method() === 'PUT',
    )
    await row.getByTestId('air-skill-approve').click()
    expect((await (await approved).json()).code).toBe(0)
    await expect(row.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'PUBLISHED')
    await expect(row.getByTestId('air-skill-grant-count')).toHaveText('0')
    await page.screenshot({ path: `${shotDir}/03-skill-published.png`, fullPage: true })

    await row.getByTestId('air-skill-grant').click()
    const drawer = page.getByTestId('air-skill-grant-form')
    await expect(drawer).toBeVisible()

    await drawer.getByTestId('air-grant-type').selectOption('PERSON')
    await drawer.getByTestId('air-grant-user-search').fill('e2e_author')
    const users = page.waitForResponse((response) => response.url().includes('/system/user/page'))
    await drawer.getByTestId('air-grant-user-find').click()
    await users
    await expect(drawer.getByTestId('air-grant-target')).not.toHaveValue('')
    const personSaved = page.waitForResponse(
      (response) => response.url().includes('/air/skill/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-grant-save').click()
    expect((await (await personSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-grant-row').filter({ hasText: '人员' })).toContainText('E2E内容作者')

    await drawer.getByTestId('air-grant-type').selectOption('ROLE')
    await expect(drawer.getByTestId('air-grant-target').locator('option', { hasText: '系统管理员' })).toHaveCount(1)
    await drawer.getByTestId('air-grant-target').selectOption({ label: '系统管理员' })
    const roleSaved = page.waitForResponse(
      (response) => response.url().includes('/air/skill/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-grant-save').click()
    expect((await (await roleSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-grant-row').filter({ hasText: '角色' })).toContainText('系统管理员')

    await drawer.getByTestId('air-grant-type').selectOption('DEPT')
    await drawer.getByTestId('air-grant-dept-search').fill('E2E内容作者')
    const orgUsers = page.waitForResponse((response) => response.url().includes('/auth/org/users'))
    await drawer.getByTestId('air-grant-dept-find').click()
    await orgUsers
    await drawer.getByTestId('air-grant-target').selectOption({ label: '部门#7301' })
    const deptSaved = page.waitForResponse(
      (response) => response.url().includes('/air/skill/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-grant-save').click()
    expect((await (await deptSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-grant-row').filter({ hasText: '部门' })).toContainText('部门#7301')
    await page.screenshot({ path: `${shotDir}/04-grant-dept-role-person.png`, fullPage: true })

    await drawer.getByTestId('air-grant-close').click()
    await expect(drawer).toHaveCount(0)
    await expect(row.getByTestId('air-skill-grant-count')).toHaveText('3')

    await row.getByTestId('air-skill-disable').click()
    await expect(page.getByTestId('air-skill-disable-confirm')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/05-disable-confirm.png`, fullPage: true })
    const disabled = page.waitForResponse(
      (response) => response.url().includes('/status') && response.request().method() === 'PUT',
    )
    await page.getByTestId('air-skill-disable-ok').click()
    expect((await (await disabled).json()).code).toBe(0)
    await expect(row.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'DISABLED')
    await expect(row.getByTestId('air-skill-enable')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/06-skill-disabled.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
