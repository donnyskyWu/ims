import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  BI_R4_VIEWER,
  BR212_PREFIX,
  loginAdmin,
  loginAs,
} from './closure-helpers'

/**
 * Checklist **E2E-S12-05 切片**（acceptance · **纯 UI** · #45）
 * BR-212：管理员 vs 本部门查看者可见报表/分享行集不同
 */
test.describe('bi BR-212 row scope closure S12', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  async function br212RowsOnReportList(page: import('@playwright/test').Page) {
    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')
    await page.locator('input[placeholder="名称/编号"]').fill(BR212_PREFIX)
    await page.getByRole('button', { name: '查询' }).click()
    await page.getByRole('button', { name: '列表' }).click()
    await page.locator('.tbl-wrap tbody tr').filter({ hasText: BR212_PREFIX }).first().waitFor({
      state: 'visible',
      timeout: 15_000,
    })
    return page.locator('.tbl-wrap tbody tr').filter({ hasText: BR212_PREFIX })
  }

  test('admin sees all BR212 seed reports; dept viewer sees dept-11 only', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    await loginAdmin(page)
    const adminRows = await br212RowsOnReportList(page)
    await expect(adminRows).toHaveCount(3)
    await expect(adminRows.filter({ hasText: `${BR212_PREFIX}dept12-C` })).toHaveCount(1)

    await loginAs(page, BI_R4_VIEWER)
    const viewerRows = await br212RowsOnReportList(page)
    await expect(viewerRows).toHaveCount(2)
    await expect(viewerRows.filter({ hasText: `${BR212_PREFIX}dept12-C` })).toHaveCount(0)

    await page.goto('/ims/bi/report/subscribe?tab=share')
    await expect(page.locator('h1')).toContainText('订阅与分享')
    const shareRows = page.locator('.tbl-wrap tbody tr').filter({ hasText: BR212_PREFIX })
    await expect(shareRows).toHaveCount(1)
    await expect(shareRows.first()).toContainText(`${BR212_PREFIX}dept11-A`)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
