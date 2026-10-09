import { mkdirSync } from 'node:fs'

import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #117）
 * Given: 内容保存 matchType=传足 + 两场 matchScheme 后提审
 * When: `/ims/content/review` 打开审核抽屉
 * Then: 只读 Tab「传足」+ 场次列表 + 玩法摘要；Tab 不可切换，无保存/确定玩法
 */
test.describe('content review readonly sessions', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('review drawer lists match sessions without edit controls', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const title = `E2E 审核场次 e2e-sess-${Date.now()}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await contentDrawer.locator('.tab', { hasText: '传足' }).click()
    async function addMatch(matchId: string, homeName: string, awayName: string) {
      await contentDrawer.getByPlaceholder('matchId').fill(matchId)
      await contentDrawer.getByPlaceholder('主队').fill(homeName)
      await contentDrawer.getByPlaceholder('客队').fill(awayName)
      await contentDrawer.getByRole('button', { name: '添加场次' }).click()
    }
    await addMatch('88001', '曼联', '切尔西')
    await addMatch('88002', '皇马', '巴萨')
    await contentDrawer.getByRole('button', { name: '确定玩法' }).click()
    await expect(contentDrawer.getByText('已确定 2 场')).toBeVisible()
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    await createResp

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await expect(contentRow).toContainText('2场')
    await contentRow.getByRole('button', { name: '提审' }).click()
    await expect(contentRow).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)
    await page.goto('/ims/content/review')
    await page.locator('.tab', { hasText: '一级审核' }).click()
    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    const reviewRow = page.locator('tr', { hasText: title }).first()
    await expect(reviewRow).toBeVisible({ timeout: 15_000 })
    await expect(reviewRow.getByTestId('review-queue-match')).toHaveText('2场')
    await reviewRow.getByRole('button', { name: '审核' }).click()

    const drawer = page.locator('.drawer.on').filter({ hasText: '审核' })
    await expect(drawer.getByTestId('review-session-list')).toBeVisible()
    await expect(drawer.getByTestId('review-play-summary')).toHaveText('玩法摘要：2场')
    await expect(drawer.getByTestId('review-match-tab').filter({ hasText: '传足' })).toHaveClass(/on/)
    await expect(drawer.getByTestId('review-match-tab').filter({ hasText: '竞足' })).not.toHaveClass(/on/)
    const sessionRows = drawer.getByTestId('review-session-row')
    await expect(sessionRows).toHaveCount(2)
    await expect(sessionRows.nth(0)).toContainText('曼联 VS 切尔西')
    await expect(sessionRows.nth(1)).toContainText('皇马 VS 巴萨')
    await drawer.getByTestId('review-match-tab').filter({ hasText: '竞足' }).click({ force: true })
    await expect(drawer.getByTestId('review-match-tab').filter({ hasText: '传足' })).toHaveClass(/on/)
    await expect(drawer.getByRole('button', { name: '保存' })).toHaveCount(0)
    await expect(drawer.getByRole('button', { name: '确定玩法' })).toHaveCount(0)
    await expect(drawer.getByTestId('content-review-reject-opinion')).toHaveCount(1)
    await expect(drawer.getByTestId('content-review-paid')).toBeDisabled()
    await expect(drawer.getByTestId('content-review-free')).toBeDisabled()
    await expect(drawer.locator('textarea:not([disabled])')).toHaveCount(1)

    mkdirSync('/opt/cursor/artifacts/e2e-117-screenshots', { recursive: true })
    await page.screenshot({
      path: '/opt/cursor/artifacts/e2e-117-screenshots/review-drawer-page.png',
      fullPage: true,
    })
    await drawer.screenshot({ path: '/opt/cursor/artifacts/e2e-117-screenshots/review-session-list.png' })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
