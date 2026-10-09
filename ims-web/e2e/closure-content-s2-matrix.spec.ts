import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createWorkTaskSopViaUi,
  E2E_OPS_AUTHOR_ID,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  registerWorkTaskRowViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-103-screenshots'

/**
 * Checklist 切片 #103 · CONTENT S2（acceptance · 纯 UI）
 * Given: 本用例单独的启用公推 SOP + IP 组/作者
 * When: 登记作者×赛事 → 矩阵改红黑 → 确认出任务 → 撤回
 * Then: 矩阵可见赛事与直播公推与红；撤回后登记行回到 DRAFT
 */
test.describe('content S2 author match matrix closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('matrix edits win prediction then confirm and withdraw', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-s2-${Date.now()}`
    const nodeName = `矩阵文案-${label}`
    const sopName = `E2E 公推 SOP ${label}`
    const workDate = new Date().toISOString().slice(0, 10)
    const competitionId = `M-s2-${label}`
    const competitionName = `矩阵赛-${label}`

    await loginAdmin(page)
    const { sopId } = await createWorkTaskSopViaUi(page, {
      sopName,
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
      confirm: false,
    })
    await page.screenshot({ path: `${SHOTS}/01-register-saved.png` })

    const sheetReload = page.waitForResponse(
      (r) => r.url().includes('/work-task/sheet') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.tab', { hasText: '任务管理' }).click()
    await sheetReload

    const matrix = page.locator('.wt-matrix-table')
    await expect(matrix.locator('td', { hasText: competitionName })).toBeVisible({ timeout: 15_000 })
    await page.locator('[data-testid="wt-matrix-win"]').selectOption('RED')
    await page.screenshot({ path: `${SHOTS}/02-matrix-editable.png` })

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/work-task/sheet') && r.request().method() === 'POST' && r.status() === 200,
    )
    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/work-task/') && r.url().includes('/confirm') && r.request().method() === 'POST',
    )
    await page.getByTestId('wt-matrix-confirm').click()
    const saveBody = (await (await saveResp).json()) as { code: number }
    expect(saveBody.code).toBe(0)
    const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { generatedTaskCount?: number } }
    expect(confirmBody.code).toBe(0)
    expect((confirmBody.data?.generatedTaskCount ?? 0) >= 1).toBeTruthy()

    const summary = page.locator('.wt-matrix-summary')
    await expect(summary).toContainText('赛事行 1')
    await expect(summary).toContainText('直播公推 1')
    await expect(summary).toContainText('红 1')
    await expect(matrix.locator('td', { hasText: '直播公推' })).toBeVisible()
    await expect(matrix.locator('td', { hasText: '红' })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/03-matrix-confirmed.png` })

    await page.locator('.tab', { hasText: '任务执行情况' }).click()
    const execResp = page.waitForResponse(
      (r) => r.url().includes('/content/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await execResp
    const execTable = page.locator('.tbl-block').filter({ hasText: '工作任务轨' })
    await expect(execTable.locator('tr', { hasText: nodeName })).toBeVisible({ timeout: 15_000 })
    await expect(execTable.locator('tr', { hasText: competitionName })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/04-execution-node.png` })

    await page.locator('.tab', { hasText: '任务管理' }).click()
    const withdrawResp = page.waitForResponse(
      (r) => r.url().includes('/work-task/') && r.url().includes('/withdraw') && r.request().method() === 'POST',
    )
    await page.getByTestId('wt-matrix-withdraw').click()
    const withdrawBody = (await (await withdrawResp).json()) as { code: number }
    expect(withdrawBody.code).toBe(0)

    await page.locator('.tab', { hasText: '任务登记' }).click()
    const registerTable = page.locator('.tbl-block').first()
    await expect(registerTable.locator('td', { hasText: 'DRAFT' }).first()).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${SHOTS}/05-withdrawn-draft.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
