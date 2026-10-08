import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const POOL_NO = 'AC-E2E-POOL'
const POOL_NICK = 'E2E池内抖音'

test.describe('CORP account pool checkout and return closure S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('E2E-S4-01/08 pool checkout IN_USE then return RETURNED (#47)', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/account/douyin')
    await expect(page.locator('h1')).toContainText('抖音')

    await page.locator('input[placeholder="账号编号/昵称"]').fill(POOL_NO)
    const searchResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await searchResp

    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })
    await expect(row).toBeVisible()
    await expect(row).toContainText('池可领用')

    await row.getByRole('button', { name: '领用' }).click()
    await expect(page.locator('.drawer.on').getByText('发起账号领用')).toBeVisible()

    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交申请' }).click()
    await applyResp

    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '审批通过' }).click()
    await approveResp

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/confirm') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '确认领用生效' }).click()
    await confirmResp

    const inUseRow = page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })
    await expect(inUseRow).toContainText('在用')
    await expect(inUseRow).toContainText('管理员')

    await inUseRow.getByRole('button', { name: '归还' }).click()
    await expect(page.locator('.drawer.on').getByText('账号归还')).toBeVisible()
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/account/return/submit') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '确认归还' }).click()
    await returnResp

    const returnedRow = page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })
    await expect(returnedRow).toContainText('已归还')

    await returnedRow.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    await expect(page.locator('.timeline-list')).toContainText('APPLY')
    await expect(page.locator('.timeline-list')).toContainText('RETURN')
  })
})
