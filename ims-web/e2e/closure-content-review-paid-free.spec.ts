import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #119）
 * Given: e2e_author 用正文 ---FREE--- 与 matchScheme 创建并提审
 * When: admin 打开 `/ims/content/review` 审核抽屉
 * Then: 场次列表只读 · layout 正文 fallback · 付费/免费双栏 disabled
 *
 * 假设：无 paid_body/free_body 列。UI 可写路径用正文分隔行派生双栏。
 */
test.describe('content review paid/free readonly columns', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('review drawer shows session list and disabled paid/free columns', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-rvpf-${Date.now()}`
    const title = `E2E 审核双栏 ${label}`
    const body = '付费推荐：主胜\n---FREE---\n免费导读：赛前看点'

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await contentDrawer.getByPlaceholder('matchId').fill('m119')
    await contentDrawer.getByPlaceholder('主队').fill('曼联')
    await contentDrawer.getByPlaceholder('客队').fill('切尔西')
    await contentDrawer.getByRole('button', { name: '添加场次' }).click()
    await contentDrawer.getByRole('button', { name: '确定玩法' }).click()
    await contentDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(body)
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
    await page.goto('/ims/content/review')
    await page.locator('.tab', { hasText: '一级审核' }).click()
    await page.locator('input[placeholder="标题"]').fill(title)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/content/review') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const reviewRow = page.locator('tr', { hasText: title }).first()
    await expect(reviewRow).toBeVisible({ timeout: 15_000 })
    await reviewRow.getByRole('button', { name: '审核' }).click()

    const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '审核' })
    const paid = reviewDrawer.getByTestId('content-review-paid')
    const free = reviewDrawer.getByTestId('content-review-free')
    await expect(paid).toHaveValue('付费推荐：主胜', { timeout: 15_000 })
    await expect(free).toHaveValue('免费导读：赛前看点')
    await expect(paid).toBeDisabled()
    await expect(free).toBeDisabled()
    await expect(reviewDrawer.getByTestId('content-review-paid-free')).toHaveAttribute('data-split', 'body-marker')
    await expect(reviewDrawer.getByTestId('content-review-paywall')).toHaveText('含付费')
    await expect(reviewDrawer.getByTestId('content-review-session')).toContainText('曼联 VS 切尔西')
    await expect(reviewDrawer.getByTestId('content-review-layout')).toContainText('付费推荐：主胜')
    await expect(reviewDrawer.getByTestId('content-review-layout')).toContainText('---FREE---')
    await expect(reviewDrawer.getByTestId('content-review-play-tabs')).toBeVisible()

    const shotDir = process.env.IMS_ARTIFACT_DIR || 'test-results'
    await reviewDrawer.getByTestId('content-review-paid-free').screenshot({
      path: `${shotDir}/content-review-paid-free-columns.png`,
    })
    await reviewDrawer.getByTestId('content-review-layout').screenshot({
      path: `${shotDir}/content-review-layout-fallback.png`,
    })
    await reviewDrawer.screenshot({ path: `${shotDir}/content-review-paid-free.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
