import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * 组件库按页面规格表格列出的名单：图表 11、查询条件 5、容器 3、交互 3。
 * 不含面积图、级联。
 */
test.describe('bi component library', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('palette matches the spec list', async ({ page }) => {
    test.setTimeout(60_000)
    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await reportModal.locator('input.fld-in').first().fill(`E2E 组件库 ${Date.now()}`)
    await reportModal.getByRole('button', { name: '创建并进入设计器' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器')

    const palette = page.locator('[data-testid^="bi-palette-"]')
    await expect(palette).toHaveCount(22)
    await expect(page.getByTestId('bi-palette-AREA')).toHaveCount(0)
    await expect(page.getByTestId('bi-palette-CASCADE')).toHaveCount(0)
    await expect(page.getByTestId('bi-palette-KPI')).toContainText('KPI 指标卡')
    await expect(page.getByTestId('bi-palette-TABLE')).toContainText('数据表')
    await expect(page.getByTestId('bi-palette-RICH_TEXT')).toContainText('富文本')
    await expect(page.getByTestId('bi-palette-DATE_RANGE')).toContainText('日期范围')
    await expect(page.getByTestId('bi-palette-NUMBER_RANGE')).toContainText('数值区间')
    await expect(page.getByTestId('bi-palette-GROUP')).toContainText('分组容器')
    await expect(page.getByTestId('bi-palette-TRIGGER')).toContainText('联动触发件')
  })
})
