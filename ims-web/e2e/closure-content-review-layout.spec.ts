import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAgCAIAAADbtmxLAAAAMUlEQVR42u3OMQ0AAAgDsEmafy2IwQXhaFIBzbSvREhISEhISEhISEhISEhISEjo0gKJWmhqLudyPwAAAABJRU5ErkJggg=='

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #112）
 * Given: 内容保存 layout_html（含 img）或仅 body
 * When: `/ims/content/review` 打开审核抽屉
 * Then: 有版式时只读渲染 HTML 与图片；无版式时纯文本 fallback，不把 body 当 HTML
 */
test.describe('content review layout viewer closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('review drawer renders layout html image and plain body fallback', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const layoutTitle = `E2E 审核版式 ${stamp}`
    const plainTitle = `E2E 审核纯文本 ${stamp}`
    const layoutHtml =
      `<p onclick="window.__imsXss=1">版式可见标记</p>` +
      `<img src="${PNG}" alt="已插入图片" data-w="120" style="width:120px">` +
      `<script>window.__imsXss=1</script>`
    const hiddenBody = '纯文本摘要不应出现'
    const plainBody = '仅纯文本正文<b>不加粗</b>'

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')

    async function createContent(title: string, body: string, layout: string) {
      await page.getByRole('button', { name: '新增内容' }).click()
      const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
      await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
      await contentDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(body)
      await contentDrawer.locator('.fld').filter({ hasText: '版式 HTML' }).locator('textarea').fill(layout)
      const createResp = page.waitForResponse(
        (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
      )
      await contentDrawer.getByRole('button', { name: '保存' }).click()
      const created = (await (await createResp).json()) as { code: number }
      expect(created.code).toBe(0)
      const row = page.locator('tr', { hasText: title })
      await expect(row).toBeVisible({ timeout: 15_000 })
      await row.getByRole('button', { name: '提审' }).click()
      await expect(row).not.toContainText('DRAFT', { timeout: 15_000 })
    }

    await createContent(layoutTitle, hiddenBody, layoutHtml)
    await createContent(plainTitle, plainBody, '')

    await loginAdmin(page)

    async function openReview(title: string) {
      await page.goto('/ims/content/review')
      await page.locator('.tab', { hasText: '一级审核' }).click()
      await page.locator('input[placeholder="标题"]').fill(title)
      await page.getByRole('button', { name: '查询' }).click()
      const reviewRow = page.locator('tr', { hasText: title }).first()
      await expect(reviewRow).toBeVisible({ timeout: 15_000 })
      await reviewRow.getByRole('button', { name: '审核' }).click()
      const drawer = page.locator('.drawer.on').filter({ hasText: '审核' })
      await expect(drawer).toBeVisible()
      return drawer
    }

    const layoutDrawer = await openReview(layoutTitle)
    await expect(layoutDrawer.locator('[data-layout-mode="html"]')).toBeVisible()
    await expect(layoutDrawer.locator('[data-layout-viewer]')).toContainText('版式可见标记')
    await expect(layoutDrawer).not.toContainText(hiddenBody)
    const img = layoutDrawer.locator('[data-layout-viewer] img[alt="已插入图片"]')
    await expect(img).toBeVisible()
    await expect
      .poll(async () => img.evaluate((el: HTMLImageElement) => (el.complete ? el.naturalWidth : 0)))
      .toBeGreaterThan(0)
    const box = await img.boundingBox()
    expect(box?.width || 0).toBeGreaterThan(40)
    const viewerHtml = await layoutDrawer.locator('[data-layout-viewer]').innerHTML()
    expect(viewerHtml.toLowerCase()).not.toContain('<script')
    expect(viewerHtml.toLowerCase()).not.toContain('onclick')
    expect(viewerHtml).not.toContain('__imsXss')
    await expect(layoutDrawer.locator('input[type="file"]')).toHaveCount(0)
    await expect(layoutDrawer.locator('[contenteditable="true"]')).toHaveCount(0)
    await layoutDrawer.screenshot({ path: '/opt/cursor/artifacts/e2e-112-screenshots/review-drawer-layout.png' })
    await layoutDrawer.locator('.dr-x').click()
    await expect(layoutDrawer).not.toBeVisible()

    const plainDrawer = await openReview(plainTitle)
    await expect(plainDrawer.locator('[data-layout-mode="plain"]')).toBeVisible()
    await expect(plainDrawer.locator('[data-layout-viewer]')).toHaveCount(0)
    await expect(plainDrawer.locator('[data-layout-plain]')).toHaveText(plainBody)
    await expect(plainDrawer.locator('[data-layout-plain] img')).toHaveCount(0)
    await plainDrawer.screenshot({ path: '/opt/cursor/artifacts/e2e-112-screenshots/review-drawer-plain.png' })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
