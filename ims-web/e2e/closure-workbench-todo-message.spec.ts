import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const E2E_WB_MSG_TITLE = 'E2E-WB-MSG'
const E2E_WB_TODO_TITLE = 'E2E-WB-CLOSE'

test.describe('WORKBENCH todo close and message read closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('mark message read then close seeded todo (#46)', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)

    const unreadCard = page.locator('.card.stat').filter({ hasText: '未读消息' })
    await expect(unreadCard.locator('.n')).toHaveText(/\d+/)
    const unreadBefore = Number(await unreadCard.locator('.n').innerText())

    const todoCard = page.locator('.card.stat').filter({ hasText: '待办预览' })
    await expect(todoCard.locator('.n')).toHaveText(/\d+/)
    const todoBefore = Number(await todoCard.locator('.n').innerText())

    const tables = page.locator('.tbl-wrap table')
    const todoTable = tables.nth(1)
    const msgTable = tables.nth(2)

    const msgRow = msgTable.locator('tbody tr').filter({ hasText: E2E_WB_MSG_TITLE })
    await expect(msgRow).toBeVisible()
    await expect(msgRow).toContainText('否')

    const readResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await msgRow.getByRole('button', { name: '标为已读' }).click()
    await readResp

    await expect(msgRow).toContainText('是')
    await expect(msgRow.getByRole('button', { name: '标为已读' })).toHaveCount(0)
    if (unreadBefore > 0) {
      await expect(unreadCard.locator('.n')).toHaveText(String(unreadBefore - 1))
    }

    const todoRow = todoTable.locator('tbody tr').filter({ hasText: E2E_WB_TODO_TITLE })
    await expect(todoRow).toBeVisible()
    await expect(todoRow.getByRole('button', { name: '关闭' })).toBeVisible()

    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await todoRow.getByRole('button', { name: '关闭' }).click()
    await closeResp

    await expect(todoTable.locator('tbody tr').filter({ hasText: E2E_WB_TODO_TITLE })).toHaveCount(0)
    if (todoBefore > 0) {
      await expect(todoCard.locator('.n')).toHaveText(String(todoBefore - 1))
    }
  })
})
