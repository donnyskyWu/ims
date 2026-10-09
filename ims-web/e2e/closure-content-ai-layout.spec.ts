import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * Checklist E2E-S7 切片（acceptance · 纯 UI · #125）
 * Given: 文章正文已保存
 * When: 编辑抽屉点「AI 语义排版」→ 预览 → 写回
 * Then: 正文纯文本仍在；审核抽屉只读同一版式
 */
test.describe('content ai semantic layout closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('preview apply then review drawer is readonly', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-ai-layout-${Date.now()}`
    const title = `E2E 语义排版 ${label}`
    const body = '周日焦点战\n主队状态稳定，客队防守一般。'

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await createDrawer.locator('.fld').filter({ hasText: '内容类型' }).locator('input').fill('ARTICLE')
    await createDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(body)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number }
    expect(createBody.code).toBe(0)

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await editDrawer.getByRole('button', { name: 'AI 语义排版' }).click()
    const previewResp = page.waitForResponse(
      (r) => r.url().includes('/typeset/preview') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: 'AI 排版预览' }).click()
    const previewBody = (await (await previewResp).json()) as {
      code: number
      data?: { selectedTemplateName?: string; layoutHtml?: string }
    }
    expect(previewBody.code).toBe(0)
    await expect(editDrawer.getByText('已选版式：决策扫读版')).toBeVisible()
    await expect(editDrawer.locator('.layout-viewer').filter({ hasText: '主队状态稳定' })).toBeVisible()

    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/typeset/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '写回版式' }).click()
    const applyBody = (await (await applyResp).json()) as { code: number; data?: { body?: string } }
    expect(applyBody.code).toBe(0)
    expect(applyBody.data?.body).toBe(body)
    await expect(editDrawer.getByText('AI 排版已写回，正文未改动')).toBeVisible()
    await expect(editDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea')).toHaveValue(body)

    await editDrawer.getByRole('button', { name: '取消' }).click()
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
    const viewer = reviewDrawer.locator('.layout-viewer[data-readonly="true"]')
    await expect(viewer).toBeVisible()
    await expect(viewer).toContainText('主队状态稳定，客队防守一般。')
    await expect(reviewDrawer.getByRole('button', { name: 'AI 语义排版' })).toHaveCount(0)
    await expect(reviewDrawer.getByRole('button', { name: '写回版式' })).toHaveCount(0)
    await expect(reviewDrawer.locator('textarea')).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})