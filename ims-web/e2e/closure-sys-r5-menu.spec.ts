import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAs } from './closure-helpers'

/**
 * BUG-058：tc_r5 侧栏不再出现数据分析及其子菜单。启动矩阵同步后与 R5 一致。
 */
test.describe('R5 sidebar drops data analysis', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('tc_r5 has no 数据分析 folder', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAs(page, 'tc_r5')
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '个人工作台' })).toBeVisible()
    await expect(page.locator('.nav-parent').filter({ hasText: '数据分析' })).toHaveCount(0)
    for (const name of ['查询工具', '自定义查询', '预览与下钻', '穿透查询', '全链路看板', '组织人效']) {
      await expect(page.getByTestId('nav-leaf').filter({ hasText: name })).toHaveCount(0)
    }
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
