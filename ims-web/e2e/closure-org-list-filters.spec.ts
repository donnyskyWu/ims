import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

test.describe('org list filter tails #212', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('org, position, role and permission filters show empty copy', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const token = String(Date.now()).slice(-8)
    const ruleName = `供给212${token}`
    const position = `岗212${token}`

    await loginAdmin(page)
    await filterOrgUsers(page)
    await filterOrgEvents(page)
    await filterPositionRules(page, ruleName, position)
    await filterRolesAndPerms(page)
    await filterMenus(page)
    expect(pageErrors).toEqual([])
  })
})

async function filterOrgUsers(page: Page) {
  await page.goto('/ims/auth/org')
  await expect(page.locator('h1')).toHaveText('组织架构同步', { timeout: 15_000 })
  await page.getByTestId('org-user-sync').selectOption('SUCCESS')
  const successResp = page.waitForResponse(
    (r) =>
      r.url().includes('/auth/org/users') &&
      r.url().includes('syncStatus=SUCCESS') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.getByTestId('org-user-search').click()
  await successResp
  await expect(page.getByTestId('org-user-sync-hint')).toContainText('失败包含失败重试和死信')
  await expect(page.getByTestId('org-user-filter-note')).toContainText('同步状态「成功」')

  await page.getByTestId('org-user-keyword').fill('不存在人员XYZ212')
  await page.getByTestId('org-user-sync').selectOption('PENDING')
  const emptyResp = page.waitForResponse(
    (r) =>
      r.url().includes('/auth/org/users') &&
      r.url().includes('syncStatus=PENDING') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.getByTestId('org-user-search').click()
  await emptyResp
  const userEmpty = page.getByTestId('org-user-empty')
  await expect(userEmpty).toBeVisible()
  await expect(userEmpty).toContainText('没有匹配的人员')
  await expect(userEmpty).toContainText('换姓名、部门或同步状态后再查')
  await page.screenshot({ path: `${shotDir}/slice-212-org-user-empty.png`, fullPage: true })

  const resetResp = page.waitForResponse(
    (r) => r.url().includes('/auth/org/users') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('org-user-reset').click()
  await resetResp
  await expect(page.getByTestId('org-user-keyword')).toHaveValue('')
  await expect(page.getByTestId('org-user-sync')).toHaveValue('')
}

async function filterOrgEvents(page: Page) {
  await page.getByTestId('org-tab-events').click()
  await page.getByTestId('org-event-from').fill('2099-03-02')
  await page.getByTestId('org-event-search').click()
  await expect(page.getByTestId('org-event-hint')).toHaveText('请同时填写开始和结束日期')

  await page.getByTestId('org-event-from').fill('2099-03-04')
  await page.getByTestId('org-event-to').fill('2099-03-01')
  await page.getByTestId('org-event-search').click()
  await expect(page.getByTestId('org-event-hint')).toHaveText('结束日期不能早于开始日期')

  await page.getByTestId('org-event-type').selectOption('resign')
  await page.getByTestId('org-event-sync').selectOption('DEAD_LETTER')
  await page.getByTestId('org-event-from').fill('2099-01-01')
  await page.getByTestId('org-event-to').fill('2099-01-02')
  const eventResp = page.waitForResponse(
    (r) =>
      r.url().includes('/auth/org/events') &&
      r.url().includes('eventType=resign') &&
      r.url().includes('syncStatus=DEAD_LETTER') &&
      r.url().includes('timeRange=') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.getByTestId('org-event-search').click()
  await eventResp
  const eventEmpty = page.getByTestId('org-event-empty')
  await expect(eventEmpty).toContainText('没有符合条件的同步事件')
  await expect(page.getByTestId('org-event-filter-note')).toContainText('离职')
  await expect(page.getByTestId('org-event-filter-note')).toContainText('死信')
  await page.screenshot({ path: `${shotDir}/slice-212-org-event-empty.png`, fullPage: true })
}

async function filterPositionRules(page: Page, ruleName: string, position: string) {
  await page.goto('/ims/auth/position')
  await expect(page.locator('h1')).toHaveText('岗位-角色供给规则', { timeout: 15_000 })
  await expect(page.getByTestId('pos-create-role').locator('option', { hasText: '系统管理员' })).toHaveCount(1)
  await expect(page.locator('.tbl-wrap')).not.toContainText('加载中')
  await page.getByTestId('pos-create-name').fill(ruleName)
  await page.getByTestId('pos-create-position').fill(position)
  const created = page.waitForResponse(
    (r) => r.url().includes('/auth/position/rule') && r.request().method() === 'POST' && r.status() === 200,
  )
  const listed = page.waitForResponse(
    (r) => r.url().includes('/auth/position/rules') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('pos-create-submit').click()
  await created
  await listed
  await expect(page.getByTestId('pos-rule-row').filter({ hasText: ruleName })).toBeVisible()

  await page.getByTestId('pos-filter-keyword').fill(ruleName)
  await page.getByTestId('pos-filter-position').fill(position)
  await page.getByTestId('pos-filter-status').selectOption('ENABLED')
  const matched = page.waitForResponse(
    (r) =>
      r.url().includes('/auth/position/rules') &&
      r.url().includes('status=ENABLED') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.getByTestId('pos-filter-search').click()
  await matched
  await expect(page.getByTestId('pos-rule-row').filter({ hasText: ruleName })).toBeVisible()
  await expect(page.getByTestId('pos-filter-summary')).toContainText(ruleName)
  await page.screenshot({ path: `${shotDir}/slice-212-position-filter.png`, fullPage: true })

  await page.getByTestId('pos-filter-keyword').fill(`没有这规则${ruleName}`)
  const missed = page.waitForResponse(
    (r) => r.url().includes('/auth/position/rules') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('pos-filter-search').click()
  await missed
  await expect(page.getByTestId('pos-list-empty')).toContainText('没有符合条件的供给规则')
  await page.screenshot({ path: `${shotDir}/slice-212-position-empty.png`, fullPage: true })
}

async function filterRolesAndPerms(page: Page) {
  await page.goto('/ims/system/role')
  await expect(page.locator('h1')).toHaveText('角色权限', { timeout: 15_000 })
  await page.getByTestId('role-filter-keyword').fill('系统管理员')
  await page.getByTestId('role-filter-source').selectOption('MANUAL')
  const adminRow = page.getByTestId('role-row').filter({ hasText: '系统管理员' })
  await expect(adminRow).toBeVisible()
  await expect(page.getByTestId('role-filter-summary')).toContainText('自建')

  await page.getByTestId('role-filter-keyword').fill('不存在角色XYZ212')
  await expect(page.getByTestId('role-list-empty')).toContainText('没有符合条件的角色')
  await page.getByTestId('role-filter-reset').click()
  await expect(page.getByTestId('role-row').filter({ hasText: '系统管理员' })).toBeVisible()

  await adminRow.getByTestId('role-edit').click()
  await page.getByTestId('role-perm-filter').fill('auth:org:query')
  await expect(page.getByTestId('role-perm-row').filter({ hasText: 'auth:org:query' })).toBeVisible()
  await page.getByTestId('role-perm-filter').fill('不存在权限XYZ212')
  await expect(page.getByTestId('role-perm-empty')).toContainText('没有匹配的权限码')
  await expect(page.getByTestId('role-perm-empty')).toContainText('已勾选的权限仍会保存')
  await page.screenshot({ path: `${shotDir}/slice-212-role-perm-filter.png`, fullPage: true })
}

async function filterMenus(page: Page) {
  await page.goto('/ims/system/menu')
  await expect(page.locator('h1')).toHaveText('菜单', { timeout: 15_000 })
  await page.getByTestId('menu-filter-keyword').fill('auth:org:query')
  const row = page.getByTestId('menu-row').filter({ hasText: '组织架构' })
  await expect(row).toBeVisible()
  await expect(row).toContainText('auth:org:query')
  await expect(page.getByTestId('menu-filter-summary')).toContainText('auth:org:query')

  await page.getByTestId('menu-filter-keyword').fill('不存在权限菜单XYZ212')
  await expect(page.getByTestId('menu-list-empty')).toContainText('没有匹配的权限菜单')
  await page.screenshot({ path: `${shotDir}/slice-212-menu-filter.png`, fullPage: true })
}
