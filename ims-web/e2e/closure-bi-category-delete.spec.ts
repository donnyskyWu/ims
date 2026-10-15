import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * 分类删除按页面规格 §7.7 / S9：非空分类阻断，空分类可删，「未分类」不能删也不能改名。
 */
test.describe('bi category delete guard', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('block occupied category and protect 未分类', async ({ page }) => {
    test.setTimeout(90_000)
    const stamp = Date.now()
    const emptyName = `E2E空类${stamp}`
    const busyName = `E2E有报表${stamp}`
    const reportName = `E2E分类报表${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await page.getByTestId('bi-cat-manage').click()
    const dialog = page.getByTestId('bi-cat-dialog')
    const fallback = dialog.locator('tr', { hasText: '未分类' })
    await expect(fallback.getByTestId('bi-cat-delete')).toHaveCount(0)
    await expect(fallback.getByTestId('bi-cat-rename')).toHaveCount(0)

    await dialog.getByTestId('bi-cat-name').fill(emptyName)
    await dialog.getByTestId('bi-cat-add').click()
    await expect(dialog.getByTestId('bi-cat-msg')).toContainText('分类已新增')
    await dialog.locator('tr', { hasText: emptyName }).getByTestId('bi-cat-delete').click()
    await expect(dialog.getByTestId('bi-cat-msg')).toContainText('分类已删除')
    await expect(dialog.locator('tr', { hasText: emptyName })).toHaveCount(0)

    await dialog.getByTestId('bi-cat-name').fill(busyName)
    await dialog.getByTestId('bi-cat-add').click()
    await expect(dialog.getByTestId('bi-cat-msg')).toContainText('分类已新增')
    await dialog.getByRole('button', { name: '关闭' }).click()

    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(reportName)
    await reportModal.getByTestId('bi-new-category').selectOption(busyName)
    await reportModal.getByRole('button', { name: '创建并进入设计器' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器')

    await page.goto('/ims/bi/report/list')
    await page.getByTestId('bi-cat-manage').click()
    const again = page.getByTestId('bi-cat-dialog')
    await again.locator('tr', { hasText: busyName }).getByTestId('bi-cat-delete').click()
    await expect(again.getByTestId('bi-cat-error')).toContainText(`该分类下有 1 个报表，请先移动`)
    await expect(again.locator('tr', { hasText: busyName })).toHaveCount(1)
  })
})
