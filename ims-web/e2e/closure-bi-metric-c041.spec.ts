import { expect, test } from '@playwright/test'
import { loginAs } from './closure-helpers'

/** BUG-C041 · 结果查询抽屉、导出、删除确认。被引用 1502 在 pytest 覆盖。 */
test.describe('bi metric chrome C041', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('tc_r9 opens result query, exports, and confirms delete', async ({ page }) => {
    test.setTimeout(120_000)
    const code = `C041_${Date.now()}`
    const name = `C041删除${Date.now()}`

    await loginAs(page, 'tc_r9')
    await page.goto('/ims/bi/metric')
    await expect(page.locator('h1')).toContainText('指标管理')

    await page.getByTestId('bi-metric-result-query').click()
    const history = page.getByTestId('bi-metric-history')
    await expect(history).toContainText('本期不做')
    await expect(history.getByRole('link', { name: '前往数据报表' })).toHaveAttribute('href', /\/ims\/bi\/report\/list/)
    await history.getByRole('button', { name: '关闭' }).click()
    await expect(history).toBeHidden()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('bi-metric-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('指标')
    await expect(page.getByTestId('bi-metric-toast')).toContainText('已导出')

    await page.getByRole('button', { name: '新建指标' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await modal.getByTestId('bi-metric-name').fill(name)
    await modal.getByTestId('bi-metric-code').fill(code)
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })

    const row = page.locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    page.once('dialog', (dialog) => {
      expect(dialog.message()).toContain('确认删除指标')
      expect(dialog.message()).toContain(name)
      dialog.accept()
    })
    await row.getByRole('button', { name: '删除' }).click()
    await expect(page.getByTestId('bi-metric-toast')).toContainText('指标已删除')
    await expect(page.locator('tbody tr', { hasText: code })).toHaveCount(0)
  })
})
