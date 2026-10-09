import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

test.describe('workbench org tails #153', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('todo type filter, message channel, org tree empty, role matrix empty', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const position = `E2E岗${String(Date.now()).slice(-8)}`
    const todoTitle = `新岗位 ${position} 已自动建角色，请配置权限`

    await loginAdmin(page)

    await page.goto('/ims/system/role')
    await expect(page.locator('h1')).toHaveText('角色权限', { timeout: 15_000 })
    await page.getByTestId('role-position-input').fill(position)
    const created = page.waitForResponse(
      (r) => r.url().includes('/system/role/from-position') && r.request().method() === 'POST' && r.status() === 200,
    )
    const listed = page.waitForResponse(
      (r) => r.url().includes('/system/role/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '从岗位生成角色' }).click()
    await created
    await listed
    await page.getByTestId('role-status-pending').click()
    const roleRow = page.getByTestId('role-row').filter({ hasText: position })
    await expect(roleRow).toBeVisible({ timeout: 15_000 })
    await expect(roleRow).toContainText('待配置')
    await roleRow.getByTestId('role-edit').click()
    const matrixEmpty = page.getByTestId('role-matrix-empty')
    await expect(matrixEmpty).toBeVisible()
    await expect(matrixEmpty).toContainText('权限矩阵为空')
    await page.screenshot({ path: `${shotDir}/slice-153-role-matrix-empty.png`, fullPage: true })
    await page.getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/workbench/todos')
    await expect(page.locator('h1')).toHaveText('待办中心', { timeout: 15_000 })
    await page.getByTestId('todo-keyword').fill(position)
    const reviewResp = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/workbench/todos') &&
        r.url().includes('taskType=review') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('todo-tab-review').click()
    await reviewResp
    const todoRow = page.getByTestId('todo-row').filter({ hasText: todoTitle })
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    await expect(todoRow.getByTestId('todo-type-review')).toHaveText('审核')
    await page.screenshot({ path: `${shotDir}/slice-153-todo-filters.png`, fullPage: true })

    const approvalResp = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/workbench/todos') &&
        r.url().includes('taskType=approval') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('todo-tab-approval').click()
    await approvalResp
    await expect(page.getByTestId('todo-row').filter({ hasText: todoTitle })).toHaveCount(0)
    await expect(page.getByTestId('todo-empty')).toContainText('该类型下暂无待办')

    const pendingReview = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/workbench/todos') &&
        r.url().includes('taskType=review') &&
        !r.url().includes('EXPIRED') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('todo-tab-review').click()
    await pendingReview
    await page.getByTestId('todo-status').selectOption('EXPIRED')
    const expiredResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.url().includes('EXPIRED') && r.status() === 200,
    )
    await page.getByTestId('todo-search').click()
    await expiredResp
    await expect(page.getByTestId('todo-empty')).toContainText('该类型下暂无待办')

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心', { timeout: 15_000 })
    await page.getByTestId('msg-read').selectOption('')
    await page.getByTestId('msg-channel').selectOption('IN_APP')
    await page.getByTestId('msg-keyword').fill('E2E-WB-MSG')
    const msgResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('msg-search').click()
    await msgResp
    const msgRow = page.getByTestId('msg-row').filter({ hasText: 'E2E-WB-MSG' })
    await expect(msgRow).toBeVisible({ timeout: 15_000 })
    await expect(msgRow.getByTestId('msg-channel-tag')).toHaveText('站内')
    await msgRow.getByRole('button', { name: '查看' }).click()
    await expect(page.getByTestId('msg-detail')).toContainText('站内')
    await page.screenshot({ path: `${shotDir}/slice-153-message-types.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('msg-channel').selectOption('DINGTALK')
    const dingResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages') && r.url().includes('DINGTALK') && r.status() === 200,
    )
    await page.getByTestId('msg-search').click()
    await dingResp
    await expect(page.getByTestId('msg-empty')).toContainText('没有钉钉消息')

    await page.goto('/ims/auth/org')
    await expect(page.locator('h1')).toHaveText('组织架构同步', { timeout: 15_000 })
    await expect(page.getByTestId('org-dept-tree')).toBeVisible()
    await page.getByTestId('org-dept-filter').fill('不存在的部门XYZ')
    const treeEmpty = page.getByTestId('org-dept-empty')
    await expect(treeEmpty).toBeVisible()
    await expect(treeEmpty).toContainText(/还没有部门|没有匹配的部门/)
    await page.screenshot({ path: `${shotDir}/slice-153-org-tree-empty.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
