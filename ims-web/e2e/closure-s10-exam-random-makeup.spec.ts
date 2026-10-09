import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-98-screenshots'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * Checklist E2E-S10-03 / E2E-S10-06（#98 · 纯 UI）
 * 1159/1160 与 MAKEUP_EXAM 在 PERF 考试契约。TRAIN 问卷契约没有随机组卷、开考窗口和补考状态。
 * 开考窗口 1161 由指派窗口 + start 拦截，本文件不单测窗口外。
 */
test.describe('exam random paper and makeup', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('random compose blocks 1160 and 1159 then saves', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const paperName = `E2E随机卷 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/perf/exam')
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })
    await page.getByRole('button', { name: '创建试卷' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '创建试卷' })
    await expect(modal).toBeVisible()
    await modal.locator('input[placeholder="如 10 月合规抽测"]').fill(paperName)
    await modal.locator('label', { hasText: '随机组卷' }).locator('input').check()
    await modal.getByLabel('抽题数').fill('5')
    await modal.getByLabel('总分').fill('50')

    await expect(modal.getByText('题库存量仅 1 题')).toBeVisible({ timeout: 15_000 })
    await expect(modal.getByRole('button', { name: '保存试卷' })).toBeDisabled()
    await shot(page, '01-random-1160-stock')

    await modal.getByLabel('抽题数').fill('1')
    await modal.getByLabel('总分').fill('99')
    await expect(modal.getByText('不一致（1159）')).toBeVisible()
    await expect(modal.getByRole('button', { name: '保存试卷' })).toBeDisabled()
    await shot(page, '02-random-1159-total')

    await modal.getByLabel('总分').fill('10')
    await modal.getByLabel('及格分').fill('6')
    await expect(modal.getByRole('button', { name: '保存试卷' })).toBeEnabled()
    await modal.getByRole('button', { name: '保存试卷' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })
    const row = page.locator('tr', { hasText: paperName })
    await expect(row).toBeVisible()
    await expect(row.getByText('随机组卷')).toBeVisible()
    await shot(page, '03-random-paper-saved')
    expect(pageErrors).toEqual([])
  })

  test('failed exam can be made up once and score is overwritten', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const paperName = `E2E补考卷 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/perf/exam')
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })
    await page.getByRole('button', { name: '创建试卷' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '创建试卷' })
    await modal.locator('input[placeholder="如 10 月合规抽测"]').fill(paperName)
    await modal.locator('label', { hasText: '固定卷' }).locator('input').check()
    await expect(modal.getByText('EQ-001')).toBeVisible({ timeout: 15_000 })
    await modal.locator('label.mat-opt', { hasText: 'EQ-001' }).locator('input').check()
    await modal.locator('label.mat-opt', { hasText: 'EQ-009' }).locator('input').check()
    await modal.getByLabel('总分').fill('20')
    await modal.getByLabel('及格分').fill('20')
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
    await expect(row.getByRole('button', { name: '考生作答' })).toBeVisible()

    await row.getByRole('button', { name: '考生作答' }).click()
    const take = page.locator('.modal-mask .card').filter({ hasText: '在线作答' })
    await expect(take.locator('.quiz-q')).toHaveCount(2)
    await take.locator('.quiz-q').nth(0).locator('label.opt', { hasText: '没有硬性红线' }).locator('input').check()
    await take.locator('.quiz-q').nth(1).locator('label.opt', { hasText: '20:00' }).locator('input').check()
    await take.getByRole('button', { name: '交卷' }).click()
    await page.getByRole('button', { name: '确认交卷' }).click()
    await expect(page.getByText('得分 0，及格 20，未通过')).toBeVisible({ timeout: 15_000 })
    await shot(page, '04-makeup-not-passed')

    await page.getByRole('button', { name: '申请补考' }).click()
    await expect(page.getByText('补考仅一次，新成绩将覆盖原成绩（PER-E-R3）')).toBeVisible()
    await shot(page, '05-makeup-confirm')
    await page.getByRole('button', { name: '确认补考' }).click()
    const retake = page.locator('.modal-mask .card').filter({ hasText: '在线作答' })
    await expect(retake.locator('.quiz-q')).toHaveCount(2)
    await retake.locator('.quiz-q').nth(0).locator('label.opt', { hasText: '在线人数不低于峰值 30%' }).locator('input').check()
    await retake.locator('.quiz-q').nth(1).locator('label.opt', { hasText: '22:00' }).locator('input').check()
    await retake.getByRole('button', { name: '交卷' }).click()
    await page.getByRole('button', { name: '确认交卷' }).click()
    await expect(page.getByText('补考成绩 20，已覆盖原成绩 · MAKEUP_EXAM')).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: '查看成绩' }).click()
    const scoreRow = page.locator('tr', { hasText: paperName })
    await expect(scoreRow.locator('.tag', { hasText: '补考' })).toBeVisible({ timeout: 15_000 })
    await expect(scoreRow.getByText('20', { exact: true })).toBeVisible()
    await shot(page, '06-makeup-score-board')
    expect(pageErrors).toEqual([])
  })
})