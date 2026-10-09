import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, createTrainTaskViaUi, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/train-233'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * #233 · TRAIN 本地尾巴：岗位提示、截止时间格式、空选项、下架后学习空态、非指派人提示。
 * 不重建 #177 部门统计、#186 资料预览/重复选项、#202 任务筛选、#215 标题长度与即将到期。
 */
test.describe('train local tails 233', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('material form shows the category position', async ({ page }) => {
    test.setTimeout(60_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })
    await page.getByRole('button', { name: '上传资料' }).click()
    const editor = page.locator('.modal-mask .card').filter({ hasText: '上传资料' })
    await expect(editor.getByTestId('train-material-position-hint')).toContainText(/关联岗位 R\d/)
    await expect(editor.getByTestId('train-material-position-hint')).toContainText('发布后该岗位学员可见')
    await shot(page, '01-position-hint')
    expect(pageErrors).toEqual([])
  })

  test('task form rejects a bad deadline, a bad assignee, and a blank quiz option', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-233f-${Date.now()}`
    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: `E2E 表单资料 ${label}` })

    await page.goto('/ims/train/task')
    await expect(page.locator('h1')).toHaveText('学习任务管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '下达学习任务' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
    await modal.locator('label.fld', { hasText: '任务名称' }).locator('xpath=following-sibling::input[1]').fill(`E2E 表单 ${label}`)
    await modal.locator('label.mat-opt').filter({ hasText: `#${materialId}` }).locator('input[type="checkbox"]').check()
    await modal.locator('input[placeholder="如 1"]').fill('1')
    await modal.locator('input[placeholder="2026-12-31T18:00:00+08:00"]').fill('昨天')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('train-task-form-error')).toHaveText('截止时间格式无效')
    await shot(page, '02-deadline-format')

    await modal.locator('input[placeholder="2026-12-31T18:00:00+08:00"]').fill('2026-12-31T18:00:00+08:00')
    await modal.locator('input[placeholder="如 1"]').fill('abc')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('train-task-form-error')).toHaveText('指派用户 ID 无效')
    await shot(page, '03-assignee-invalid')

    await modal.locator('input[placeholder="如 1"]').fill('1')
    await modal.locator('select').selectOption('QUIZ')
    await modal.locator('.quiz-block').first().locator('input[placeholder="请输入题目"]').fill(`空选项 ${label}`)
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('train-task-form-error')).toHaveText('选项内容不能为空')
    await shot(page, '04-quiz-blank-option')

    expect(pageErrors).toEqual([])
  })

  test('offline material leaves an empty study list, and a stranger cannot report progress', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-233s-${Date.now()}`
    const hiddenTitle = `E2E 下架资料 ${label}`
    const hiddenTask = `E2E 下架任务 ${label}`
    const strangerTitle = `E2E 旁听资料 ${label}`
    const strangerTask = `E2E 旁听任务 ${label}`

    await loginAdmin(page)
    const hidden = await createTrainMaterialViaUi(page, { title: hiddenTitle })
    const hiddenTaskId = (
      await createTrainTaskViaUi(page, {
        taskName: hiddenTask,
        materialIds: [hidden.materialId],
        assignUserIds: [1],
      })
    ).taskId

    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })
    const row = page.locator('tr', { hasText: hiddenTitle })
    await expect(row).toBeVisible()
    const offlineResp = page.waitForResponse(
      (r) => r.url().includes(`/train/material/${hidden.materialId}`) && r.request().method() === 'DELETE' && r.status() === 200,
    )
    await row.getByRole('button', { name: '下架' }).click()
    const offlineBody = (await (await offlineResp).json()) as { code: number }
    expect(offlineBody.code).toBe(0)

    await page.goto(`/ims/train/study/${hiddenTaskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    const missing = page.getByTestId('train-study-material-missing')
    await expect(missing).toContainText('关联资料已下架或未发布，暂不可学习')
    await expect(missing).toContainText('请联系培训负责人恢复资料后再学习')
    await expect(page.getByRole('button', { name: '标记当前资料已学完' })).toHaveCount(0)
    await shot(page, '05-study-material-offline')

    const stranger = await createTrainMaterialViaUi(page, { title: strangerTitle })
    const strangerTaskId = (
      await createTrainTaskViaUi(page, {
        taskName: strangerTask,
        materialIds: [stranger.materialId],
        assignUserIds: [99999],
      })
    ).taskId

    await page.goto(`/ims/train/study/${strangerTaskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByText(strangerTitle)).toBeVisible()
    await page.getByRole('button', { name: '标记当前资料已学完' }).click()
    await expect(page.getByTestId('train-study-action-error')).toHaveText('仅被指派人可学习本任务')
    await expect(page.getByTestId('train-study-back-workbench')).toBeVisible()
    await shot(page, '06-not-assignee')

    expect(pageErrors).toEqual([])
  })
})
