import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-135-screenshots'

/**
 * #135 CONTENT ComfyUI 视频生成抽屉（纯 UI · 桩）
 * 创建任务 → 提交 Job → 轮询生成中 → 绑定预览 stub/comfyui/stable-demo.mp4
 */
test.describe('content ComfyUI video drawer closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('create job poll status and bind preview', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const title = `E2E 视频任务 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await createDrawer
      .locator('.fld')
      .filter({ hasText: 'matchScheme JSON' })
      .locator('textarea')
      .fill('[{"matchId":"1001","homeName":"主队","awayName":"客队","matchPlays":[]}]')
    const createResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    await createResp

    const row = page.locator('tr', { hasText: title }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('ai-video-task-btn')).toBeEnabled()
    await editDrawer.getByTestId('ai-video-task-btn').click()

    const videoDrawer = page.locator('.drawer.on').filter({ has: page.getByTestId('video-gen-drawer') })
    await expect(videoDrawer.getByTestId('video-gen-drawer')).toBeVisible()
    await expect(videoDrawer.getByText('无本机 GPU')).toBeVisible()

    const submitResp = page.waitForResponse(
      (r) => r.url().includes('/content/ai-job/submit') && r.request().method() === 'POST' && r.status() === 200,
    )
    await videoDrawer.getByTestId('video-submit-btn').click()
    const submitted = await submitResp
    const submitBody = (await submitted.json()) as { code: number; data?: { provider?: string; queueStatus?: string } }
    expect(submitBody.code).toBe(0)
    expect(submitBody.data?.provider).toBe('stub')
    expect(submitBody.data?.queueStatus).toBe('WAITING')

    await expect(videoDrawer.getByTestId('video-provider')).toContainText('桩')
    await expect(videoDrawer.getByTestId('video-poll-status')).toContainText('生成中', { timeout: 8_000 })
    await page.screenshot({ path: path.join(SHOTS, '01-video-generating.png'), fullPage: true })

    await expect(videoDrawer.getByTestId('video-preview')).toBeVisible({ timeout: 8_000 })
    await expect(videoDrawer.getByTestId('video-bind-line')).toContainText('已绑定到本条内容')
    await expect(videoDrawer.getByTestId('video-bind-line')).toContainText('stub/comfyui/stable-demo.mp4')
    await expect(videoDrawer.getByText('plain-token')).toHaveCount(0)
    await page.screenshot({ path: path.join(SHOTS, '02-video-bound-preview.png'), fullPage: true })

    await videoDrawer.getByRole('button', { name: '关闭' }).click()
    await expect(editDrawer.getByTestId('video-status')).toContainText('待终审', { timeout: 15_000 })
    await expect(editDrawer.getByTestId('video-file-key')).toHaveText('stub/comfyui/stable-demo.mp4')
    await page.screenshot({ path: path.join(SHOTS, '03-content-video-bound.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
