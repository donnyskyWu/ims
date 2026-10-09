import { mkdirSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-114-screenshots'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #114）
 * Given: 内容保存了 layout_html（或仅 body）
 * When: 内容列表「查看」，以及审核抽屉打开同一条内容
 * Then: 有版式时只读渲染消毒后的 HTML；无版式时正文纯文本；查看抽屉不可编辑
 */
test.describe('content list view layout preview closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('view and review render the same read-only layout html', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-view-${Date.now()}`
    const title = `E2E 查看版式 ${label}`
    const plainTitle = `E2E 查看正文 ${label}`
    const layoutText = `版式预览甲${label}`
    const bodyText = `纯文本乙${label}`
    const fallbackBody = `只有正文丙${label}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })

    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await createDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(bodyText)
    await createDrawer.getByTestId('content-layout-html-input').fill(
      `<p>${layoutText}</p><script>window.__imsLayoutXss=1</script><img src="javascript:alert(1)" alt="bad">`,
    )
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number; data?: { layoutHtml?: string } }
    expect(createBody.code).toBe(0)
    expect(createBody.data?.layoutHtml || '').toContain(layoutText)
    expect((createBody.data?.layoutHtml || '').toLowerCase()).not.toContain('<script')
    expect((createBody.data?.layoutHtml || '').toLowerCase()).not.toContain('javascript:')

    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    const detailResp = page.waitForResponse(
      (r) => /\/content\/\d+(\?|$)/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row.getByRole('button', { name: '查看' }).click()
    await detailResp

    const viewDrawer = page.locator('.drawer.on').filter({ hasText: '查看内容' })
    const preview = viewDrawer.getByTestId('content-layout-preview')
    const html = preview.getByTestId('content-layout-html')
    await expect(html).toContainText(layoutText)
    await expect(html).not.toContainText(bodyText)
    await expect(preview.locator('script')).toHaveCount(0)
    await expect(preview.locator('textarea, input, [contenteditable="true"]')).toHaveCount(0)
    await expect(viewDrawer.getByRole('button', { name: '保存' })).toHaveCount(0)
    await expect(viewDrawer.getByRole('button', { name: '提审' })).toHaveCount(0)
    await expect(html).toHaveCSS('max-width', '677px')
    await page.screenshot({ path: `${shotDir}/01-view-layout-html.png` })
    await viewDrawer.getByRole('button', { name: '关闭' }).click()
    await expect(viewDrawer).not.toBeVisible()

    await page.getByRole('button', { name: '新增内容' }).click()
    const plainDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await plainDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(plainTitle)
    await plainDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(fallbackBody)
    const plainResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await plainDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await plainResp).json()) as { code: number }).code).toBe(0)

    await page.locator('input[placeholder="标题"]').fill(plainTitle)
    await page.getByRole('button', { name: '查询' }).click()
    const plainRow = page.locator('tr', { hasText: plainTitle })
    await expect(plainRow).toBeVisible({ timeout: 15_000 })
    await plainRow.getByRole('button', { name: '查看' }).click()
    const plainView = page.locator('.drawer.on').filter({ hasText: '查看内容' })
    await expect(plainView.getByTestId('content-layout-body')).toContainText(fallbackBody)
    await expect(plainView.getByTestId('content-layout-html')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-view-body-fallback.png` })
    await plainView.getByRole('button', { name: '关闭' }).click()

    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    const reviewSource = page.locator('tr', { hasText: title })
    await expect(reviewSource).toBeVisible({ timeout: 15_000 })
    await reviewSource.getByRole('button', { name: '提审' }).click()
    await expect(reviewSource).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)
    await page.goto('/ims/content/review')
    await page.locator('.tab', { hasText: '一级审核' }).click()
    await page.locator('input[placeholder="标题"]').fill(title)
    await page.getByRole('button', { name: '查询' }).click()
    const reviewRow = page.locator('tr', { hasText: title }).first()
    await expect(reviewRow).toBeVisible({ timeout: 15_000 })
    await reviewRow.getByRole('button', { name: '审核' }).click()
    const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '审核' })
    const reviewHtml = reviewDrawer.getByTestId('content-layout-html')
    await expect(reviewHtml).toContainText(layoutText, { timeout: 15_000 })
    await expect(reviewHtml).not.toContainText(bodyText)
    await expect(reviewDrawer.getByTestId('content-layout-preview').locator('script, textarea')).toHaveCount(0)
    await expect(reviewHtml).toHaveCSS('max-width', '677px')
    await page.screenshot({ path: `${shotDir}/03-review-same-layout.png` })

    const boxes = reviewDrawer.locator('input[type="checkbox"]')
    const n = await boxes.count()
    for (let i = 0; i < n; i++) await boxes.nth(i).check()
    const concludeResp = page.waitForResponse(
      (r) =>
        r.url().includes('/content/review/') &&
        r.url().includes('/conclusion') &&
        r.request().method() === 'PUT' &&
        r.status() === 200,
    )
    await reviewDrawer.getByRole('button', { name: '通过' }).click()
    expect(((await (await concludeResp).json()) as { code: number }).code).toBe(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
