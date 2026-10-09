import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * 切片 #124 · 内容编辑 AI 文案（acceptance · 纯 UI）
 * Given: 内容列表已有一条草稿
 * When: 编辑抽屉打开 AI 文案 → 选模型、输入提示、生成
 * Then: 预览含提示标记 → 采纳后正文可见该标记，且未自动改版式
 */
test.describe('content AI copy closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('open AI, generate, adopt into body', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const marker = `E2E-AI-COPY-${Date.now()}`
    const title = `E2E AI文案 ${marker}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && !r.url().includes('/ai-content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number }
    expect(createBody.code).toBe(0)

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await editDrawer.getByRole('button', { name: 'AI 文案' }).click()

    const aiDrawer = page.locator('.drawer.on').filter({ hasText: '选择模型并输入提示' })
    await expect(aiDrawer.locator('select')).toBeVisible()
    await expect(aiDrawer.locator('select option').first()).toContainText(/qwen|gpt|模型/i, { timeout: 15_000 })
    await aiDrawer.locator('textarea').fill(`${marker} 写一段赛后复盘`)

    const genResp = page.waitForResponse(
      (r) => r.url().includes('/content/ai-content/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await aiDrawer.getByRole('button', { name: '生成', exact: true }).click()
    const genBody = (await (await genResp).json()) as { code: number; data?: { markdown?: string; layoutApplied?: boolean } }
    expect(genBody.code).toBe(0)
    expect(genBody.data?.layoutApplied).toBe(false)
    await expect(aiDrawer.locator('.ai-copy-preview')).toContainText(marker)

    await aiDrawer.getByRole('button', { name: '采纳' }).click()
    await expect(aiDrawer).toBeHidden({ timeout: 10_000 })
    const bodyField = editDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea')
    await expect(bodyField).toHaveValue(new RegExp(marker))
    expect(pageErrors).toEqual([])
  })
})
