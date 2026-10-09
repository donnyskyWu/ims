import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-102-screenshots'

/**
 * Checklist E2E-S7 可映射闭环（#102 · 纯 UI · 桩，无本机 GPU）
 * E2E-S7-02 文案生成写入草稿并可见「成功」
 * E2E-S7-03 视频桩产物待终审 + 文件键 stub/comfyui/stable-demo.mp4
 * E2E-S7-04 终审打回可见，重新发起后回到待终审
 * E2E-S7-06 失败重试文案在打回态露出「重新发起」
 * 密钥只在系统参数页掩码，内容页不出现明文。
 */
test.describe('content AI copy and ComfyUI stub closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('draft ai copy video review retry and masked token', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const title = `E2E 桩文案 ${Date.now()}`

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
    await expect(editDrawer.getByTestId('gpu-hint')).toContainText('无本机 GPU')
    await expect(editDrawer.getByTestId('content-ai-panel')).toBeVisible()

    const copyResp = page.waitForResponse(
      (r) => r.url().includes('/content/script/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: 'AI 生成文案' }).click()
    await copyResp
    await expect(editDrawer.getByTestId('ai-copy-status')).toContainText('成功', { timeout: 15_000 })
    await expect(editDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea')).toHaveValue(/【桩】口播稿 v1/)
    await page.screenshot({ path: path.join(SHOTS, '01-ai-copy-success.png'), fullPage: true })

    const runResp = page.waitForResponse(
      (r) => /\/ai-production\/task\/[^/]+\/run$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST',
    )
    await editDrawer.getByRole('button', { name: '视频生成' }).click()
    await runResp
    await expect(editDrawer.getByTestId('video-status')).toContainText('待终审', { timeout: 15_000 })
    await expect(editDrawer.getByTestId('video-file-key')).toHaveText('stub/comfyui/stable-demo.mp4')
    await expect(editDrawer.getByText('plain-token')).toHaveCount(0)
    await page.screenshot({ path: path.join(SHOTS, '02-video-pending-no-gpu.png'), fullPage: true })

    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '终审打回' }).click()
    await rejectResp
    await expect(editDrawer.getByTestId('video-status')).toContainText('终审打回')
    await expect(editDrawer.getByRole('button', { name: '重新发起视频' })).toBeVisible()
    await page.screenshot({ path: path.join(SHOTS, '03-video-reject-retry.png'), fullPage: true })

    const retryResp = page.waitForResponse(
      (r) => /\/ai-production\/task\/[^/]+\/run$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST',
    )
    await editDrawer.getByRole('button', { name: '重新发起视频' }).click()
    await retryResp
    await expect(editDrawer.getByTestId('video-status')).toContainText('待终审', { timeout: 15_000 })

    await page.goto('/ims/system/param')
    await expect(page.locator('h1')).toHaveText('系统参数', { timeout: 15_000 })
    const tokenRow = page.locator('tr', { hasText: 'content.ai.tokenSecret' })
    await expect(tokenRow).toBeVisible()
    await tokenRow.getByRole('button', { name: '修改' }).click()
    const paramDrawer = page.locator('.drawer.on').filter({ hasText: '修改参数' })
    await paramDrawer.locator('input[type="password"]').fill('plain-token-should-not-leak')
    const saveParam = page.waitForResponse(
      (r) => r.url().includes('/system/param') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await paramDrawer.getByRole('button', { name: '保存' }).click()
    await saveParam
    await expect(tokenRow).toContainText('********')
    await expect(page.getByText('plain-token-should-not-leak')).toHaveCount(0)
    await page.screenshot({ path: path.join(SHOTS, '04-param-token-masked.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
