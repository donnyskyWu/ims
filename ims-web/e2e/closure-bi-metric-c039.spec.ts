import { expect, test } from '@playwright/test'
import { loginAs } from './closure-helpers'

/** BUG-C039 · 指标表单字段、编码、名称长度、生成公式、预览、编辑与停用 */
test.describe('bi metric form C039', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('tc_r9 creates a basic metric with formula preview and can disable it', async ({ page }) => {
    test.setTimeout(120_000)
    const code = `TC_PLAY_${Date.now()}`
    const name = `TC播放量${Date.now()}`

    await loginAs(page, 'tc_r9')
    await page.goto('/ims/bi/metric')
    await expect(page.locator('h1')).toContainText('指标管理')
    await expect(page.locator('thead')).toContainText('数据源')
    await expect(page.locator('thead')).toContainText('计算公式')
    await expect(page.locator('thead')).toContainText('单位')

    await page.getByRole('button', { name: '新建指标' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('bi-metric-name-error')).toContainText('必填项，请填写')
    await expect(modal.getByTestId('bi-metric-code-error')).toContainText('必填项，请填写')

    await modal.getByTestId('bi-metric-name').fill('测'.repeat(51))
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('bi-metric-name-error')).toContainText('50')

    await modal.getByTestId('bi-metric-name').fill(name)
    await modal.getByTestId('bi-metric-code').fill(code)
    await modal.getByTestId('bi-metric-unit').fill('次')
    await modal.getByTestId('bi-metric-freq').selectOption('DAILY')
    await modal.getByTestId('bi-metric-source').selectOption('oa_content_metric')
    await modal.getByTestId('bi-metric-method').selectOption('SUM')
    await modal.getByTestId('bi-metric-calc-field').selectOption('play_count')
    await modal.getByTestId('bi-metric-summary').selectOption('ip_group_name')
    await modal.getByTestId('bi-metric-cond-param').check()
    await modal.getByTestId('bi-metric-add-cond').click()
    await modal.getByRole('button', { name: '删除' }).last().click()
    await modal.getByRole('button', { name: '删除' }).click()
    await expect(modal.getByTestId('bi-metric-cond-error')).toContainText('至少保留一个条件行')

    await modal.getByTestId('bi-metric-gen').click()
    await expect(modal.getByTestId('bi-metric-formula')).toHaveValue(/SELECT/i)
    const formula = await modal.getByTestId('bi-metric-formula').inputValue()
    expect(formula.toUpperCase()).not.toContain('DELETE')

    await modal.getByTestId('bi-metric-preview-data').click()
    await expect(modal.getByTestId('bi-metric-draft-table')).toContainText('电竞一组')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })
    const row = page.locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await expect(row).toContainText('次')

    await page.getByRole('button', { name: '新建指标' }).click()
    const again = page.locator('.modal-mask .card').filter({ hasText: '新建指标' })
    await again.getByTestId('bi-metric-name').fill(`${name}重复`)
    await again.getByTestId('bi-metric-code').fill(code)
    await again.getByRole('button', { name: '保存' }).click()
    await expect(again.getByTestId('bi-metric-code-error')).toContainText('编码已存在')
    await again.getByRole('button', { name: '取消' }).click()

    await row.getByRole('button', { name: '编辑' }).click()
    const edit = page.locator('.modal-mask .card').filter({ hasText: '编辑指标' })
    await edit.getByTestId('bi-metric-name').fill(`${name}改`)
    await edit.getByRole('button', { name: '保存' }).click()
    await expect(edit).toBeHidden({ timeout: 15_000 })
    await expect(page.locator('tbody tr', { hasText: code })).toContainText(`${name}改`)

    await page.locator('tbody tr', { hasText: code }).getByRole('button', { name: '停用' }).click()
    await expect(page.getByTestId('bi-metric-toast')).toContainText('已停用')
    await expect(page.locator('tbody tr', { hasText: code })).toContainText('停用')
  })
})