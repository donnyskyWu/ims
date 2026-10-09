import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

test.describe('HOME date and IP empty states, todo filter copy, message source (#209)', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('date span and missing IP copy, done-filter edge, source link', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')
    const ipFilter = page.getByTestId('home-ip-filter')
    await expect(ipFilter).toBeVisible()
    await expect(ipFilter.locator('option').first()).toHaveText('全部 IP 组')
    const accounts = page.locator('.card.stat').filter({ hasText: '账号数' })
    await expect(accounts).toBeVisible()
    await page.screenshot({ path: `${shotDir}/home-ip-filter.png`, fullPage: true })

    await page.getByTestId('home-date-from').fill('2025-06-01')
    await page.getByRole('button', { name: '刷新' }).click()
    const partial = page.getByTestId('home-dash-error')
    await expect(partial).toContainText('请同时填写开始和结束日期')
    await expect(accounts).toHaveCount(0)

    await page.getByTestId('home-date-to').fill('2025-01-01')
    await page.getByRole('button', { name: '刷新' }).click()
    await expect(partial).toContainText('结束日期不能早于开始日期')

    await page.getByTestId('home-date-from').fill('2025-01-01')
    await page.getByTestId('home-date-to').fill('2025-06-01')
    const spanResp = page.waitForResponse(
      (r) => r.url().includes('/home/dashboard') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    await spanResp
    await expect(partial).toContainText('日期跨度超过 90 天')
    await expect(partial).toContainText('90 天以内')
    await expect(accounts).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/home-date-span-empty.png`, fullPage: true })

    await page.getByTestId('home-date-from').fill('')
    await page.getByTestId('home-date-to').fill('')
    const restored = page.waitForResponse(
      (r) => r.url().includes('/home/dashboard') && r.url().includes('dateFrom=') && r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    await restored
    await expect(page.getByTestId('home-dash-error')).toHaveCount(0)
    await expect(accounts).toBeVisible()

    await page.route('**/ip-group/accessible-tree**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, msg: 'ok', data: [] }),
      })
    })
    await page.goto('/ims/home')
    await expect(page.getByTestId('home-ip-empty')).toContainText('没有可筛选的 IP 组')
    await expect(page.getByTestId('home-ip-filter').locator('option')).toHaveCount(1)
    await expect(accounts).toBeVisible()
    await page.screenshot({ path: `${shotDir}/home-ip-filter-empty.png`, fullPage: true })
    await page.unroute('**/ip-group/accessible-tree**')

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    await page.getByTestId('wb-todo-more').click()
    await page.waitForURL(/\/ims\/workbench\/todos/, { timeout: 30_000 })
    await expect(page.locator('h1')).toHaveText('待办中心')
    const typeSelect = page.getByTestId('todo-task-type')
    await expect(typeSelect.locator('option', { hasText: '审批' })).toHaveCount(1)
    await expect(typeSelect.locator('option', { hasText: '补录' })).toHaveCount(1)
    const approvalResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.url().includes('taskType=approval') && r.status() === 200,
    )
    await page.getByTestId('todo-tab-approval').click()
    await approvalResp
    await expect(typeSelect).toHaveValue('approval')

    const allResp = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/workbench/todos') &&
        !r.url().includes('taskType=') &&
        r.status() === 200,
    )
    await page.getByTestId('todo-tab-all').click()
    await allResp
    await page.getByTestId('todo-status').selectOption('DONE')
    await page.getByTestId('todo-keyword').fill('ZZZ209-NO-HIT')
    const doneResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.url().includes('DONE') && r.status() === 200,
    )
    await page.getByTestId('todo-search').click()
    await doneResp
    await expect(page.getByTestId('todo-empty')).toContainText('没有匹配的已处理待办')
    await expect(page.getByTestId('todo-empty')).toContainText('已处理列表里没有这个标题或摘要')
    await page.screenshot({ path: `${shotDir}/todo-done-filter-empty.png`, fullPage: true })

    await page.getByTestId('todo-status').selectOption('PENDING')
    const pendingResp = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/workbench/todos') &&
        r.url().includes('PENDING') &&
        r.url().includes('ZZZ209-NO-HIT') &&
        r.status() === 200,
    )
    await page.getByTestId('todo-search').click()
    await pendingResp
    await expect(page.getByTestId('todo-empty')).toContainText('没有匹配的待处理待办')

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心')
    await page.getByTestId('msg-read').selectOption('')
    await page.getByTestId('msg-keyword').fill('E2E-WB-MSG')
    const msgResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('msg-search').click()
    await msgResp
    const msgRow = page.getByTestId('msg-row').filter({ hasText: 'E2E-WB-MSG' })
    await expect(msgRow).toBeVisible()
    await msgRow.getByRole('button', { name: '查看' }).click()
    await expect(page.getByTestId('msg-source-link')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/msg-source-link.png`, fullPage: true })
    await page.getByTestId('msg-source-link').click()
    await page.waitForURL(/\/ims\/corp\/resource\/certificate/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('证件管理')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
