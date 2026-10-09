import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

test.describe('HOME filter notes and workbench widget copy (#228)', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter note, widget hints, expired and read empties', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')
    const note = page.getByTestId('home-filter-note')
    await expect(note).toContainText('账号数随 IP 组')
    await expect(note).toContainText('不请求 Football')
    await expect(note).toContainText('近 7 天')
    await expect(note).toContainText('不按 IP 组或日期缩小')
    const works = page.locator('.card.stat').filter({ hasText: '今日作品' })
    await expect(works.locator('.d')).toContainText('Football')
    await expect(works.locator('.d')).toContainText('不随日期')
    await expect(page.locator('.card.stat').filter({ hasText: '账号数' }).locator('.d')).toContainText('随 IP 组变化')
    await expect(page.locator('.card.stat').filter({ hasText: '采集异常' }).locator('.d')).toContainText('近 7 天')
    await expect(page.locator('.csub').first()).toContainText('不随筛选变化')
    await page.screenshot({ path: `${shotDir}/home-filter-note.png`, fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    await expect(page.getByTestId('wb-todo-hint')).toHaveText(/本人待处理|暂无待办/)
    await expect(page.getByTestId('wb-flow-hint')).toHaveText(/待我处理的流程|暂无流程待办/)
    await expect(page.getByTestId('wb-unread-hint')).toHaveText(/站内未读|暂无未读/)
    await expect(page.getByText('GET /auth/workbench/dashboard')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/workbench-widget-hints.png`, fullPage: true })

    await page.goto('/ims/workbench/todos')
    await expect(page.locator('h1')).toHaveText('待办中心')
    await page.getByTestId('todo-status').selectOption('EXPIRED')
    await page.getByTestId('todo-keyword').fill('ZZZ228-NO-HIT')
    const expiredResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.url().includes('EXPIRED') && r.status() === 200,
    )
    await page.getByTestId('todo-search').click()
    await expiredResp
    await expect(page.getByTestId('todo-empty')).toContainText('没有匹配的已过期待办')
    await expect(page.getByTestId('todo-empty')).toContainText('已过期列表里没有这个标题或摘要')
    await page.screenshot({ path: `${shotDir}/todo-expired-filter-empty.png`, fullPage: true })

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心')
    await page.getByTestId('msg-read').selectOption('true')
    await page.getByTestId('msg-keyword').fill('ZZZ228-NO-READ')
    const readResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages') && r.url().includes('ZZZ228') && r.status() === 200,
    )
    await page.getByTestId('msg-search').click()
    await readResp
    await expect(page.getByTestId('msg-empty')).toContainText('没有匹配的已读消息')
    await expect(page.getByTestId('msg-empty')).toContainText('已读列表里没有这个标题或摘要')
    await page.screenshot({ path: `${shotDir}/msg-read-filter-empty.png`, fullPage: true })

    await page.route('**/auth/workbench/dashboard**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1200, msg: '工作台暂时不可用', data: null }),
      })
    })
    await page.goto('/ims/workbench')
    await expect(page.getByTestId('wb-todo-hint')).toHaveText('加载失败')
    await expect(page.getByTestId('wb-dash-retry')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/workbench-widget-load-fail.png`, fullPage: true })
    await page.unroute('**/auth/workbench/dashboard**')
    const recovered = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/dashboard') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('wb-dash-retry').click()
    await recovered
    await expect(page.getByTestId('wb-todo-hint')).toHaveText(/本人待处理|暂无待办/)

    await page.route('**/auth/workbench/dashboard**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          msg: 'ok',
          data: { todoCount: 0, flowTodoCount: 0, unreadMessageCount: 0 },
        }),
      })
    })
    await page.goto('/ims/workbench')
    await expect(page.getByTestId('wb-todo-hint')).toHaveText('暂无待办')
    await expect(page.getByTestId('wb-flow-hint')).toHaveText('暂无流程待办')
    await expect(page.getByTestId('wb-unread-hint')).toHaveText('暂无未读')
    await page.screenshot({ path: `${shotDir}/workbench-widget-zero.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
