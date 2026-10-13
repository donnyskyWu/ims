import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAs } from './closure-helpers'

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

/**
 * HOME-08 / WB-12：无运营看板的角色侧栏不出现看板，直链进 403。
 * 个人工作台流程待办只看本人，空态是「暂无流程待办」，不报无操作权限。
 */
test.describe('home board and personal flow todos by role', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('R7 and R10 hide the ops board and still load personal flow todos', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)

    await loginAs(page, 'tc_r7')
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '个人工作台' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '运营看板' })).toHaveCount(0)
    await page.goto('/ims/home')
    await expect(page).toHaveURL(/\/403/)
    await expect(page.getByTestId('forbidden-page')).toBeVisible()

    const mine = page.waitForResponse(
      (r) => r.url().includes('/flow/task/my-todo') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/workbench')
    const flowBody = (await (await mine).json()) as { code: number; data: { list: unknown[] } }
    expect(flowBody.code).toBe(0)
    const flowTable = page.locator('.tbl-block').first()
    await expect(flowTable.getByText('加载失败')).toHaveCount(0)
    await expect(flowTable.getByText('无操作权限')).toHaveCount(0)
    if (flowBody.data.list.length === 0) {
      await expect(flowTable.getByText('暂无流程待办')).toBeVisible()
    }
    await expect(page.getByTestId('wb-flow-hint')).toHaveText(/待我处理的流程|暂无流程待办/)

    await logout(page)
    await loginAs(page, 'tc_r10')
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '个人工作台' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '运营看板' })).toHaveCount(0)
    await page.goto('/ims/home')
    await expect(page).toHaveURL(/\/403/)
    const outsider = page.waitForResponse(
      (r) => r.url().includes('/flow/task/my-todo') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/workbench')
    expect(((await (await outsider).json()) as { code: number }).code).toBe(0)
    await expect(page.locator('.tbl-block').first().getByText('无操作权限')).toHaveCount(0)

    await logout(page)
    await loginAs(page, 'tc_r4')
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '运营看板' })).toBeVisible()
    await page.goto('/ims/home')
    await expect(page).toHaveURL(/\/ims\/home/)
    await expect(page.locator('h1')).toContainText('运营仪表盘')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
