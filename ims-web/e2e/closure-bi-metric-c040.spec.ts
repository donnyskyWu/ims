import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * BUG-C040 · 复合指标公式白名单（admin；tc_r9 走标准 R9，不在此克隆全菜单）
 * 保存 DELETE 被拦；合法公式可保存并试算。存量非法公式的试算拒绝在 pytest 覆盖。
 */
test.describe('bi metric formula C040', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('cannot save DELETE formula and can preview a whitelist formula', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const legalName = `C040合法试算${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/bi/metric')
    await expect(page.locator('h1')).toContainText('指标管理')

    await page.getByRole('button', { name: '新建指标' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await modal.getByTestId('bi-metric-name').fill('C040注入')
    await modal.getByTestId('bi-metric-code').fill('C040_INJECT')
    await modal.getByTestId('bi-metric-type').selectOption('COMPOSITE')
    await modal.getByTestId('bi-metric-formula').fill('DELETE FROM x')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('bi-metric-form-error')).toContainText('1192')
    await expect(modal.getByTestId('bi-metric-form-error')).toContainText('DELETE')
    await expect(page.locator('tbody tr', { hasText: 'C040注入' })).toHaveCount(0)

    await modal.getByTestId('bi-metric-name').fill(legalName)
    await modal.getByTestId('bi-metric-code').fill(`C040_OK_${Date.now()}`)
    await modal.getByTestId('bi-metric-formula').fill('INTERACTION_COUNT / TC_PLAY * 100')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })

    const row = page.locator('tbody tr', { hasText: legalName })
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: '试算' }).click()
    const result = page.getByTestId('bi-metric-preview-result')
    await expect(result).toBeVisible()
    await expect(result).toContainText(legalName)
    await expect(result).toContainText('=')
    await expect(page.getByTestId('bi-metric-preview-error')).toHaveCount(0)
    expect(pageErrors).toEqual([])
  })
})
