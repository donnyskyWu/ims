import { test, expect } from '@playwright/test'

/**
 * Checklist **E2E-FLOW-01**（acceptance · 非 narrow smoke）
 * Given: 已发布流程模板 · admin 会话
 * When: UI 发起 → 流程实例可见 → 我的待办「通过」
 * Then: 待办表无该单号 · 实例表状态 tag「已通过」+ 标题可见
 */
test.describe('flow start todo approve closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('E2E-FLOW-01: start instance then approve from my-todo tab', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    page.on('dialog', (d) => d.accept())

    const uniq = `e2e-flow-closure-${Date.now()}`
    const title = `E2E 闭环 ${uniq}`

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '发起流程' }).click()
    const drawer = page.locator('aside.drawer.on')
    await expect(drawer.locator('.drawer-h b')).toHaveText('发起流程')
    await expect(drawer.getByTestId('flow-start-empty')).toHaveCount(0)
    await expect(drawer.getByTestId('flow-start-template')).toBeVisible()
    await drawer.getByTestId('flow-start-template').selectOption({ index: 0 })
    await drawer.getByTestId('flow-start-title').fill(title)
    await drawer.getByTestId('flow-start-key').fill(uniq)

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('flow-start-submit').click()
    const resp =     await startResp
    const startBody = (await resp.json()) as { code: number; data?: { instanceNo?: string } }
    expect(startBody.code).toBe(0)
    const instanceNo = startBody.data?.instanceNo ?? ''
    expect(instanceNo.length).toBeGreaterThan(0)

    // E2E-FLOW-01 step: 发起后默认回到「流程实例」Tab，列表应可见新单
    await expect(page.getByRole('button', { name: '流程实例' })).toHaveClass(/on/)
    const instTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '状态' }) })
    const instRow = instTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(instRow).toBeVisible({ timeout: 15_000 })
    await expect(instRow).toContainText(title)
    await expect(instRow.locator('.tag')).toContainText('进行中')

    await page.getByRole('button', { name: '我的待办' }).click()
    const todoTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '发起人' }) })
    await expect(todoTable).toBeVisible()
    const todoRow = todoTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    await todoRow.getByText('通过', { exact: true }).click()
    const approve = page.locator('aside.drawer.on')
    await expect(approve.getByTestId('flow-approve-copy')).toBeVisible()
    await approve.getByTestId('flow-approve-confirm').click()

    await expect(todoTable.locator('tbody tr').filter({ hasText: instanceNo })).toHaveCount(0, { timeout: 15_000 })

    // E2E-FLOW-01 step: 审批后实例终态在 UI 可查
    await page.getByRole('button', { name: '流程实例' }).click()
    const instRowAfter = instTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(instRowAfter).toBeVisible({ timeout: 15_000 })
    await expect(instRowAfter.locator('.tag')).toContainText('已通过')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
