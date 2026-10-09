import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * #225 · PERF 本地空态与 calc/exam/mine 边角文案（纯 UI）
 * 不覆盖 #187 排名看板、#208 计算筛选。
 */
const SHOTS = '/opt/cursor/artifacts/perf-225'
const STAFF = '绩效员工甲'

function pad(n: number) {
  return String(n).padStart(2, '0')
}

function localInput(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function freshPeriod() {
  const slot = Math.floor(Date.now() / 1000) % 36
  const year = 2032 + Math.floor(slot / 12)
  const month = (slot % 12) + 1
  return `${year}-${pad(month)}`
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true })
  await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true })
}

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

test.describe('perf local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('calc empty, observation 1156, reject remark, mine empty period', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/perf/calc')
    await expect(page.locator('h1')).toHaveText('绩效计算与核准', { timeout: 15_000 })
    await page.getByTestId('perf-period').fill('2031-08')
    await page.getByTestId('perf-period').press('Tab')
    await expect(page.getByTestId('perf-calc-empty')).toContainText('本周期还没有计算结果', { timeout: 15_000 })
    await expect(page.getByTestId('perf-calc-empty')).toContainText('第 23 周前无基线数据')
    await shot(page, '01-calc-empty')

    await page.getByTestId('perf-run-open').click()
    await page.getByTestId('perf-run-period').fill('2026-05')
    await page.getByTestId('perf-run-confirm').click()
    await expect(page.getByTestId('perf-run-error')).toContainText('观察期不足：第 23 周前无基线数据', {
      timeout: 15_000,
    })
    await expect(page.getByTestId('perf-run-error')).toContainText('1156')
    await shot(page, '02-calc-1156')
    await page.locator('.drawer.on .dr-x').click()

    await page.getByTestId('perf-approve-open').click()
    await expect(page.getByTestId('perf-approve-manual-empty')).toContainText('本周期没有待人工人员')
    await expect(page.getByTestId('perf-reject-hint')).toContainText('驳回须填写审批意见')
    await expect(page.getByTestId('perf-approve-reject')).toBeDisabled()
    await shot(page, '03-reject-hint')
    await page.getByTestId('perf-approve-remark').fill('空周期驳回')
    await expect(page.getByTestId('perf-approve-reject')).toBeEnabled()
    await page.getByTestId('perf-approve-reject').click()
    await expect(page.getByTestId('perf-approve-error')).toContainText('没有可核准', { timeout: 15_000 })
    await page.locator('.drawer.on .dr-x').click()

    await logout(page)
    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await expect(page.locator('h1')).toHaveText('我的绩效', { timeout: 15_000 })
    await page.getByTestId('perf-mine-period').fill('2031-08')
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-empty')).toContainText('本期无绩效记录', { timeout: 15_000 })
    await expect(page.getByTestId('perf-mine-empty')).toContainText('PER-C-R2')
    await shot(page, '04-mine-empty')
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('exam filter empty, inverted window, and unanswered confirm', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const paperName = `E2E边角卷 ${Date.now()}`
    await loginAdmin(page)
    await page.goto('/ims/perf/exam')
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })
    await page.getByTestId('exam-question-keyword').fill('没有这道题zzz')
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-bank-empty')).toHaveText('没有符合筛选条件的题目', { timeout: 15_000 })
    await shot(page, '05-exam-bank-empty')

    await page.getByRole('button', { name: '试卷管理' }).click()
    await page.getByTestId('exam-paper-name').fill('没有这张卷zzz')
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-paper-empty')).toHaveText('没有符合筛选条件的试卷', { timeout: 15_000 })

    await page.getByRole('button', { name: '成绩管理' }).click()
    await page.getByTestId('exam-score-user').fill('没有这个人zzz')
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-score-empty')).toContainText('暂无成绩', { timeout: 15_000 })
    await expect(page.getByTestId('exam-score-empty')).toContainText('当前筛选无匹配')

    await page.getByRole('button', { name: '试卷管理' }).click()
    await page.getByTestId('exam-paper-name').fill('')
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await page.getByRole('button', { name: '创建试卷' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '创建试卷' })
    await modal.locator('input[placeholder="如 10 月合规抽测"]').fill(paperName)
    await expect(modal.getByRole('button', { name: '保存试卷' })).toBeEnabled({ timeout: 15_000 })
    await modal.getByRole('button', { name: '保存试卷' }).click()
    await expect(modal).toBeHidden({ timeout: 15_000 })
    const row = page.locator('tr', { hasText: paperName })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '发布' }).click()
    await page.getByRole('button', { name: '确认发布' }).click()
    await expect(row.getByText('已发布')).toBeVisible({ timeout: 15_000 })

    await row.getByRole('button', { name: '指派考生' }).click()
    const assign = page.locator('.modal-mask .card').filter({ hasText: '指派考生' })
    const start = assign.locator('input[type="datetime-local"]').nth(0)
    const end = assign.locator('input[type="datetime-local"]').nth(1)
    await end.fill(localInput(new Date(Date.now() + 60 * 60 * 1000)))
    await start.fill(localInput(new Date(Date.now() + 3 * 60 * 60 * 1000)))
    await assign.getByRole('button', { name: '确认指派' }).click()
    await expect(page.getByTestId('exam-assign-error')).toContainText('开始时间须早于结束时间')
    await shot(page, '06-exam-window-order')

    await start.fill(localInput(new Date(Date.now() + 24 * 60 * 60 * 1000)))
    await end.fill(localInput(new Date(Date.now() + 48 * 60 * 60 * 1000)))
    await assign.getByRole('button', { name: '确认指派' }).click()
    await expect(assign).toBeHidden({ timeout: 15_000 })
    await row.getByRole('button', { name: '考生作答' }).click()
    await expect(page.getByTestId('exam-window-dialog')).toContainText('不在考试窗口内', { timeout: 15_000 })
    await shot(page, '07-exam-1161')
    await page.getByTestId('exam-window-ok').click()

    await row.getByRole('button', { name: '指派考生' }).click()
    await page.locator('.modal-mask .card').filter({ hasText: '指派考生' }).getByRole('button', { name: '确认指派' }).click()
    await expect(page.getByTestId('exam-assign-notice')).toContainText('已指派', { timeout: 15_000 })
    await row.getByRole('button', { name: '考生作答' }).click()
    const take = page.locator('.modal-mask .card').filter({ hasText: '在线作答' })
    await expect(take.locator('.quiz-q')).toHaveCount(1, { timeout: 15_000 })
    await take.getByRole('button', { name: '交卷' }).click()
    await expect(page.getByTestId('exam-submit-confirm')).toContainText('未答 1 题，确认交卷？')
    await shot(page, '08-exam-unanswered')
    await take.getByRole('button', { name: '继续作答' }).click()
    await take.getByRole('button', { name: '关闭' }).click()
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('manual gap hint and mine alert under 60', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const period = freshPeriod()
    const stamp = Date.now()
    const code = `E2E_GAP_${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/perf/metric')
    await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })
    await page.getByTestId('metric-create-open').click()
    const create = page.locator('.drawer.on')
    await create.getByTestId('metric-code').fill(code)
    await create.getByTestId('metric-name').fill(`边角缺项 ${stamp}`)
    await create.getByTestId('metric-save').click()
    await expect(page.locator('tbody tr').filter({ hasText: code })).toBeVisible({ timeout: 15_000 })

    await page.locator('input[placeholder="指标名称"]').fill(String(stamp))
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('tbody tr').filter({ hasText: code })).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('metric-bind-open').click()
    const bind = page.locator('.drawer.on')
    await bind.getByTestId('bind-position').selectOption('R5')
    await bind.getByTestId(`bind-check-${code}`).check()
    await bind.getByTestId(`bind-weight-${code}`).fill('100')
    await bind.getByTestId('metric-bind-save').click()
    await expect(page.getByTestId('metric-bind-ok')).toContainText('已绑定 1 项指标', { timeout: 15_000 })

    await page.goto('/ims/perf/calc')
    await page.getByTestId('perf-period').fill(period)
    await page.getByTestId('perf-period').press('Tab')
    await page.getByTestId('perf-run-open').click()
    await page.getByTestId('perf-run-period').fill(period)
    const runResp = page.waitForResponse((r) => r.url().includes('/perf/calc/run') && r.request().method() === 'POST')
    await page.getByTestId('perf-run-confirm').click()
    const runJson = (await (await runResp).json()) as { code: number }
    expect(runJson.code).toBe(0)
    const staffRow = page.getByTestId(`perf-row-${STAFF}`)
    await expect(staffRow).toBeVisible({ timeout: 15_000 })
    await expect(staffRow.getByTestId(`perf-missing-hint-${STAFF}`)).toContainText('缺项按 0 分计入（PER-C-R1）')
    await shot(page, '09-missing-hint')

    await staffRow.getByTestId('perf-supplement').click()
    await page.getByTestId('perf-manual-reason').fill('边角补录')
    await page.getByTestId('perf-manual-value').fill('40')
    await page.getByTestId('perf-manual-save').click()
    await expect(staffRow.getByTestId(`perf-status-${STAFF}`)).toContainText('待核准', { timeout: 15_000 })
    await page.getByTestId('perf-approve-open').click()
    await page.getByTestId('perf-approve-remark').fill('发布待改进')
    await page.getByTestId('perf-approve-confirm').click()
    await expect(page.getByTestId('perf-approve-result')).toContainText('已发布', { timeout: 15_000 })
    await expect(staffRow.getByTestId(`perf-status-${STAFF}`)).toContainText('已发布')
    await page.locator('.drawer.on .dr-x').click()
    await staffRow.getByTestId('perf-detail').click()
    const detail = page.locator('.drawer.on')
    await expect(detail.getByTestId('perf-approve-remark-view')).toContainText('发布待改进')
    await expect(detail).toContainText('人工补充 MANUAL')
    await detail.locator('.dr-x').click()

    await logout(page)
    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await page.getByTestId('perf-mine-period').fill(period)
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-score')).toHaveText('40.00', { timeout: 15_000 })
    await expect(page.getByTestId('perf-mine-grade')).toContainText('待改进')
    await expect(page.getByTestId('perf-mine-alert')).toHaveText('本期得分低于 60，已通知您与直属上级')
    await expect(page.getByTestId('perf-mine-detail')).toContainText('人工补充')
    await shot(page, '10-mine-alert')
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
