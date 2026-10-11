import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** 验收：组件面板恰好 22 格，名称与规格第 80～83 行、BiCompType 一致。 */
const PALETTE = [
  ['KPI', 'KPI 指标卡'],
  ['BAR', '柱状图'],
  ['LINE', '折线图'],
  ['PIE', '饼图'],
  ['DONUT', '环形图'],
  ['RADAR', '雷达图'],
  ['FUNNEL', '漏斗图'],
  ['SCATTER', '散点图'],
  ['TABLE', '数据表'],
  ['DETAIL_TABLE', '明细表'],
  ['RICH_TEXT', '富文本'],
  ['DATE_RANGE', '日期范围'],
  ['SELECT_SINGLE', '下拉单选'],
  ['SELECT_MULTI', '下拉多选'],
  ['TEXT_INPUT', '文本输入'],
  ['NUMBER_RANGE', '数值区间'],
  ['GROUP', '分组容器'],
  ['CARD', '卡片容器'],
  ['TAB', 'Tab 容器'],
  ['BUTTON', '按钮'],
  ['LINK', '跳转链接'],
  ['TRIGGER', '联动触发件'],
] as const

test.describe('bi component library', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('palette is exactly 22 spec cells', async ({ page }) => {
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
    await expect(page.getByTestId('bi-comp-group-CHART').locator('[data-testid^="bi-palette-"]')).toHaveCount(11)
    await expect(page.getByTestId('bi-comp-group-FILTER').locator('[data-testid^="bi-palette-"]')).toHaveCount(5)
    await expect(page.getByTestId('bi-comp-group-CONTAINER').locator('[data-testid^="bi-palette-"]')).toHaveCount(3)
    await expect(page.getByTestId('bi-comp-group-ACTION').locator('[data-testid^="bi-palette-"]')).toHaveCount(3)
    await expect(page.getByTestId('bi-palette-AREA')).toHaveCount(0)
    await expect(page.getByTestId('bi-palette-CASCADE')).toHaveCount(0)

    const labels = (await palette.allInnerTexts()).map((text) => text.replace(/^\+\s*/, '').trim())
    expect(labels).toEqual(PALETTE.map(([, name]) => name))
    for (const [type, name] of PALETTE) {
      await expect(page.getByTestId(`bi-palette-${type}`)).toContainText(name)
    }
  })
})
