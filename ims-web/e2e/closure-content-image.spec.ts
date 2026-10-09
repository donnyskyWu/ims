import fs from 'fs'
import os from 'os'
import path from 'path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-110-screenshots'

/** #110 · 内容编辑器 scene=content_image → layout_html，插入后预览（纯 UI） */
test.describe('content image editor closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('upload content_image into layout and preview after reopen', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const stamp = Date.now()
    const title = `E2E 版式图 ${stamp}`
    const pngPath = path.join(os.tmpdir(), `ims-content-image-${stamp}.png`)
    fs.writeFileSync(
      pngPath,
      Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
        'base64',
      ),
    )

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await expect(drawer).toBeVisible()
    await drawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/content/file/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('content-image-file').setInputFiles(pngPath)
    const uploadResult = await uploadResp
    const uploaded = (await uploadResult.json()) as {
      code: number
      data?: { fileKey?: string; fileUrl?: string; fileName?: string }
    }
    expect(uploaded.code).toBe(0)
    const fileKey = uploaded.data?.fileKey || ''
    expect(fileKey.startsWith('content_image/')).toBe(true)
    expect(uploaded.data?.fileUrl || '').toContain('/admin-api/ims/file/')
    expect(uploadResult.request().headers()['content-type'] || '').toContain('multipart/form-data')

    const preview = drawer.getByTestId('content-layout-preview')
    const previewImg = preview.locator('img')
    await expect(previewImg).toBeVisible({ timeout: 15_000 })
    await expect(previewImg).toHaveAttribute('alt', 'ims-content-image-' + stamp + '.png')
    await expect(drawer.getByTestId('content-layout-html')).toHaveValue(new RegExp(`data-file-key="${fileKey}"`))
    await page.screenshot({ path: `${shotDir}/01-image-inserted-preview.png`, fullPage: true })

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByRole('button', { name: '保存' }).click()
    const saved = (await (await saveResp).json()) as { code: number; data?: { layoutHtml?: string } }
    expect(saved.code).toBe(0)
    expect(saved.data?.layoutHtml || '').toContain(fileKey)
    await expect(drawer).toBeHidden({ timeout: 15_000 })

    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer).toBeVisible()
    await expect(editDrawer.getByTestId('content-layout-html')).toHaveValue(new RegExp(fileKey))
    await expect(editDrawer.getByTestId('content-layout-preview').locator('img')).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/02-reopen-layout-persisted.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
