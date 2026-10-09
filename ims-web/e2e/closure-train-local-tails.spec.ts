import fs from 'node:fs'
import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, createTrainTaskViaUi, loginAdmin } from './closure-helpers'

const SHOT = '/opt/cursor/artifacts'

/**
 * #202 TRAIN 本地尾项（纯 UI）
 * 任务列表筛选空态、学习记录筛选空态、问卷边界文案、看板日期与逾期筛选空态、逾期补学横幅。
 * 不重复 #157 资料筛选，也不重做部门统计口径。
 */
test.describe('train local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('task and record filters, quiz edge copy, stat range and overdue empty', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOT, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const token = `tails${Date.now()}`
    const durationName = `学时任务 ${token}`
    const quizName = `问卷任务 ${token}`
    const questionA = `边界甲 ${token}`
    const questionB = `边界乙 ${token}`

    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: `尾项资料 ${token}` })
    await createTrainTaskViaUi(page, { taskName: durationName, materialIds: [materialId], assignUserIds: [1] })
    await composeQuiz(page, { quizName, materialId, questionA, questionB })

    await page.getByTestId('train-task-filter-name').fill(token)
    await queryTasks(page)
    await expect(page.locator('tr', { hasText: durationName })).toBeVisible()
    await expect(page.locator('tr', { hasText: quizName })).toBeVisible()
    await expect(page.getByTestId('train-task-filter-summary')).toContainText(`名称「${token}」`)

    await page.getByTestId('train-task-filter-confirm').selectOption('QUIZ')
    await queryTasks(page)
    await expect(page.locator('tr', { hasText: quizName })).toBeVisible()
    await expect(page.locator('tr', { hasText: durationName })).toHaveCount(0)
    await expect(page.getByTestId('train-task-filter-summary')).toContainText('自测问卷')

    await page.getByTestId('train-task-filter-name').fill(`不存在${token}`)
    await queryTasks(page)
    await expect(page.getByTestId('train-task-empty')).toContainText('没有符合筛选的任务')
    await expect(page.getByTestId('train-task-total')).toHaveText('共 0 条')
    await page.screenshot({ path: `${SHOT}/train-task-filter-empty.png`, fullPage: true })

    await queryTasks(page, () => page.getByTestId('train-task-filter-clear-empty').click())
    await expect(page.getByTestId('train-task-filter-summary')).toHaveCount(0)
    await expect(page.locator('tr', { hasText: durationName })).toBeVisible()

    await page.locator('tr', { hasText: durationName }).getByRole('button', { name: '学习记录' }).click()
    const records = page.locator('.modal-mask .card').filter({ hasText: '学习记录' })
    await expect(records.getByText('NOT_CONFIRMED')).toBeVisible()
    await records.getByTestId('train-record-filter-status').selectOption('CONFIRMED')
    const emptyRecords = page.waitForResponse(
      (r) => r.url().includes('/train/task/records') && r.url().includes('confirmStatus=CONFIRMED') && r.status() === 200,
    )
    await records.getByTestId('train-record-query').click()
    await emptyRecords
    await expect(records.getByTestId('train-record-empty')).toContainText('没有符合筛选的学习记录')
    await page.screenshot({ path: `${SHOT}/train-record-filter-empty.png`, fullPage: true })
    await records.getByTestId('train-record-clear').click()
    await expect(records.getByText('NOT_CONFIRMED')).toBeVisible()
    await records.getByRole('button', { name: '关闭' }).click()

    await page.goto(`/ims/train/study/${await taskIdOf(page, quizName)}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByTestId('train-study-quiz-all-correct')).toHaveText('须全部答对才能通过')
    await expect(page.getByTestId('train-quiz-unanswered')).toContainText('还有 2 题未作答')
    await page.locator('.quiz-q').nth(0).locator('label.opt').nth(1).locator('input').check()
    await expect(page.getByTestId('train-quiz-unanswered')).toContainText('还有 1 题未作答')
    await page.locator('.quiz-q').nth(1).locator('label.opt').nth(0).locator('input').check()
    await expect(page.getByTestId('train-quiz-unanswered')).toHaveCount(0)
    await page.getByRole('button', { name: '提交问卷' }).click()
    const dialog = page.locator('.modal-mask .card').filter({ hasText: '确认交卷' })
    await dialog.getByRole('button', { name: '确认交卷' }).click()
    await expect(page.getByTestId('train-quiz-grade')).toContainText('未通过，可重答')
    await expect(page.getByText('请修改答案后再次交卷，成绩保留最新一次。')).toBeVisible()
    await page.screenshot({ path: `${SHOT}/train-quiz-edge-copy.png`, fullPage: true })

    await page.goto('/ims/train/stat')
    await expect(page.locator('h1')).toHaveText('培训统计看板', { timeout: 15_000 })
    await page.getByTestId('train-stat-range').fill('2099-12-31,2099-01-01')
    await page.getByRole('button', { name: '刷新' }).click()
    await expect(page.getByTestId('train-stat-range-error')).toHaveText('日期范围起大于止')
    await page.screenshot({ path: `${SHOT}/train-stat-range-error.png`, fullPage: true })

    await page.getByRole('button', { name: '近30天' }).click()
    await expect(page.getByTestId('train-stat-range-error')).toHaveCount(0)
    await page.getByTestId('train-stat-tab-overdue').click()
    await page.getByTestId('train-stat-overdue-dept').fill('999999')
    const overdueEmpty = page.waitForResponse(
      (r) => r.url().includes('/train/stat/overdue') && r.url().includes('deptId=999999') && r.status() === 200,
    )
    await page.getByRole('button', { name: '筛选' }).click()
    await overdueEmpty
    await expect(page.getByTestId('train-stat-overdue-empty')).toContainText('没有符合筛选的逾期记录')
    await page.getByTestId('train-stat-export').click()
    await expect(page.getByTestId('train-stat-export-msg')).toHaveText('没有可导出的逾期记录')
    await page.screenshot({ path: `${SHOT}/train-overdue-filter-empty.png`, fullPage: true })

    await page.goto('/ims/train/task')
    await page.getByTestId('train-task-filter-name').fill('E2E-TRAIN-OD-76')
    await queryTasks(page)
    const overdueRow = page.locator('tr', { hasText: 'E2E-TRAIN-OD-76' })
    await expect(overdueRow).toBeVisible({ timeout: 15_000 })
    await overdueRow.getByRole('button', { name: '去学习' }).click()
    await expect(page.getByTestId('train-study-overdue')).toContainText('本任务已逾期')
    await expect(page.getByTestId('train-study-overdue')).toContainText('补学仍计入完成率统计')
    await page.screenshot({ path: `${SHOT}/train-study-overdue.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})

async function queryTasks(page: Page, action?: () => Promise<void>) {
  const wait = page.waitForResponse(
    (r) => r.url().includes('/train/task/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  if (action) await action()
  else await page.getByRole('button', { name: '查询' }).click()
  await wait
}

async function taskIdOf(page: Page, taskName: string) {
  await page.goto('/ims/train/task')
  await page.getByTestId('train-task-filter-name').fill(taskName)
  const wait = page.waitForResponse(
    (r) => r.url().includes('/train/task/list') && r.url().includes('taskName=') && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  const body = (await (await wait).json()) as { data?: { list?: Array<{ id?: number; taskName?: string }> } }
  const hit = body.data?.list?.find((row) => row.taskName === taskName)
  expect(hit?.id).toBeTruthy()
  return hit!.id!
}

async function composeQuiz(
  page: Page,
  opts: { quizName: string; materialId: number; questionA: string; questionB: string },
) {
  await page.getByRole('button', { name: '下达学习任务' }).click()
  const modal = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
  await expect(modal).toBeVisible()
  await modal.locator('label.fld', { hasText: '任务名称' }).locator('xpath=following-sibling::input[1]').fill(opts.quizName)
  await modal.locator('label.mat-opt').filter({ hasText: `#${opts.materialId}` }).locator('input[type="checkbox"]').check()
  await modal.locator('input[placeholder="如 1"]').fill('1')
  await modal.locator('select').selectOption('QUIZ')
  const first = modal.locator('.quiz-block').nth(0)
  await first.locator('input[placeholder="请输入题目"]').fill(opts.questionA)
  await first.locator('input[placeholder="选项内容"]').nth(0).fill('相同')
  await first.locator('input[placeholder="选项内容"]').nth(1).fill('相同')
  await modal.getByRole('button', { name: '保存' }).click()
  await expect(modal.getByTestId('train-task-form-error')).toHaveText('选项内容不能重复')
  await page.screenshot({ path: `${SHOT}/train-quiz-duplicate-option.png`, fullPage: true })

  await first.locator('input[placeholder="选项内容"]').nth(1).fill('不同')
  await modal.getByRole('button', { name: '添加题目' }).click()
  const second = modal.locator('.quiz-block').nth(1)
  await second.locator('input[placeholder="请输入题目"]').fill(opts.questionA)
  await second.locator('input[placeholder="选项内容"]').nth(0).fill('是')
  await second.locator('input[placeholder="选项内容"]').nth(1).fill('否')
  await second.locator('input[type="radio"]').nth(1).check()
  await modal.getByRole('button', { name: '保存' }).click()
  await expect(modal.getByTestId('train-task-form-error')).toHaveText('题目不能重复')

  await second.locator('input[placeholder="请输入题目"]').fill(opts.questionB)
  await modal.locator('input[type="number"]').fill('2')
  await expect(modal.getByTestId('train-quiz-all-correct')).toHaveText('须全部答对才能通过')
  const createResp = page.waitForResponse(
    (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
  )
  await modal.getByRole('button', { name: '保存' }).click()
  const created = (await (await createResp).json()) as { code: number }
  expect(created.code).toBe(0)
  await expect(page.locator('tr', { hasText: opts.quizName })).toBeVisible({ timeout: 15_000 })
}
