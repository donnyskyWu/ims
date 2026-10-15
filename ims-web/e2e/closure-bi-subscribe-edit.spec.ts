import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-C037：新建订阅选择报表和推送渠道；编辑；暂停/恢复先确认再提示。
 */
test.describe('bi subscribe edit C037', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pick report and channel, edit, pause and resume with confirm', async ({ page }) => {
    test.setTimeout(90_000)
    const reportName = `E2E 订阅 ${Date.now()}`
    const subName = `订阅 ${Date.now()}`
    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(reportName)
    await reportModal.getByRole('button', { name: '创建并进入设计器' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器')

    await page.goto('/ims/bi/report/subscribe')
    await page.getByRole('button', { name: '订阅推送' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建订阅' })
    await expect(modal.getByTestId('bi-sub-report')).toBeVisible()
    await expect(modal.locator('input[type="number"]')).toHaveCount(0)
    await modal.getByTestId('bi-sub-name').fill(subName)
    await modal.getByTestId('bi-sub-report').selectOption({ label: reportName })
    await modal.getByTestId('bi-sub-channel').selectOption('SITE')
    await modal.getByTestId('bi-sub-save').click()
    const row = page.locator('tr', { hasText: subName })
    await expect(row).toContainText('站内')

    await row.getByTestId('bi-sub-edit').click()
    const edit = page.locator('.modal-mask .card').filter({ hasText: '编辑订阅' })
    await edit.getByTestId('bi-sub-channel').selectOption('MAIL')
    await edit.getByTestId('bi-sub-save').click()
    await expect(page.getByTestId('bi-sub-toast')).toContainText('订阅已保存')
    await expect(row).toContainText('邮件')

    await row.getByTestId('bi-sub-pause').click()
    await expect(page.getByTestId('bi-sub-status-confirm')).toContainText('确认暂停')
    await page.getByTestId('bi-sub-status-ok').click()
    await expect(page.getByTestId('bi-sub-toast')).toContainText('已暂停')
    await expect(row).toContainText('暂停')

    await row.getByTestId('bi-sub-pause').click()
    await expect(page.getByTestId('bi-sub-status-confirm')).toContainText('确认恢复')
    await page.getByTestId('bi-sub-status-ok').click()
    await expect(page.getByTestId('bi-sub-toast')).toContainText('已恢复')
    await expect(row).toContainText('生效')
  })
})
