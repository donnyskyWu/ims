import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/train-164-quiz-retake'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * Checklist E2E-S10 切片（#164 · 纯 UI）
 * 未作答成绩空态、不及格成绩在重新进入后仍可见，学习记录可去重答。
 */
test.describe('train quiz score empty and retake entry', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty score, restored fail score, and retake entry overwrite the latest result', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-quiz-empty-${Date.now()}`
    const materialTitle = `E2E 空成绩资料 ${label}`
    const taskName = `E2E 空成绩任务 ${label}`
    const questionA = `E2E空成绩甲 ${label}`
    const questionB = `E2E空成绩乙 ${label}`

    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })

    await page.goto('/ims/train/task')
    await expect(page.locator('h1')).toHaveText('学习任务管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '下达学习任务' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
    await expect(modal).toBeVisible()
    await modal
      .locator('label.fld', { hasText: '任务名称' })
      .locator('xpath=following-sibling::input[1]')
      .fill(taskName)
    await modal.locator('label.mat-opt').filter({ hasText: `#${materialId}` }).locator('input[type="checkbox"]').check()
    await modal.locator('input[placeholder="如 1"]').fill('1')
    await modal.locator('select').selectOption('QUIZ')

    await modal.getByRole('button', { name: '添加题目' }).click()
    const blocks = modal.locator('.quiz-block')
    await expect(blocks).toHaveCount(2)
    await blocks.nth(0).locator('input[placeholder="请输入题目"]').fill(questionA)
    await blocks.nth(0).locator('input[placeholder="选项内容"]').nth(0).fill('对')
    await blocks.nth(0).locator('input[placeholder="选项内容"]').nth(1).fill('错')
    await blocks.nth(1).locator('input[placeholder="请输入题目"]').fill(questionB)
    await blocks.nth(1).locator('input[placeholder="选项内容"]').nth(0).fill('是')
    await blocks.nth(1).locator('input[placeholder="选项内容"]').nth(1).fill('否')
    await blocks.nth(1).locator('input[type="radio"]').nth(1).check()
    await modal.locator('input[type="number"]').fill('2')

    const createResp = page.waitForResponse(
      (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
    )
    await modal.getByRole('button', { name: '保存' }).click()
    const created = (await (await createResp).json()) as { code: number; data?: { id?: number } }
    expect(created.code).toBe(0)
    const taskId = created.data?.id
    expect(taskId).toBeTruthy()
    await expect(page.locator('tr', { hasText: taskName })).toBeVisible({ timeout: 15_000 })

    const taskRow = page.locator('tr', { hasText: taskName })
    await taskRow.getByRole('button', { name: '学习记录' }).click()
    const records = page.locator('.modal-mask .card').filter({ hasText: '学习记录' })
    await expect(records.getByTestId('train-record-score-empty')).toHaveText('暂无成绩')
    await expect(records.getByTestId('train-record-retake')).toHaveCount(0)
    await shot(page, '01-records-score-empty')
    await records.getByRole('button', { name: '关闭' }).click()

    await page.goto(`/ims/train/study/${taskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByTestId('train-quiz-score-empty')).toHaveText('暂无成绩')
    await expect(page.getByTestId('train-quiz-retake')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '提交问卷' })).toBeDisabled()
    await shot(page, '02-study-score-empty')

    await page.locator('.quiz-q').nth(0).locator('label.opt', { hasText: '错' }).locator('input').check()
    await page.locator('.quiz-q').nth(1).locator('label.opt', { hasText: '是' }).locator('input').check()
    await page.getByRole('button', { name: '提交问卷' }).click()
    const dialog = page.locator('.modal-mask .card').filter({ hasText: '确认交卷' })
    const failResp = page.waitForResponse(
      (r) => r.url().includes(`/train/task/${taskId}/confirm`) && r.request().method() === 'POST',
    )
    await dialog.getByRole('button', { name: '确认交卷' }).click()
    const failed = (await (await failResp).json()) as {
      code: number
      data?: { isPassed?: boolean; confirmScore?: number; confirmStatus?: string }
    }
    expect(failed.code).toBe(0)
    expect(failed.data?.confirmScore).toBe(0)
    expect(failed.data?.confirmStatus).toBe('NOT_CONFIRMED')
    await expect(page.getByTestId('train-quiz-score-latest')).toHaveText('得分 0，及格 2，未通过，可重答')
    await expect(page.getByTestId('train-quiz-score-empty')).toHaveCount(0)

    await page.reload()
    await expect(page.getByTestId('train-quiz-score-latest')).toHaveText('得分 0，及格 2，未通过，可重答', {
      timeout: 15_000,
    })
    await page.getByTestId('train-quiz-retake').click()
    await expect(page.getByRole('button', { name: '提交问卷' })).toBeDisabled()
    await expect(page.getByTestId('train-quiz-score-latest')).toHaveText('得分 0，及格 2，未通过，可重答')
    await shot(page, '03-retake-restored-score')

    await page.goto('/ims/train/task')
    await page.locator('tr', { hasText: taskName }).getByRole('button', { name: '学习记录' }).click()
    const failedRecords = page.locator('.modal-mask .card').filter({ hasText: '学习记录' })
    await expect(failedRecords.locator('td').filter({ hasText: /^0$/ })).toBeVisible()
    await expect(failedRecords.getByTestId('train-record-score-empty')).toHaveCount(0)
    await shot(page, '04-records-retake-entry')
    await failedRecords.getByTestId('train-record-retake').click()
    await expect(page).toHaveURL(new RegExp(`/ims/train/study/${taskId}`))
    await expect(page.getByTestId('train-quiz-score-latest')).toHaveText('得分 0，及格 2，未通过，可重答')

    await page.locator('.quiz-q').nth(0).locator('label.opt', { hasText: '对' }).locator('input').check()
    await page.locator('.quiz-q').nth(1).locator('label.opt', { hasText: '否' }).locator('input').check()
    await page.getByRole('button', { name: '提交问卷' }).click()
    const passDialog = page.locator('.modal-mask .card').filter({ hasText: '确认交卷' })
    const passResp = page.waitForResponse(
      (r) => r.url().includes(`/train/task/${taskId}/confirm`) && r.request().method() === 'POST',
    )
    await passDialog.getByRole('button', { name: '确认交卷' }).click()
    const passed = (await (await passResp).json()) as {
      code: number
      data?: { isPassed?: boolean; confirmScore?: number; confirmStatus?: string }
    }
    expect(passed.code).toBe(0)
    expect(passed.data?.isPassed).toBe(true)
    expect(passed.data?.confirmScore).toBe(2)
    await expect(page.getByText('学习已完成 · CONFIRMED · 得分 2')).toBeVisible()
    await expect(page.getByTestId('train-quiz-retake')).toHaveCount(0)
    await shot(page, '05-passed-score')

    await page.goto('/ims/train/task')
    await page.locator('tr', { hasText: taskName }).getByRole('button', { name: '学习记录' }).click()
    const passedRecords = page.locator('.modal-mask .card').filter({ hasText: '学习记录' })
    await expect(passedRecords.getByText('CONFIRMED')).toBeVisible()
    await expect(passedRecords.locator('td').filter({ hasText: /^2$/ })).toBeVisible()
    await expect(passedRecords.getByTestId('train-record-retake')).toHaveCount(0)
    await expect(passedRecords.getByTestId('train-record-score-empty')).toHaveCount(0)
    await shot(page, '06-records-latest-score')

    expect(pageErrors).toEqual([])
  })
})
