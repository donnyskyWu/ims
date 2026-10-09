import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-148-screenshots'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * #148 成绩展示与考试待办（纯 UI）
 * 简答交卷后显示「客观 n · 待阅」，阅卷后显示总分；指派后工作台出现考试待办。
 */
test.describe('exam score display and workbench todo', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('assign creates exam todo and subjective score shows pending then graded', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const paperName = `E2E待阅 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/perf/exam')
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })
    await page.getByRole('button', { name: '试卷管理' }).click()
    await page.getByRole('button', { name: '创建试卷' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '创建试卷' })
    await modal.locator('input[placeholder="如 10 月合规抽测"]').fill(paperName)
    await modal.locator('label', { hasText: '固定卷' }).locator('input').check()
    await expect(modal.getByText('EQ-001')).toBeVisible({ timeout: 15_000 })
    await modal.locator('label.mat-opt', { hasText: 'EQ-001' }).locator('input').check()
    await modal.locator('label.mat-opt', { hasText: 'EQ-006' }).locator('input').check()
    await modal.getByLabel('总分').fill('30')
    await modal.getByLabel('及格分').fill('30')
    await expect(modal.getByRole('button', { name: '保存试卷' })).toBeEnabled()
    await modal.getByRole('button', { name: '保存试卷' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })

    const row = page.locator('tr', { hasText: paperName })
    await row.getByRole('button', { name: '发布' }).click()
    await page.getByRole('button', { name: '确认发布' }).click()
    await expect(row.getByText('已发布')).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '指派考生' }).click()
    const assign = page.locator('.modal-mask .card').filter({ hasText: '指派考生' })
    await assign.getByRole('button', { name: '确认指派' }).click()
    await expect(assign).toBeHidden({ timeout: 15_000 })
    await expect(page.getByTestId('exam-assign-notice')).toContainText('考生工作台已收到考试待办')
    await shot(page, '01-assign-notice')

    await page.goto('/ims/workbench/todos')
    await expect(page.locator('h1')).toHaveText('待办中心', { timeout: 15_000 })
    await page.getByTestId('todo-task-type').selectOption('exam')
    await page.getByRole('button', { name: '查询' }).click()
    const todoRow = page.locator('tr', { hasText: paperName })
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    await expect(todoRow.getByText('考试', { exact: true })).toBeVisible()
    await shot(page, '02-exam-todo')
    await todoRow.getByTestId('todo-exam-entry').click()
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })

    await page.getByRole('button', { name: '试卷管理' }).click()
    const paperRow = page.locator('tr', { hasText: paperName })
    await paperRow.getByRole('button', { name: '考生作答' }).click()
    const take = page.locator('.modal-mask .card').filter({ hasText: '在线作答' })
    await expect(take.locator('.quiz-q')).toHaveCount(2)
    await take.locator('label.opt').first().locator('input').check()
    await take.locator('textarea').fill('先测人群再放量')
    await take.getByRole('button', { name: '交卷' }).click()
    await page.getByRole('button', { name: '确认交卷' }).click()
    await expect(page.getByTestId('exam-pending-grade')).toContainText('客观 0 · 待阅', { timeout: 15_000 })
    await shot(page, '03-pending-objective')

    await page.getByRole('button', { name: '查看成绩' }).click()
    const scoreRow = page.locator('[data-testid="exam-score-row"]', { hasText: paperName })
    await expect(scoreRow.getByTestId('exam-score-total')).toHaveText('客观 0 · 待阅', { timeout: 15_000 })
    await shot(page, '04-score-pending')

    await page.getByTestId('exam-score-user').fill('没有这个人')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByText('暂无成绩')).toBeVisible({ timeout: 15_000 })
    await shot(page, '05-score-filter-empty')

    await page.getByTestId('exam-score-user').fill('管理员')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(scoreRow.getByTestId('exam-grade-open')).toBeVisible({ timeout: 15_000 })
    await scoreRow.getByTestId('exam-grade-open').click()
    const drawer = page.getByTestId('exam-grade-drawer')
    await expect(drawer.getByText('PER-E-R4')).toBeVisible()
    await drawer.getByLabel(/评分/).fill('10')
    await shot(page, '06-grade-drawer')
    await drawer.getByTestId('exam-grade-submit').click()
    await expect(drawer).toBeHidden({ timeout: 15_000 })
    await expect(scoreRow.getByTestId('exam-score-total')).toHaveText('10', { timeout: 15_000 })
    await expect(scoreRow.getByText('已判分')).toBeVisible()
    await shot(page, '07-score-graded')
    expect(pageErrors).toEqual([])
  })
})
