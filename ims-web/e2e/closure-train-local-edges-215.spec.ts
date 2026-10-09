import fs from 'node:fs'
import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, loginAdmin } from './closure-helpers'

const SHOT = '/opt/cursor/artifacts'

/**
 * #215 TRAIN 本地尾项（纯 UI）
 * 标题/任务名长度、下架引用提示、即将到期标记、学时差距文案。
 * 不重复 #157 资料筛选、#164 重答、#177 部门统计、#186 预览空态、#202 任务筛选。
 */
test.describe('train local edges 215', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('title length, offline refs, due soon, and study gap', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const token = `e215${Date.now()}`
    const looseTitle = `无引用资料 ${token}`
    const linkedTitle = `被引用资料 ${token}`
    const taskName = `即将到期 ${token}`

    await loginAdmin(page)
    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })
    await expect(page.locator('.tree button.linkish').first()).toBeVisible({ timeout: 15_000 })

    await page.getByRole('button', { name: '上传资料' }).click()
    const upload = page.locator('.modal-mask .card').filter({ hasText: '上传资料' })
    await expect(upload).toBeVisible()
    await fieldAfter(upload, '标题').fill('资'.repeat(129))
    await upload.getByRole('button', { name: '发布' }).click()
    await expect(upload.getByTestId('train-material-form-error')).toHaveText('标题不超过 128 字')
    await page.screenshot({ path: `${SHOT}/train-215-title-too-long.png`, fullPage: true })
    await upload.getByRole('button', { name: '取消' }).click()

    const { materialId: looseId } = await createTrainMaterialViaUi(page, { title: looseTitle })
    await openOffline(page, looseTitle)
    await expect(page.getByTestId('train-offline-copy')).toHaveText('下架后学员不可见')
    await expect(page.getByTestId('train-offline-refs')).toHaveText(
      '当前没有进行中的学习任务引用，资料保留为已下架，不强删',
    )
    await page.screenshot({ path: `${SHOT}/train-215-offline-empty.png`, fullPage: true })
    await confirmOffline(page)
    await expect(page.locator('tr', { hasText: looseTitle }).getByTestId('train-material-status')).toContainText('已下架')
    expect(looseId).toBeGreaterThan(0)

    const { materialId } = await createTrainMaterialViaUi(page, { title: linkedTitle })
    await page.goto('/ims/train/task')
    await expect(page.locator('h1')).toHaveText('学习任务管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '下达学习任务' }).click()
    const taskForm = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
    await fieldAfter(taskForm, '任务名称').fill('任'.repeat(129))
    await taskForm.locator('label.mat-opt').filter({ hasText: `#${materialId}` }).locator('input').check()
    await taskForm.locator('input[placeholder="如 1"]').fill('1')
    await taskForm.getByRole('button', { name: '保存' }).click()
    await expect(taskForm.getByTestId('train-task-form-error')).toHaveText('任务名称不超过 128 字')
    await page.screenshot({ path: `${SHOT}/train-215-task-name-too-long.png`, fullPage: true })
    await fieldAfter(taskForm, '任务名称').fill(taskName)
    await fieldAfter(taskForm, '截止时间').fill(deadlineInHours(6))
    const created = page.waitForResponse(
      (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
    )
    await taskForm.getByRole('button', { name: '保存' }).click()
    const createdBody = (await (await created).json()) as { code: number; data?: { id?: number } }
    expect(createdBody.code).toBe(0)
    const taskId = createdBody.data?.id
    expect(taskId).toBeTruthy()

    const taskRow = page.locator('tr', { hasText: taskName })
    await expect(taskRow.getByTestId('train-task-due-soon')).toHaveText('即将到期', { timeout: 15_000 })
    await page.screenshot({ path: `${SHOT}/train-215-due-soon.png`, fullPage: true })

    await page.goto(`/ims/train/study/${taskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByTestId('train-study-gap')).toHaveText('还差 1 份资料未学完，学完后才能完成确认')
    await expect(page.getByRole('button', { name: '完成确认' })).toBeDisabled()
    await page.screenshot({ path: `${SHOT}/train-215-study-gap.png`, fullPage: true })

    const progress = page.waitForResponse(
      (r) => r.url().includes(`/train/task/${taskId}/progress`) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '标记当前资料已学完' }).click()
    expect(((await (await progress).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('train-study-gap')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '完成确认' })).toBeEnabled()

    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })
    await openOffline(page, linkedTitle)
    await expect(page.getByTestId('train-offline-copy')).toHaveText('下架后学员不可见')
    await expect(page.getByTestId('train-offline-refs')).toHaveText(
      '被 1 个进行中学习任务引用，资料保留，仅改为已下架，不强删',
    )
    await page.screenshot({ path: `${SHOT}/train-215-offline-referenced.png`, fullPage: true })
    await confirmOffline(page)
    await expect(page.locator('tr', { hasText: linkedTitle }).getByTestId('train-material-status')).toContainText('已下架')
    await expect(page.locator('tr', { hasText: linkedTitle }).getByTestId('train-material-offline')).toHaveCount(0)

    expect(pageErrors).toEqual([])
  })
})

function fieldAfter(scope: Page | ReturnType<Page['locator']>, label: string) {
  return scope.locator('label.fld', { hasText: label }).locator('xpath=following-sibling::input[1]')
}

function deadlineInHours(hours: number) {
  const shifted = new Date(Date.now() + hours * 3600 * 1000 + 8 * 3600 * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${shifted.getUTCFullYear()}-${pad(shifted.getUTCMonth() + 1)}-${pad(shifted.getUTCDate())}T${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}:${pad(shifted.getUTCSeconds())}+08:00`
}

async function openOffline(page: Page, title: string) {
  const listed = page.waitForResponse(
    (r) => r.url().includes('/train/task/list') && r.url().includes('status=IN_PROGRESS') && r.status() === 200,
  )
  await page.locator('tr', { hasText: title }).getByTestId('train-material-offline').click()
  await listed
  await expect(page.getByTestId('train-offline-dialog')).toBeVisible()
}

async function confirmOffline(page: Page) {
  const removed = page.waitForResponse(
    (r) => r.url().includes('/train/material/') && r.request().method() === 'DELETE' && r.status() === 200,
  )
  await page.getByTestId('train-offline-confirm').click()
  const body = (await (await removed).json()) as { code: number; data: unknown }
  expect(body.code).toBe(0)
  expect(body.data).toBeNull()
  await expect(page.getByTestId('train-offline-dialog')).toHaveCount(0)
}
