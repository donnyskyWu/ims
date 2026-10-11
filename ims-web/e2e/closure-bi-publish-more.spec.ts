import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-C036：保存并发布打开发布配置；卡片「更多」含复制、删除、导出模板、发布管理；页面显示版本号。
 */
test.describe('bi publish config C036', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('publish drawer then more menu copy export and manage', async ({ page }) => {
    test.setTimeout(90_000)
    const reportName = `E2E 发布 ${Date.now()}`
    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(reportName)
    await reportModal.getByRole('button', { name: '创建并进入设计器' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器')
    await expect(page.locator('.pg-h .sub')).toContainText('v1')

    await page.getByTestId('bi-publish').click()
    const drawer = page.getByTestId('bi-publish-drawer')
    await expect(drawer).toContainText('发布配置')
    await expect(drawer.getByTestId('bi-publish-dest')).toBeVisible()
    await expect(drawer.getByTestId('bi-publish-scope')).toBeVisible()
    await expect(drawer.getByTestId('bi-publish-op')).toBeVisible()
    await expect(drawer.getByTestId('bi-publish-row')).toBeVisible()
    await expect(drawer.getByTestId('bi-publish-scope').locator('option')).toHaveText(['私有', '指定人', '全员'])
    await drawer.getByTestId('bi-publish-scope').selectOption('ALL')
    await drawer.getByTestId('bi-publish-op').selectOption('EXPORT')
    await drawer.getByTestId('bi-publish-row').selectOption('INHERIT')
    await drawer.getByTestId('bi-publish-now').click()
    await expect(page.getByTestId('bi-save-status')).toContainText('已发布', { timeout: 15_000 })
    await expect(page.locator('.pg-h .sub')).toContainText('v1')

    await page.getByTestId('bi-back').click()
    await expect(page.locator('h1')).toContainText('报表管理')
    const card = page.locator('.card', { hasText: reportName }).first()
    await expect(card).toContainText('v1')
    await expect(card).toContainText('可导出')
    await card.getByTestId('bi-more').click()
    const menu = card.getByTestId('bi-more-menu')
    await expect(menu.getByTestId('bi-more-copy')).toBeVisible()
    await expect(menu.getByTestId('bi-more-delete')).toBeVisible()
    await expect(menu.getByTestId('bi-more-export')).toBeVisible()
    await expect(menu.getByTestId('bi-more-publish')).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await menu.getByTestId('bi-more-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('.json')

    await card.getByTestId('bi-more').click()
    await card.getByTestId('bi-more-publish').click()
    const manage = page.getByTestId('bi-publish-manage')
    await expect(manage).toContainText('发布管理')
    await expect(manage.getByTestId('bi-publish-row').first()).toContainText('报表中心')
    await expect(page.getByTestId('bi-filter-scope').locator('option', { hasText: '全员' })).toHaveCount(1)
    await expect(card).toContainText('全员')
    await expect(manage.getByTestId('bi-publish-row').first()).toContainText('全员')
    await manage.getByRole('button', { name: '关闭' }).click()

    await card.getByTestId('bi-more').click()
    await card.getByTestId('bi-more-copy').click()
    await expect(page.getByTestId('bi-action-msg')).toContainText('副本')
    await expect(page.locator('.card', { hasText: `${reportName}副本` }).first()).toContainText('v1')
  })
})
