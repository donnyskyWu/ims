import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createDraftPlanViaUi,
  createSopViaUi,
  fillMatchSchemeViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  requestPlanTerminateViaUi,
  startPlanRowViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts'

/**
 * #183 CONTENT 本地桩尾巴（纯 UI）
 * 文案抽屉未生成空态 → 桩预览；内容面板露出 ComfyUI 桩状态。
 * 计划结束日早于开始日；终止原因从抽屉写入列表。
 * 不重建 #135 视频轮询，也不重建 #152 的筛选与进度列。
 */
test.describe('content AI copy empty and ComfyUI stub tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty copy preview then stub preview, and comfyui stub status', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const marker = `E2E183-${Date.now()}`
    const title = `E2E 桩空态 ${marker}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await fillMatchSchemeViaUi(createDrawer, { matchId: '1001', homeName: '主队', awayName: '客队' })
    const createResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    await createResp

    const row = page.locator('tr', { hasText: title }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.getByTestId('row-ai-status')).toHaveText('未生成')
    await expect(row.getByTestId('row-video-status')).toHaveText('未生成')
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('comfyui-stub-status')).toContainText('桩')
    await expect(editDrawer.getByTestId('ai-copy-provider')).toContainText('桩')
    await expect(editDrawer.getByTestId('ai-copy-empty')).toContainText('尚未生成文案')
    await expect(editDrawer.getByTestId('ai-copy-status')).toContainText('未生成')
    await page.screenshot({ path: path.join(SHOTS, '183-comfyui-stub-status.png'), fullPage: true })

    await editDrawer.getByRole('button', { name: 'AI 文案' }).click()
    const aiDrawer = page.locator('.drawer.on').filter({ hasText: '选择模型并输入提示' })
    await expect(aiDrawer.getByTestId('ai-copy-empty')).toContainText('尚未生成')
    await expect(aiDrawer.getByTestId('ai-copy-stub-hint')).toContainText('无本机 GPU')
    await page.screenshot({ path: path.join(SHOTS, '183-ai-copy-empty.png'), fullPage: true })

    await aiDrawer.locator('textarea').fill(`${marker} 写一段赛后复盘`)
    const genResp = page.waitForResponse(
      (r) => r.url().includes('/content/ai-content/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await aiDrawer.getByRole('button', { name: '生成', exact: true }).click()
    const genBody = (await (await genResp).json()) as { code: number; data?: { mock?: boolean; markdown?: string } }
    expect(genBody.code).toBe(0)
    expect(genBody.data?.mock).toBe(true)
    await expect(aiDrawer.getByTestId('ai-copy-stub')).toContainText('桩预览')
    await expect(aiDrawer.locator('.ai-copy-preview')).toContainText(marker)
    await expect(aiDrawer.getByTestId('ai-copy-empty')).toHaveCount(0)
    await page.screenshot({ path: path.join(SHOTS, '183-ai-copy-stub.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('plan date edge, empty sop nodes hint stays hidden, and terminate reason', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-183-${Date.now()}`
    const sopName = `E2E183 SOP ${label}`
    const nodeName = `节点-${label}`
    const planName = `E2E183 计划 ${label}`
    const reason = `切片183终止 ${label}`

    await loginAdmin(page)
    await page.goto('/ims/content/plan')
    await expect(page.locator('h1')).toHaveText('计划管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增计划' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增计划（草稿）' })
    await createDrawer.locator('input[type="date"]').first().fill('2026-10-20')
    await createDrawer.locator('input[type="date"]').nth(1).fill('2026-10-01')
    await createDrawer.getByRole('button', { name: '保存草稿' }).click()
    await expect(createDrawer.getByTestId('plan-date-error')).toHaveText('结束日期不能早于开始日期')
    await page.screenshot({ path: path.join(SHOTS, '183-plan-date-error.png'), fullPage: true })
    await createDrawer.getByRole('button', { name: '取消' }).click()

    const { sopId } = await createSopViaUi(page, { sopName, nodeName })
    await page.locator('tr', { hasText: sopName }).getByRole('button', { name: '节点' }).click()
    const nodeDrawer = page.locator('.drawer.on').filter({ hasText: '节点 ·' })
    await expect(nodeDrawer).toContainText(nodeName)
    await expect(nodeDrawer.getByTestId('sop-nodes-empty')).toHaveCount(0)
    await nodeDrawer.locator('.dr-x').click()

    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })
    await startPlanRowViaUi(page, planName)
    await requestPlanTerminateViaUi(page, planName, reason)
    const planRow = page.locator('tr', { hasText: planName })
    await expect(planRow.getByTestId('plan-terminate-reason')).toHaveText(reason)
    await page.screenshot({ path: path.join(SHOTS, '183-plan-terminate-reason.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
