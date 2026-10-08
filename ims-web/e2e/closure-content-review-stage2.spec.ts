import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs, passContentReviewViaUi } from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #42）
 * Given: e2e_author 立项/提审 · admin 一级审核通过
 * When: `/ims/content/review`「二级审核」Tab 查询
 * Then: 轮次 2 可见 · 二级通过 · Tab 空态「暂无待审」
 */
test.describe('content review stage2 tab closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('level1 pass then stage2 tab approve clears queue', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-rv2-${Date.now()}`
    const title = `E2E 二级审核 ${label}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    await createResp

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '提审' }).click()
    await expect(contentRow).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)
    await passContentReviewViaUi(page, { title, stageTab: '一级审核' })

    await page.goto('/ims/content/review')
    await page.locator('.tab', { hasText: '一级审核' }).click()
    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.tbl-wrap tbody tr', { hasText: title })).toHaveCount(0)

    await page.locator('.tab', { hasText: '二级审核' }).click()
    await expect(page.locator('.tab.on', { hasText: '二级审核' })).toBeVisible()
    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    const stage2Row = page.locator('tr', { hasText: title }).first()
    await expect(stage2Row).toBeVisible({ timeout: 15_000 })
    await expect(stage2Row.locator('td.num').first()).toHaveText('2')

    await passContentReviewViaUi(page, { title, stageTab: '二级审核' })

    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.empty .et', { hasText: '暂无待审' })).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
