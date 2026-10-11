import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAs } from './closure-helpers'

/**
 * BUG-058：tc_r5 侧栏不再出现数据分析下的查询/穿透菜单。
 * C054：组织人效单独保留，父级「数据分析」因此可见。
 */
test.describe('R5 sidebar drops data analysis', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('tc_r5 has no 数据分析 folder', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAs(page, 'tc_r5')
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '个人工作台' })).toBeVisible()
    await expect(page.locator('.nav-parent').filter({ hasText: '数据分析' })).toBeVisible()
    await expect(page.getByTestId('nav-leaf').filter({ hasText: '组织人效' })).toBeVisible()
    for (const name of ['查询工具', '自定义查询', '预览与下钻', '穿透查询', '全链路看板']) {
      await expect(page.getByTestId('nav-leaf').filter({ hasText: name })).toHaveCount(0)
    }
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
