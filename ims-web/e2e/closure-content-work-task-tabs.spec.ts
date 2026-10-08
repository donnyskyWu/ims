import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createWorkTaskSopViaUi,
  E2E_OPS_AUTHOR_ID,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  registerWorkTaskRowViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · #37 · **纯 UI**）
 * Given: UI 公推 SOP + IP 组/作者 + 工作任务登记确认
 * When: 切换「任务执行情况」「任务管理」Tab 并查询
 * Then: 执行列表可见 SOP 节点行 · 矩阵 summary/表体可见赛事与营销计划
 */
test.describe('content work task execution and matrix tabs closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('register then execution and matrix tabs show data', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-wt-tabs-${Date.now()}`
    const nodeName = `写文案-${label}`
    const workDate = new Date().toISOString().slice(0, 10)
    const competitionId = `M-tabs-${label}`
    const competitionName = `周末赛-${label}`

    await loginAdmin(page)

    await createWorkTaskSopViaUi(page, {
      sopName: `E2E 公推 SOP ${label}`,
      nodeName,
      marketingPlan: 'LIVE_PUBLIC',
    })
    const { ipGroupId, groupName } = await prepareIpGroupWithAdminMember(page, label, true, E2E_OPS_AUTHOR_ID)

    await registerWorkTaskRowViaUi(page, {
      ipGroupId,
      workDate,
      authorId: E2E_OPS_AUTHOR_ID,
      competitionId,
      competitionName,
      groupNameHint: groupName,
    })

    await page.locator('.tab', { hasText: '任务执行情况' }).click()
    const execResp = page.waitForResponse(
      (r) => r.url().includes('/content/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await execResp

    const execTable = page.locator('.tbl-block').filter({ hasText: '共' }).filter({ hasText: '工作任务轨' })
    await expect(execTable.locator('tr', { hasText: nodeName })).toBeVisible({ timeout: 15_000 })
    await expect(execTable.locator('tr', { hasText: competitionName })).toBeVisible()

    await page.locator('.tab', { hasText: '任务管理' }).click()
    await expect(page.locator('.wt-matrix-summary')).toContainText('赛事行 1')
    await expect(page.locator('.wt-matrix-summary')).toContainText('直播公推 1')

    const matrixTable = page.locator('.wt-matrix-table')
    await expect(matrixTable.locator('td', { hasText: competitionName })).toBeVisible({ timeout: 15_000 })
    await expect(matrixTable.locator('td', { hasText: '直播公推' })).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
