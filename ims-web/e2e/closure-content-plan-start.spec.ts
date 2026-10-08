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
 * Checklist **E2E-S7** 切片（acceptance · 计划启动 · **纯 UI**）
 * Given: UI 创建 SOP + IP 组 + 草稿计划
 * When: `/ims/content/plan` 行内「启动」
 * Then: 状态 IN_PROGRESS · 全部任务列表可见节点
 */
test.describe('content plan start closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('draft plan start then IN_PROGRESS and tasks listed', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-plan-start-${Date.now()}`
    const sopName = `E2E 计划 SOP ${label}`
    const nodeName = `节点-${label}`
    const planName = `E2E 计划 ${label}`

    await loginAdmin(page)

    const { sopId } = await createSopViaUi(page, { sopName, nodeName })
    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })

    await page.goto('/ims/content/plan')
    await startPlanRowViaUi(page, planName)

    await page.goto('/ims/content/task')
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    await page.locator('.tab', { hasText: '全部任务' }).click()
    const taskRow = page.locator('tr', { hasText: nodeName })
    await expect(taskRow).toBeVisible({ timeout: 15_000 })
    await expect(taskRow).toContainText(nodeName)

    expect(pageErrors).toEqual([])
  })
})
