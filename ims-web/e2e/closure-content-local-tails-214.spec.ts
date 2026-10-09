import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, fillMatchSchemeViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/content-214'

/**
 * #214 · 发布列表筛选余量、模板名称空态、正文空时不排版、视频桩成片要求空态。
 * 纯 UI。不重建文案/ComfyUI 桩客户端。
 */
test.describe('content local tails 214', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('publish filters, layout name, empty body, and video requirement', async ({ page }) => {
    test.setTimeout(180_000)
    mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-214-${Date.now()}`
    const title = `E2E 内容尾巴 ${label}`

    await loginAdmin(page)
    await page.goto('/ims/content/publish')
    await expect(page.locator('h1')).toHaveText('发布管理', { timeout: 15_000 })
    await expect(page.getByTestId('publish-supervise')).toContainText('督办：待发布')

    await page.getByTestId('publish-filter-no').fill(`miss-${label}`)
    await page.getByTestId('publish-filter-platform').selectOption('KUAISHOU')
    const missResp = page.waitForResponse(
      (r) => r.url().includes('/content/publish/list') && r.url().includes('platform=KUAISHOU') && r.status() === 200,
    )
    await page.getByTestId('publish-filters').getByRole('button', { name: '查询' }).click()
    await missResp
    await expect(page.getByTestId('publish-list-empty')).toContainText('没有符合筛选的发布单')
    await page.screenshot({ path: `${SHOTS}/01-publish-filter-empty.png`, fullPage: true })

    await page.getByTestId('publish-filter-from').fill('2026-12-20')
    await page.getByTestId('publish-filter-to').fill('2026-12-01')
    await page.getByTestId('publish-filters').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('publish-list-empty')).toContainText('计划结束日不能早于开始日')
    await page.screenshot({ path: `${SHOTS}/02-publish-date-order.png`, fullPage: true })

    await page.getByTestId('publish-filter-reset').click()
    await expect(page.getByTestId('publish-filter-no')).toHaveValue('')
    const receiptBtn = page.getByRole('button', { name: '回填' }).first()
    if (await receiptBtn.count()) {
      await receiptBtn.click()
      const receiptDrawer = page.locator('.drawer.on').filter({ hasText: '回填发布链接' })
      await receiptDrawer.getByTestId('publish-receipt-url').fill('ftp://not-http')
      await receiptDrawer.getByRole('button', { name: '保存' }).click()
      await expect(receiptDrawer.getByTestId('publish-receipt-error')).toHaveText('发布链接需以 http:// 或 https:// 开头')
      await page.screenshot({ path: `${SHOTS}/03-publish-receipt-url.png`, fullPage: true })
      await receiptDrawer.getByRole('button', { name: '取消' }).click()
    }

    await page.goto('/ims/content/layout')
    await expect(page.locator('h1')).toHaveText('公推模板库', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建模板' }).click()
    const createModal = page.locator('.modal-mask').filter({ hasText: '新建公推模板' })
    await createModal.getByRole('button', { name: '保存' }).click()
    await expect(createModal.getByTestId('layout-name-error')).toHaveText('请填写模板名称')
    await page.screenshot({ path: `${SHOTS}/04-layout-name-empty.png`, fullPage: true })
    await createModal.getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await fillMatchSchemeViaUi(createDrawer, { matchId: '2141', homeName: '主队', awayName: '客队' })
    const createResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const created = (await (await createResp).json()) as { code: number }
    expect(created.code).toBe(0)

    const row = page.locator('tr', { hasText: title }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('content-layout-need-body')).toHaveText('正文为空时不能套用模板或预览排版。')
    await expect(editDrawer.getByTestId('content-layout-preview-btn')).toBeDisabled()
    await page.screenshot({ path: `${SHOTS}/05-layout-need-body.png`, fullPage: true })

    await expect(editDrawer.getByTestId('ai-video-task-btn')).toBeEnabled()
    await editDrawer.getByTestId('ai-video-task-btn').click()
    const videoDrawer = page.locator('.drawer.on').filter({ has: page.getByTestId('video-gen-drawer') })
    await videoDrawer.getByTestId('video-requirement').fill('')
    await expect(videoDrawer.getByTestId('video-requirement-empty')).toContainText('成片要求为空时不能提交')
    await expect(videoDrawer.getByTestId('video-preview-empty')).toContainText('尚未绑定成片')
    await expect(videoDrawer.getByTestId('video-submit-btn')).toBeDisabled()
    await page.screenshot({ path: `${SHOTS}/06-video-requirement-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
