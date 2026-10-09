import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.describe('HOME empty cards and workbench unread badge', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('home cards and shortcuts show empty states when lists are empty', async ({ page }) => {
    await loginAdmin(page)
    await page.route('**/home/dashboard**', async (route) => {
      const response = await route.fetch()
      const json = await response.json()
      if (json?.data) {
        json.data.kpis = []
        json.data.todos = []
        json.data.shortcuts = []
        json.data.trendPlayEngage = []
      }
      await route.fulfill({ response, json })
    })
    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')
    await expect(page.getByTestId('home-kpi-empty')).toContainText('暂无指标')
    await expect(page.getByTestId('home-trend-empty')).toContainText('暂无播放趋势')
    await expect(page.getByTestId('home-todo-empty')).toContainText('暂无待办')
    await expect(page.getByTestId('home-shortcut-empty')).toContainText('暂无可用快捷入口')
    await page.screenshot({
      path: '/opt/cursor/artifacts/home-cards-empty.png',
      fullPage: true,
    })
  })

  test('topbar unread badge and mark-all-read clear the inbox', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/home')
    await expect(page.locator('.card.stat').filter({ hasText: '账号数' })).toBeVisible()
    await expect(page.locator('.card.hov').filter({ hasText: '登记工作任务' })).toBeVisible()
    await page.screenshot({
      path: '/opt/cursor/artifacts/home-cards-shortcuts.png',
      fullPage: true,
    })

    const badge = page.getByTestId('topbar-unread-badge')
    await expect(badge).toBeVisible()
    const unreadBefore = Number(await badge.innerText())
    expect(unreadBefore).toBeGreaterThan(0)

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    await expect(page.getByTestId('wb-msg-unread')).toBeVisible()
    await expect(page.getByTestId('wb-msg-read-all')).toBeVisible()
    await page.screenshot({
      path: '/opt/cursor/artifacts/workbench-unread-badge.png',
      fullPage: true,
    })

    await page.getByTestId('topbar-msg-bell').click()
    const drawer = page.getByTestId('topbar-msg-drawer')
    await expect(drawer).toBeVisible()
    const seedRow = drawer.locator('[data-testid="topbar-msg-item"]').filter({ hasText: 'E2E-WB-MSG' })
    await expect(seedRow).toContainText('未读')
    await page.screenshot({
      path: '/opt/cursor/artifacts/workbench-message-drawer.png',
      fullPage: true,
    })

    const readAll = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages/read-all') && r.request().method() === 'PUT' && r.ok(),
    )
    await drawer.getByTestId('topbar-msg-read-all').click()
    await readAll
    await expect(badge).toHaveCount(0)
    await expect(seedRow).toContainText('已读')

    const unreadCard = page.locator('.card.stat').filter({ hasText: '未读消息' })
    await expect(unreadCard.locator('.n')).toHaveText('0')
    await page.screenshot({
      path: '/opt/cursor/artifacts/workbench-mark-all-read.png',
      fullPage: true,
    })
  })
})
