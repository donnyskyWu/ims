import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** 可见范围文案：私有 / 指定人 / 全员。分享弹窗与新建报表使用同一套选项，存储值仍为 ALL。 */
test.describe('bi share scope label', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share dialog and new report use 全员', async ({ page }) => {
    test.setTimeout(60_000)
    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await expect(reportModal.getByTestId('bi-new-scope').locator('option')).toHaveText(['私有', '指定人', '全员'])
    await reportModal.getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/bi/report/subscribe')
    await page.getByText('分享链接', { exact: true }).click()
    await page.getByRole('button', { name: '生成分享链接' }).click()
    const share = page.locator('.modal-mask .card').filter({ hasText: '生成分享链接' })
    await expect(share.getByTestId('bi-share-scope').locator('option')).toHaveText(['私有', '指定人', '全员'])
  })
})
