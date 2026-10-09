import { test, expect } from '@playwright/test'

/**
 * #203 FLOW 本地收尾（acceptance）
 * 已超时筛选空态、实例详情边界文案、撤销留痕、驳回抽屉（取消不提交，空意见可驳回）。
 * 不覆盖 #188 的 SLA / 退回目标节点 / 钉钉督办桩。
 */
test.describe('flow reject revoke local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter empty, detail edges, withdraw, and reject drawer', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    const shot = async (name: string) => {
      await page.screenshot({ path: `/opt/cursor/artifacts/flow-203-${name}.png`, fullPage: true })
    }

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByTestId('flow-instance-status').selectOption('TIMEOUT')
    await page.getByRole('button', { name: '查询' }).click()
    const timeoutEmpty = page.getByTestId('flow-instance-empty')
    await expect(timeoutEmpty).toContainText('暂无已超时实例', { timeout: 15_000 })
    await expect(timeoutEmpty).toContainText('临期待办请到超时督办')
    await shot('timeout-empty')

    await page.getByRole('button', { name: '重置' }).click()
    await page.locator('input[placeholder="标题/单号"]').fill('赛事集锦')
    await page.getByRole('button', { name: '查询' }).click()
    const instTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '状态' }) })
    const seedRow = instTable.locator('tbody tr').filter({ hasText: '赛事集锦' }).first()
    await expect(seedRow).toBeVisible({ timeout: 15_000 })
    await seedRow.getByTestId('flow-instance-detail').click()
    await expect(page.getByTestId('flow-detail-edge')).toContainText('实例已结束不可撤销')
    await expect(page.getByTestId('flow-detail-form-empty')).toContainText('未填写表单字段')
    await expect(page.getByTestId('flow-detail-trace-empty')).toContainText('暂无流转记录')
    await expect(page.getByTestId('flow-detail-cc-empty')).toContainText('暂无抄送记录')
    await expect(page.getByTestId('flow-revoke')).toHaveCount(0)
    await shot('detail-ended-empty')
    await page.getByRole('button', { name: '关闭' }).click()

    await page.getByRole('button', { name: '重置' }).click()

    const uniq = `e2e-flow-203-${Date.now()}`
    const title = `E2E 撤销 ${uniq}`
    await page.getByRole('button', { name: '发起流程' }).click()
    const modal = page.locator('aside.drawer.on')
    await expect(modal).toContainText('发起流程')
    await modal.locator('select').selectOption({ index: 0 })
    await modal.locator('input[placeholder="formData.title"]').fill(title)
    await modal.locator('input').nth(1).fill(uniq)
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.ok(),
    )
    await modal.getByRole('button', { name: '提交发起' }).click()
    const startBody = (await (await startResp).json()) as { code: number; data?: { instanceNo?: string } }
    expect(startBody.code).toBe(0)
    const instanceNo = startBody.data?.instanceNo ?? ''
    expect(instanceNo.length).toBeGreaterThan(0)

    const runningRow = instTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(runningRow).toBeVisible({ timeout: 15_000 })
    await runningRow.getByTestId('flow-instance-detail').click()
    await expect(page.getByTestId('flow-detail-edge')).toContainText('撤销后已完成节点留痕')
    await expect(page.locator('.drawer').getByText(title)).toBeVisible()
    await shot('detail-running')

    await page.getByTestId('flow-revoke').click()
    await expect(page.getByTestId('flow-revoke-copy')).toContainText('撤销后已完成节点留痕，实例进入已撤销')
    await shot('revoke-confirm')
    await page.getByTestId('flow-revoke-cancel').click()
    await expect(page.getByTestId('flow-revoke-modal')).toHaveCount(0)
    await expect(page.getByTestId('flow-detail-edge')).toContainText('进行中')

    await page.getByTestId('flow-revoke').click()
    const revokeResp = page.waitForResponse(
      (r) => r.url().includes('/revoke') && r.request().method() === 'PUT',
    )
    await page.getByTestId('flow-revoke-confirm').click()
    expect((await (await revokeResp).json()).code).toBe(0)
    await expect(page.getByTestId('flow-detail-edge')).toContainText('已撤销，已完成节点留痕，不可再次撤销', {
      timeout: 15_000,
    })
    await expect(page.getByTestId('flow-revoke')).toHaveCount(0)
    await expect(page.getByText('未办结，随实例撤销关闭')).toBeVisible()
    await shot('detail-cancelled')
    await page.getByRole('button', { name: '关闭' }).click()
    await expect(runningRow.locator('.tag')).toContainText('已撤销')

    const rejectTitle = `E2E 驳回 ${uniq}`
    await page.getByRole('button', { name: '发起流程' }).click()
    const modal2 = page.locator('aside.drawer.on')
    await modal2.locator('select').selectOption({ index: 0 })
    await modal2.locator('input[placeholder="formData.title"]').fill(rejectTitle)
    await modal2.locator('input').nth(1).fill(`${uniq}-reject`)
    const startResp2 = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.ok(),
    )
    await modal2.getByRole('button', { name: '提交发起' }).click()
    const startBody2 = (await (await startResp2).json()) as { code: number; data?: { instanceNo?: string } }
    expect(startBody2.code).toBe(0)
    const rejectNo = startBody2.data?.instanceNo ?? ''

    await page.getByRole('button', { name: '我的待办' }).click()
    const todoTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '发起人' }) })
    const todoRow = todoTable.locator('tbody tr').filter({ hasText: rejectNo }).first()
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    await todoRow.getByTestId('flow-reject').click()
    await expect(page.getByTestId('flow-reject-copy')).toContainText('建议填写退回意见，可不填')
    await shot('reject-drawer')
    await page.getByTestId('flow-reject-cancel').click()
    await expect(todoRow).toBeVisible()

    await todoRow.getByTestId('flow-reject').click()
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/flow/task/') && r.url().includes('/handle') && r.request().method() === 'PUT',
    )
    await page.getByTestId('flow-reject-confirm').click()
    const rejectBody = (await (await rejectResp).json()) as { code: number; data?: { newStatus?: string } }
    expect(rejectBody.code).toBe(0)
    expect(rejectBody.data?.newStatus).toBe('REJECTED')
    await expect(page.getByTestId('flow-reject-done')).toContainText(rejectNo)
    await expect(todoTable.locator('tbody tr').filter({ hasText: rejectNo })).toHaveCount(0, { timeout: 15_000 })

    await page.getByRole('button', { name: '流程实例' }).click()
    const rejectedRow = instTable.locator('tbody tr').filter({ hasText: rejectNo }).first()
    await expect(rejectedRow).toBeVisible({ timeout: 15_000 })
    await rejectedRow.getByTestId('flow-instance-detail').click()
    await expect(page.getByTestId('flow-detail-edge')).toContainText('实例已驳回结束，不可撤销')
    await expect(page.getByTestId('flow-revoke')).toHaveCount(0)
    await expect(page.locator('.drawer').getByText(rejectTitle)).toBeVisible()
    await shot('detail-rejected')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
