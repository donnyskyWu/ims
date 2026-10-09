import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createWorkTaskSopViaUi,
  E2E_OPS_AUTHOR_ID,
  loginAdmin,
  loginAs,
  fillMatchSchemeViaUi,
  passContentReviewViaUi,
  prepareIpGroupWithAdminMember,
  registerWorkTaskRowViaUi,
} from './closure-helpers'

/**
 * Checklist **E2E-S7** 切片（acceptance · #35 · **纯 UI**）
 * Given: UI 创建公推 SOP(CONTENT_GENERATION) + IP 组/作者 + 工作任务确认
 * When: 我的任务执行 → 内容编辑 → 提审 → e2e_author 审核通过 → admin 完成
 * Then: CONTENT_GENERATION 任务 **DONE**
 */
test.describe('content work task CONTENT_GENERATION closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('work task register review approve task done', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-wt-cg-${Date.now()}`
    const nodeName = `写文案-${label}`
    const contentTitle = `E2E 公推文案 ${label}`
    const workDate = new Date().toISOString().slice(0, 10)
    const competitionId = `M-${label}`
    const competitionName = `周末赛-${label}`

    await loginAdmin(page)

    const { sopId } = await createWorkTaskSopViaUi(page, {
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
      sopId,
    })

    await page.goto('/ims/content/task')
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const taskRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(taskRow).toBeVisible({ timeout: 15_000 })

    await taskRow.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    await expect(page.locator('.pg-h .sub')).toContainText(nodeName, { timeout: 15_000 })

    await page.getByRole('button', { name: '进入内容创作' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '内容编辑' })
    await editDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(contentTitle)
    await fillMatchSchemeViaUi(editDrawer, { matchId: '1001', homeName: '主队', awayName: '客队' })
    const saveContentResp = page.waitForResponse(
      (r) => /\/content\/\d+$/.test(r.url()) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存内容' }).click()
    await saveContentResp

    const submitResp = page.waitForResponse(
      (r) => r.url().includes('/submit-review') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交审核' }).click()
    await submitResp

    await loginAs(page, 'e2e_author')
    await passContentReviewViaUi(page, { title: contentTitle, stageTab: '一级审核' })
    await passContentReviewViaUi(page, { title: contentTitle, stageTab: '二级审核' })

    await loginAdmin(page)

    await page.goto('/ims/content/task')
    const donePrepRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(donePrepRow).toBeVisible({ timeout: 15_000 })
    await donePrepRow.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    const completeBtn = page.locator('.acts').getByRole('button', { name: '完成' })
    await expect(completeBtn).toBeEnabled({ timeout: 15_000 })
    await completeBtn.click()

    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const doneRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(doneRow).toContainText('DONE', { timeout: 15_000 })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
