import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-79-screenshots'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * Checklist E2E-S10 切片（#79 · 纯 UI）
 * TRAIN 契约没有随机组卷、开考窗口和 MAKEUP_EXAM。
 * 本片覆盖手工组卷校验、交卷判分、不及格重答后最新成绩覆盖。
 */
test.describe('train quiz compose grade and retake', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('admin composes quiz, fails once, then retake overwrites score', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-quiz-${Date.now()}`
    const materialTitle = `E2E 问卷资料 ${label}`
    const taskName = `E2E 问卷任务 ${label}`
    const questionA = `E2E问卷甲 ${label}`
    const questionB = `E2E问卷乙 ${label}`

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

    await modal.locator('input[type="number"]').fill('3')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByText('及格分须在 1 到题目数之间')).toBeVisible()
    await shot(page, '01-compose-pass-score-blocked')

    await modal.locator('input[type="number"]').fill('2')
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
    )
    await modal.getByRole('button', { name: '保存' }).click()
    const created = (await (await createResp).json()) as {
      code: number
      data?: { id?: number; questionCount?: number; quiz?: Array<Record<string, unknown>> }
    }
    expect(created.code).toBe(0)
    expect(created.data?.questionCount).toBe(2)
    expect(created.data?.quiz?.[0]).not.toHaveProperty('answerIndex')
    const taskId = created.data?.id
    expect(taskId).toBeTruthy()
    await expect(page.locator('tr', { hasText: taskName })).toBeVisible({ timeout: 15_000 })

    await page.goto(`/ims/train/study/${taskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByText(questionA)).toBeVisible()
    await expect(page.getByText(questionB)).toBeVisible()
    await expect(page.getByText('及格 2 分')).toBeVisible()
    await expect(page.getByRole('button', { name: '提交问卷' })).toBeDisabled()
    await shot(page, '02-study-quiz-before-answer')

    await page.locator('.quiz-q').nth(0).locator('label.opt', { hasText: '错' }).locator('input').check()
    await page.locator('.quiz-q').nth(1).locator('label.opt', { hasText: '是' }).locator('input').check()
    await page.getByRole('button', { name: '提交问卷' }).click()
    const dialog = page.locator('.modal-mask .card').filter({ hasText: '确认交卷' })
    await expect(dialog.getByText('提交后将判分，未及格可重答')).toBeVisible()

    const failResp = page.waitForResponse(
      (r) => r.url().includes(`/train/task/${taskId}/confirm`) && r.request().method() === 'POST',
    )
    await dialog.getByRole('button', { name: '确认交卷' }).click()
    const failed = (await (await failResp).json()) as {
      code: number
      data?: { isPassed?: boolean; confirmScore?: number; confirmStatus?: string }
    }
    expect(failed.code).toBe(0)
    expect(failed.data?.isPassed).toBe(false)
    expect(failed.data?.confirmScore).toBe(0)
    expect(failed.data?.confirmStatus).toBe('NOT_CONFIRMED')
    await expect(page.getByTestId('train-quiz-score-latest')).toHaveText('得分 0，及格 2，未通过，可重答')
    await shot(page, '03-retake-not-passed')

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
    expect(passed.data?.confirmStatus).toBe('CONFIRMED')
    await expect(page.getByText('学习已完成 · CONFIRMED · 得分 2')).toBeVisible()
    await shot(page, '04-passed-score')

    await page.goto('/ims/train/task')
    const taskRow = page.locator('tr', { hasText: taskName })
    await expect(taskRow.getByText('自测问卷')).toBeVisible()
    await taskRow.getByRole('button', { name: '学习记录' }).click()
    const records = page.locator('.modal-mask .card').filter({ hasText: '学习记录' })
    await expect(records.getByText('CONFIRMED')).toBeVisible()
    await expect(records.locator('td').filter({ hasText: /^2$/ })).toBeVisible()
    await shot(page, '05-records-latest-score')

    expect(pageErrors).toEqual([])
  })
})
