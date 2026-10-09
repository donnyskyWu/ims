import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * 切片 #121（acceptance · 纯 UI）
 * Given: 作者保存带正文的内容
 * When: 编辑页套用版式模板 → 预览并应用规则一键排版 → 保存提审
 * Then: 正文纯文本仍在 · 审核抽屉只读版式可见同一正文
 */
test.describe('content typeset layout closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('apply template then one-click typeset is visible on review', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-typeset-${Date.now()}`
    const title = `E2E 排版 ${label}`
    const sentence = `主队近期状态回升，客队防守不稳。${label}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })

    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await createDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(sentence)
    const createResp = page.waitForResponse(
      (r) => /\/content$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number }
    expect(createBody.code).toBe(0)

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('content-layout-panel')).toBeVisible()
    const templateSelect = editDrawer.getByTestId('content-layout-template')
    await expect(templateSelect.locator('option', { hasText: '清爽阅读' })).toBeAttached({ timeout: 15_000 })
    await templateSelect.selectOption({ label: '清爽阅读' })

    const templateResp = page.waitForResponse(
      (r) => r.url().includes('/typeset/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByTestId('content-layout-apply-template').click()
    const templateBody = (await (await templateResp).json()) as {
      code: number
      data?: { body?: string; bodyFormat?: string; layoutHtml?: string }
    }
    expect(templateBody.code).toBe(0)
    expect(templateBody.data?.bodyFormat).toBe('LAYOUT')
    expect(templateBody.data?.body).toContain(sentence)
    expect(templateBody.data?.layoutHtml).toContain(sentence)
    await expect(editDrawer.getByTestId('content-layout-before')).toContainText(sentence)
    await expect(editDrawer.getByTestId('content-layout-after')).toContainText(sentence)
    await expect(editDrawer.getByTestId('content-layout-format')).toContainText('LAYOUT')

    await editDrawer.getByTestId('content-layout-preset').selectOption('marketing')
    const previewResp = page.waitForResponse(
      (r) => r.url().includes('/typeset/preview') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByTestId('content-layout-preview-btn').click()
    const previewBody = (await (await previewResp).json()) as {
      code: number
      data?: { fidelityCheck?: { passed?: boolean }; layoutHtml?: string; body?: string }
    }
    expect(previewBody.code).toBe(0)
    expect(previewBody.data?.fidelityCheck?.passed).toBe(true)
    expect(previewBody.data?.body).toContain(sentence)
    await expect(editDrawer.getByTestId('content-layout-after').locator('[data-preset="marketing"]')).toBeVisible()

    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/typeset/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByTestId('content-layout-apply-btn').click()
    const applyBody = (await (await applyResp).json()) as { code: number; data?: { body?: string; layoutHtml?: string } }
    expect(applyBody.code).toBe(0)
    expect(applyBody.data?.body).toContain(sentence)
    expect(applyBody.data?.layoutHtml).toContain('data-preset="marketing"')
    await expect(editDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea')).toHaveValue(sentence)

    const saveResp = page.waitForResponse(
      (r) => /\/content\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存' }).click()
    const saveBody = (await (await saveResp).json()) as { code: number; data?: { bodyFormat?: string; layoutHtml?: string; body?: string } }
    expect(saveBody.code).toBe(0)
    expect(saveBody.data?.body).toContain(sentence)
    expect(saveBody.data?.bodyFormat).toBe('LAYOUT')
    expect(saveBody.data?.layoutHtml).toContain(sentence)

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
    const preview = reviewDrawer.getByTestId('content-layout-preview')
    await expect(preview).toContainText(sentence)
    await expect(preview.locator('[data-preset="marketing"]')).toBeVisible()
    await page.screenshot({ path: '/opt/cursor/artifacts/content-typeset-review.png', fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
