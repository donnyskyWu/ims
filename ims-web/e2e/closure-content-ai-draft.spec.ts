import { test, expect, type Page } from '@playwright/test'
import {
  attachClosurePageHooks,
  createWorkTaskSopViaUi,
  E2E_OPS_AUTHOR_ID,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  registerWorkTaskRowViaUi,
} from './closure-helpers'

/**
 * 切片 #128 · 工作任务确认后自动文案草稿（acceptance · 纯 UI）
 * Given: 系统参数打开自动文案，桩模式先失败
 * When: UI 创建 SOP / 工作任务并确认 → 执行页见失败 → 改回 success → 重试
 * Then: 草稿正文可见选题 → AI 文案面板采纳并可人工修订 → 仍为草稿，未自动提审、未改版式
 */
test.describe('content work task AI draft closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('confirm generates draft, failure can retry, execute page can polish', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const shotDir = '/opt/cursor/artifacts/e2e-128-screenshots'
    const label = `e2e-ai-draft-${Date.now()}`
    const nodeName = `写文案-${label}`
    const competitionName = `选题赛-${label}`
    const workDate = new Date().toISOString().slice(0, 10)
    const marker = `E2E-DRAFT-${Date.now()}`

    await loginAdmin(page)
    try {
      await setSystemParam(page, 'content.ai.stubMode', 'fail')
      await setSystemParam(page, 'work.task.confirm.auto-ai-generate', 'true')

      await createWorkTaskSopViaUi(page, {
        sopName: `E2E 自动草稿 SOP ${label}`,
        nodeName,
        marketingPlan: 'LIVE_PUBLIC',
      })
      const { ipGroupId, groupName } = await prepareIpGroupWithAdminMember(page, label, true, E2E_OPS_AUTHOR_ID)
      await registerWorkTaskRowViaUi(page, {
        ipGroupId,
        workDate,
        authorId: E2E_OPS_AUTHOR_ID,
        competitionId: `M-${label}`,
        competitionName,
        groupNameHint: groupName,
      })

      await page.goto('/ims/content/task')
      await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
      const taskRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
      await expect(taskRow).toBeVisible({ timeout: 15_000 })
      await taskRow.getByRole('button', { name: '执行' }).click()
      await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
      await expect(page.locator('.ai-draft-status')).toContainText('失败', { timeout: 15_000 })
      await page.screenshot({ path: `${shotDir}/01-draft-failed.png`, fullPage: true })

      await setSystemParam(page, 'content.ai.stubMode', 'success')
      await page.goto('/ims/content/task')
      const retryRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
      await retryRow.getByRole('button', { name: '执行' }).click()
      await expect(page.locator('.ai-draft-status')).toContainText('失败')
      const retryResp = page.waitForResponse(
        (r) => r.url().includes('/retry-ai-generate') && r.request().method() === 'POST' && r.status() === 200,
      )
      await page.getByRole('button', { name: '重试' }).click()
      const retryBody = (await (await retryResp).json()) as { code: number; data?: { aiGenerateStatus?: string } }
      expect(retryBody.code).toBe(0)
      expect(retryBody.data?.aiGenerateStatus).toBe('GENERATED')
      await expect(page.locator('.ai-draft-status')).toContainText('已生成', { timeout: 15_000 })
      const draft = page.locator('.ai-draft-body')
      await expect(draft).toContainText(competitionName)
      await expect(draft).toContainText('不改版式')
      await page.screenshot({ path: `${shotDir}/02-draft-generated.png`, fullPage: true })

      await page.getByRole('button', { name: '进入内容创作' }).click()
      const editDrawer = page.locator('.drawer.on').filter({ hasText: '内容编辑' })
      const bodyField = editDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea')
      await expect(bodyField).toHaveValue(new RegExp(competitionName))
      await editDrawer.getByRole('button', { name: 'AI 文案' }).click()
      const aiDrawer = page.locator('.drawer.on').filter({ hasText: '选择模型并输入提示' })
      await expect(aiDrawer.locator('select')).toBeVisible()
      await aiDrawer.locator('textarea').fill(`${marker} 润色结尾`)
      const genResp = page.waitForResponse(
        (r) => r.url().includes('/content/ai-content/generate') && r.request().method() === 'POST' && r.status() === 200,
      )
      await aiDrawer.getByRole('button', { name: '生成', exact: true }).click()
      const genBody = (await (await genResp).json()) as { code: number; data?: { layoutApplied?: boolean } }
      expect(genBody.code).toBe(0)
      expect(genBody.data?.layoutApplied).toBe(false)
      await expect(aiDrawer.locator('.ai-copy-preview')).toContainText(marker)
      await page.screenshot({ path: `${shotDir}/03-ai-panel-preview.png`, fullPage: true })
      await aiDrawer.getByRole('button', { name: '采纳' }).click()
      await expect(aiDrawer).toBeHidden({ timeout: 10_000 })
      const adopted = await bodyField.inputValue()
      expect(adopted).toContain(marker)
      await bodyField.fill(`${adopted}\n人工修订`)

      const saveResp = page.waitForResponse(
        (r) => /\/content\/\d+$/.test(r.url()) && r.request().method() === 'PUT' && r.status() === 200,
      )
      await editDrawer.getByRole('button', { name: '保存内容' }).click()
      const saved = (await (await saveResp).json()) as {
        code: number
        data?: { contentStatus?: string; layoutHtml?: string; body?: string }
      }
      expect(saved.code).toBe(0)
      expect(saved.data?.contentStatus).toBe('DRAFT')
      expect(saved.data?.layoutHtml || '').not.toContain('<')
      expect(saved.data?.body || '').toContain('人工修订')
      await expect(page.locator('.ai-draft-body')).toContainText('人工修订')
      await expect(page.locator('.ai-draft-body')).toContainText(marker)
      await expect(page.getByRole('button', { name: '提交审核' })).toBeVisible()
      await page.screenshot({ path: `${shotDir}/04-draft-edited.png`, fullPage: true })
      expect(pageErrors, pageErrors.join('\n')).toEqual([])
    } finally {
      await loginAdmin(page)
      await setSystemParam(page, 'content.ai.stubMode', '')
      await setSystemParam(page, 'work.task.confirm.auto-ai-generate', 'false')
    }
  })
})

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function setSystemParam(page: Page, key: string, value: string) {
  await page.goto('/ims/system/param')
  await expect(page.locator('h1')).toHaveText('系统参数', { timeout: 15_000 })
  const row = page.locator('tbody tr').filter({
    has: page.locator('td.mono', { hasText: new RegExp(`^${escapeRegExp(key)}$`) }),
  })
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.getByRole('button', { name: '修改' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '修改参数' })
  await drawer.locator('.fld').filter({ hasText: '当前值' }).locator('input').fill(value)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/system/param') && r.request().method() === 'PUT' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存' }).click()
  const body = (await (await saveResp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden({ timeout: 10_000 })
}
