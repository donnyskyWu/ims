import { test, expect } from '@playwright/test'

/**
 * #172 local tails: filtered empty states on start/todo lists, and timeout urge edges
 * (blank message and over-256 do not increment remindCount).
 */
test.describe('flow local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filtered empty lists and urge message edges', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '发起流程' }).click()
    const drawer = page.locator('aside.drawer.on')
    await expect(drawer.getByTestId('flow-start-template')).toBeVisible()
    await expect(drawer.getByTestId('flow-start-empty')).toHaveCount(0)
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-start-drawer.png', fullPage: true })
    await drawer.getByRole('button', { name: '取消' }).click()
    await expect(drawer).toBeHidden()

    const miss = `no-such-flow-${Date.now()}`
    await page.locator('input[placeholder="标题/单号"]').fill(miss)
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    const instEmpty = page.getByTestId('flow-instance-empty')
    await expect(instEmpty).toBeVisible({ timeout: 15_000 })
    await expect(instEmpty).toContainText('没有符合条件的流程实例')
    await expect(instEmpty).toContainText('调整标题、单号或状态后再查询')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-instance-empty.png', fullPage: true })

    await page.getByRole('button', { name: '我的待办' }).click()
    await page.getByTestId('flow-todo-domain').selectOption('COMMON')
    await page.getByTestId('flow-todo-qbar').getByRole('button', { name: '查询' }).click()
    const todoEmpty = page.getByTestId('flow-todo-empty')
    await expect(todoEmpty).toBeVisible({ timeout: 15_000 })
    await expect(todoEmpty).toContainText('该业务域暂无待办')
    await expect(todoEmpty).toContainText('换一个业务域')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-todo-empty.png', fullPage: true })

    await page.getByRole('button', { name: '超时督办' }).click()
    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '提醒次数' }) })
    await expect(timeoutTable).toBeVisible({ timeout: 15_000 })
    const firstRow = timeoutTable.locator('tbody tr').first()
    await expect(firstRow).not.toContainText('暂无')
    const remindCell = firstRow.locator('td').nth(5)
    const before = parseInt((await remindCell.innerText()).trim(), 10)

    await firstRow.getByText('督办', { exact: true }).click()
    const modal = page.getByTestId('flow-urge-modal')
    await expect(modal).toBeVisible()
    await modal.getByTestId('flow-urge-message').fill('   ')
    let urgeCalls = 0
    page.on('request', (req) => {
      if (req.method() === 'PUT' && req.url().includes('/flow/timeout/') && req.url().includes('/urge')) urgeCalls += 1
    })
    await modal.getByTestId('flow-urge-confirm').click()
    await expect(modal.getByTestId('flow-urge-msg')).toContainText('请填写督办说明')
    expect(urgeCalls).toBe(0)
    await expect(remindCell).toHaveText(String(before))

    await modal.getByTestId('flow-urge-message').fill('督'.repeat(257))
    await modal.getByTestId('flow-urge-confirm').click()
    await expect(modal.getByTestId('flow-urge-msg')).toContainText('不能超过 256 字')
    expect(urgeCalls).toBe(0)
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-urge-overlong.png', fullPage: true })
    await modal.getByTestId('flow-urge-cancel').click()
    await expect(remindCell).toHaveText(String(before))

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
