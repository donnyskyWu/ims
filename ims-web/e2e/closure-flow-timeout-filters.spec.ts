import { test, expect } from '@playwright/test'

/**
 * #216 local tails: timeout list domain / assignee empty copy, and a stat month
 * with no executed nodes. Does not rebuild the approval drawer.
 */
test.describe('flow timeout filter empty closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('domain and assignee empties, empty stat month, invalid month', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await page.getByRole('button', { name: '超时督办' }).click()
    await expect(page.getByText('时长分布：')).toBeVisible({ timeout: 15_000 })

    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '提醒次数' }) })
    await expect(timeoutTable).toBeVisible()
    const firstRow = timeoutTable.locator('tbody tr').first()
    await expect(firstRow).not.toContainText('暂无')
    const assigneeName = (await firstRow.locator('td').nth(3).innerText()).trim()
    expect(assigneeName).not.toBe('—')
    expect(assigneeName.length).toBeGreaterThan(0)

    const qbar = page.getByTestId('flow-timeout-qbar')
    await qbar.getByTestId('flow-timeout-domain').selectOption('COMMON')
    await qbar.getByRole('button', { name: '查询' }).click()
    const empty = page.getByTestId('flow-timeout-empty')
    await expect(empty).toBeVisible({ timeout: 15_000 })
    await expect(empty).toContainText('该业务域暂无超时待办')
    await expect(empty).toContainText('换一个业务域，或清空筛选后再查')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-216-timeout-domain-empty.png', fullPage: true })

    await qbar.getByRole('button', { name: '重置' }).click()
    await expect(firstRow).not.toContainText('暂无', { timeout: 15_000 })

    const miss = `no-such-assignee-${Date.now()}`
    await qbar.getByTestId('flow-timeout-assignee').fill(miss)
    await qbar.getByRole('button', { name: '查询' }).click()
    await expect(empty).toBeVisible({ timeout: 15_000 })
    await expect(empty).toContainText('该处理人暂无超时待办')
    await expect(empty).toContainText('核对处理人姓名后再查询')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-216-timeout-assignee-empty.png', fullPage: true })

    await qbar.getByRole('button', { name: '重置' }).click()
    await expect(timeoutTable.locator('tbody tr').first()).not.toContainText('暂无', { timeout: 15_000 })
    await qbar.getByTestId('flow-timeout-assignee').fill(`  ${assigneeName}  `)
    await qbar.getByRole('button', { name: '查询' }).click()
    const hitRow = timeoutTable.locator('tbody tr').filter({ hasText: assigneeName }).first()
    await expect(hitRow).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('flow-timeout-empty')).toHaveCount(0)

    await qbar.getByTestId('flow-timeout-domain').selectOption('COMMON')
    await qbar.getByRole('button', { name: '查询' }).click()
    await expect(empty).toBeVisible({ timeout: 15_000 })
    await expect(empty).toContainText('没有符合条件的超时待办')
    await expect(empty).toContainText('调整业务域或处理人后再查询')

    const currentMonth = await page.getByTestId('flow-stat-month').inputValue()
    await page.getByTestId('flow-stat-month').fill('2000-01')
    await page.getByTestId('flow-stat-month-apply').click()
    const monthEmpty = page.getByTestId('flow-stat-month-empty')
    await expect(monthEmpty).toBeVisible({ timeout: 15_000 })
    await expect(monthEmpty).toContainText('该统计月暂无执行记录')
    await expect(monthEmpty).toContainText('换一个月或回到本月')
    await expect(page.getByText('时长分布：')).toHaveCount(0)
    await expect(empty).toContainText('没有符合条件的超时待办')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-216-stat-month-empty.png', fullPage: true })

    await page.getByTestId('flow-stat-month').fill('2020-13')
    await page.getByTestId('flow-stat-month-apply').click()
    await expect(page.getByTestId('flow-stat-month-msg')).toContainText('统计月请填写 YYYY-MM')
    await expect(page.getByTestId('flow-stat-month-empty')).toHaveCount(0)
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-216-stat-month-invalid.png', fullPage: true })

    await page.getByTestId('flow-stat-month').fill(currentMonth)
    await page.getByTestId('flow-stat-month-apply').click()
    await expect(page.getByText('时长分布：')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('flow-stat-month-msg')).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
