import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * TC-13 数据上报（BUG-B043～B047）纯 UI。
 * 不删除环境中的模板 RT20261011001。
 */
test.describe('report tc13 closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('template edit, create validation, submit error, and pass-rate chart', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/report/template')
    await expect(page.locator('h1')).toHaveText('上报模板')
    await expect(page.locator('.page')).not.toContainText('/admin-api')
    await expect(page.locator('.page')).not.toContainText('09 REPORT')

    const preserved = page.locator('tr', { hasText: 'RT20261011001' })
    if (await preserved.count()) {
      await preserved.first().getByTestId('tpl-edit').click()
      await expect(page.getByTestId('tpl-edit-drawer')).toBeVisible()
      await expect(page.getByRole('button', { name: '字段定义' })).toBeVisible()
      await expect(page.getByRole('button', { name: '勾稽规则' })).toBeVisible()
      await expect(page.getByRole('button', { name: '填报人' })).toBeVisible()
      await page.getByTestId('tpl-edit-drawer').getByRole('button', { name: '取消' }).click()
    }

    await page.getByTestId('tpl-create-open').click()
    await expect(page.getByTestId('tpl-create-dialog')).toBeVisible()
    await page.getByTestId('tpl-create').click()
    await expect(page.getByTestId('tpl-create-dialog')).toContainText('必填项，请填写')

    const name = `E2E上报模板${Date.now()}`
    await page.getByTestId('tpl-name').fill(name)
    await page.getByTestId('tpl-frequency').selectOption({ label: '每日 18:00 前' })
    await page.getByTestId('tpl-dept').selectOption({ label: '运营中心' })
    await page.getByTestId('tpl-line').selectOption({ label: '业务' })
    await page.getByTestId('tpl-field-count').fill('1')
    await page.getByTestId('tpl-create').click()
    await expect(page.getByTestId('tpl-toast')).toContainText('模板已创建')

    const created = page.locator('tr', { hasText: name })
    await expect(created).toContainText('每日 18:00 前')
    await created.getByTestId('tpl-edit').click()
    await expect(page.getByTestId('tpl-edit-drawer')).toBeVisible()
    await expect(page.getByRole('button', { name: '字段定义' })).toBeVisible()
    await expect(page.getByRole('button', { name: '勾稽规则' })).toBeVisible()
    await expect(page.getByRole('button', { name: '填报人' })).toBeVisible()
    await page.getByTestId('tpl-edit-drawer').getByRole('button', { name: '取消' }).click()

    await created.getByTestId('tpl-disable').click()
    await expect(page.getByTestId('tpl-disable-confirm')).toBeVisible()
    await page.getByTestId('tpl-disable-ok').click()
    await expect(page.getByTestId('tpl-toast')).toContainText('模板已停用')

    await page.goto('/ims/report/submission')
    await expect(page.locator('h1')).toHaveText('填报单管理')
    await expect(page.locator('.page')).not.toContainText('/admin-api')
    await expect(page.locator('.page')).not.toContainText('GET /report')
    await expect(page.getByTestId('filter-author')).toBeVisible()
    await expect(page.getByTestId('filter-account')).toBeVisible()
    await expect(page.locator('thead')).toContainText('提交时间')
    await expect(page.locator('thead')).toContainText('数据量')

    await page.getByTestId('submit-open').click()
    await expect(page.getByTestId('submit-dialog')).toBeVisible()
    await expect(page.getByTestId('submit-template')).toBeVisible()
    await expect(page.getByTestId('submit-author')).toBeVisible()
    await page.getByTestId('submit-send').click()
    await expect(page.getByTestId('submit-error')).toContainText('请选择作者（AuthorSelect）')
    await page.getByTestId('submit-dialog').getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/report/stat')
    await expect(page.locator('h1')).toHaveText('完成率统计')
    const completeCard = page.getByTestId('stat-complete-card')
    await expect(completeCard).toContainText('完成率')
    await expect(completeCard).toContainText('应提交')
    await expect(completeCard).toContainText('95%')
    await expect(completeCard).not.toContainText('已提交')
    await expect(page.getByTestId('stat-complete-rate')).toBeVisible()
    await expect(page.getByTestId('stat-target-line')).toBeVisible()
    const passCard = page.getByTestId('stat-pass-card')
    await expect(passCard).toContainText('通过率')
    await expect(passCard).toContainText('已提交')
    await expect(passCard).not.toContainText('应提交')
    await expect(passCard).not.toContainText('95%')
    await expect(page.getByTestId('stat-trend')).toBeVisible()
    await expect(page.getByTestId('stat-template')).toBeVisible()
    await expect(page.locator('.page')).not.toContainText('/admin-api')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
