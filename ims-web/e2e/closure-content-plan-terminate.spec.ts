import { test, expect } from '@playwright/test'
import {
  approvePlanTerminateViaUi,
  attachClosurePageHooks,
  createDraftPlanViaUi,
  createSopViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  requestPlanTerminateViaUi,
  startPlanRowViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · 计划终止 · **纯 UI** · #36）
 * Given: UI 创建 SOP + 计划并启动
 * When: 申请终止 → 批准终止
 * Then: 计划 TERMINATED · 关联任务 TERMINATED
 */
test.describe('content plan terminate closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('in-progress plan terminate approve then tasks TERMINATED', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-plan-term-${Date.now()}`
    const sopName = `E2E 终止 SOP ${label}`
    const nodeName = `节点-${label}`
    const planName = `E2E 终止计划 ${label}`

    await loginAdmin(page)

    const { sopId } = await createSopViaUi(page, { sopName, nodeName })
    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)

    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })
    await startPlanRowViaUi(page, planName)

    await page.goto('/ims/content/plan')
    await requestPlanTerminateViaUi(page, planName, 'E2E 计划终止')
    await approvePlanTerminateViaUi(page, planName)

    await page.goto('/ims/content/task')
    await page.locator('.tab', { hasText: '全部任务' }).click()
    const taskRow = page.locator('tr', { hasText: nodeName })
    await expect(taskRow).toBeVisible({ timeout: 15_000 })
    await expect(taskRow).toContainText('TERMINATED')

    expect(pageErrors).toEqual([])
  })
})
