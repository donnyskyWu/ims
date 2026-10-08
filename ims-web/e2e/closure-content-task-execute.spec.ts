import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createDraftPlanViaUi,
  createSopViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  startPlanRowViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · 计划任务执行完成 · **纯 UI**）
 * Given: UI 创建 SOP/IP 组/计划并启动
 * When: `/ims/content/task` → 执行 → 填写工作说明 →「完成」
 * Then: 任务状态 DONE
 */
test.describe('content task execute closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('plan task execute complete with deliverables', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-task-exec-${Date.now()}`
    const nodeName = `脚本撰写-${label}`
    const planName = `E2E 执行任务 ${label}`

    await loginAdmin(page)

    const { sopId } = await createSopViaUi(page, { sopName: `E2E 执行 SOP ${label}`, nodeName })
    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })

    await page.goto('/ims/content/plan')
    await startPlanRowViaUi(page, planName)

    await page.goto('/ims/content/task')
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })

    const row = page.locator('tr', { hasText: nodeName }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })

    await row.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    await expect(page.locator('.pg-h .sub')).toContainText(nodeName)

    const note = `E2E 工作说明 ${label}`
    await page.getByPlaceholder('完成必填（ADR-079）').fill(note)
    await page.getByRole('button', { name: '完成' }).click()

    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const doneRow = page.locator('tr', { hasText: nodeName }).first()
    await expect(doneRow).toContainText('DONE', { timeout: 15_000 })

    expect(pageErrors).toEqual([])
  })
})
