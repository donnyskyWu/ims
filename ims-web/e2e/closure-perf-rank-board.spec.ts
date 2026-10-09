import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #187 考核结果页排名区。
 * 未发布周期给出空态；核准发布后展示红榜、部门均分和末位预警桩（不外发钉钉）。
 */
const shotDir = '/opt/cursor/artifacts/e2e-187-screenshots'
const PERIOD = '2026-09'
const EMPTY_PERIOD = '2026-07'
const STAFF = '绩效员工甲'
const PEER = '绩效员工乙'

test.describe('perf rank board edges', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('unpublished empty state, then top3 average and pip stub', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()

    await loginAdmin(page)
    await page.goto('/ims/perf/result')
    await expect(page.locator('h1')).toHaveText('考核结果', { timeout: 15_000 })
    await page.getByTestId('perf-rank-period').fill(EMPTY_PERIOD)
    await page.getByTestId('perf-rank-period').press('Tab')
    await expect(page.getByTestId('perf-rank-empty')).toContainText('尚未核准发布', { timeout: 15_000 })
    await expect(page.getByTestId('perf-rank-empty')).toContainText('发布后自动生成排名')
    await page.screenshot({ path: `${shotDir}/01-rank-unpublished.png` })

    await publishSeptember(page, stamp)

    await page.goto('/ims/perf/result')
    await expect(page.locator('h1')).toHaveText('考核结果', { timeout: 15_000 })
    await page.getByTestId('perf-rank-period').fill(PERIOD)
    await page.getByTestId('perf-rank-period').press('Tab')
    await expect(page.getByTestId('perf-rank-top3')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId(`perf-rank-top-${STAFF}`)).toContainText('金')
    await expect(page.getByTestId(`perf-rank-top-${STAFF}`)).toContainText('100.00')
    await expect(page.getByTestId(`perf-rank-top-${PEER}`)).toContainText('银')
    await expect(page.getByTestId(`perf-rank-top-${PEER}`)).toContainText('40.00')
    await expect(page.getByTestId('perf-rank-avg-value')).toHaveText('70.00')
    await expect(page.getByTestId('perf-rank-board')).toContainText('不含竞品分析维度')
    await page.screenshot({ path: `${shotDir}/02-rank-top3.png` })

    await expect(page.getByTestId(`perf-rank-tail-${PEER}`)).toContainText('40.00')
    await expect(page.getByTestId(`perf-rank-tail-${PEER}`)).toContainText('待改进')
    await expect(page.getByTestId('perf-rank-pip')).toContainText('PIP')
    await expect(page.getByTestId('perf-rank-pip')).toContainText('不外发钉钉')
    const rankTable = page.getByTestId('perf-rank-row').filter({ hasText: PEER })
    await expect(rankTable).toContainText('已预警')
    await expect(rankTable).toContainText('待改进 <60')
    await page.screenshot({ path: `${shotDir}/03-rank-pip-stub.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})

async function publishSeptember(page: Page, stamp: number) {
  const trainCode = `E2E_RK_TR_${stamp}`
  const meetCode = `E2E_RK_MT_${stamp}`
  await createAutoMetric(page, {
    code: trainCode,
    name: `培训完成率 ${stamp}`,
    module: 'TRAIN',
    expression: 'finish_rate',
  })
  await createAutoMetric(page, {
    code: meetCode,
    name: `日报按时率 ${stamp}`,
    module: 'MEET',
    expression: 'on_time_rate',
  })
  await bindPair(page, stamp, trainCode, meetCode)

  await page.goto('/ims/perf/calc')
  await expect(page.locator('h1')).toHaveText('绩效计算与核准', { timeout: 15_000 })
  await page.getByTestId('perf-period').fill(PERIOD)
  await page.getByTestId('perf-run-open').click()
  await page.getByTestId('perf-run-period').fill(PERIOD)
  const runResp = page.waitForResponse(
    (response) => response.url().includes('/perf/calc/run') && response.request().method() === 'POST',
  )
  await page.getByTestId('perf-run-confirm').click()
  const runJson = (await (await runResp).json()) as { code: number }
  if (runJson.code === 1155) return
  expect(runJson.code).toBe(0)

  await expect(page.getByTestId(`perf-row-${PEER}`)).toBeVisible({ timeout: 15_000 })
  await page.getByTestId(`perf-row-${PEER}`).getByTestId('perf-supplement').click()
  await page.getByTestId('perf-manual-reason').fill('现场补录')
  await page.getByTestId('perf-manual-value').fill('80')
  await page.getByTestId('perf-manual-save').click()
  await expect(page.getByTestId(`perf-status-${PEER}`)).toContainText('待核准', { timeout: 15_000 })

  await page.getByTestId('perf-approve-open').click()
  await page.getByTestId('perf-approve-confirm').click()
  await expect(page.getByTestId('perf-approve-result')).toContainText('已发布 2 人', { timeout: 15_000 })
}

async function createAutoMetric(
  page: Page,
  item: { code: string; name: string; module: string; expression: string },
) {
  await page.goto('/ims/perf/metric')
  await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })
  await page.getByTestId('metric-create-open').click()
  const drawer = page.locator('.drawer.on')
  await drawer.getByTestId('metric-code').fill(item.code)
  await drawer.getByTestId('metric-name').fill(item.name)
  await drawer.getByTestId('metric-source').selectOption('AUTO')
  await drawer.getByTestId('metric-module').selectOption(item.module)
  await drawer.getByTestId('metric-expression').fill(item.expression)
  await drawer.getByTestId('metric-weight').fill('50')
  await drawer.getByTestId('metric-rule-type').selectOption('LINEAR')
  await drawer.getByTestId('metric-save').click()
  await expect(page.locator('tbody tr').filter({ hasText: item.code })).toBeVisible({ timeout: 15_000 })
}

async function bindPair(page: Page, stamp: number, trainCode: string, meetCode: string) {
  await page.goto('/ims/perf/metric')
  await page.locator('input[placeholder="指标名称"]').fill(String(stamp))
  await page.getByRole('button', { name: '查询' }).click()
  await expect(page.locator('tbody tr').filter({ hasText: trainCode })).toBeVisible({ timeout: 15_000 })
  await page.getByTestId('metric-bind-open').click()
  const drawer = page.locator('.drawer.on')
  await drawer.getByTestId('bind-position').selectOption('R5')
  await drawer.getByTestId(`bind-check-${trainCode}`).check()
  await drawer.getByTestId(`bind-check-${meetCode}`).check()
  await drawer.getByTestId(`bind-weight-${trainCode}`).fill('50')
  await drawer.getByTestId(`bind-weight-${meetCode}`).fill('50')
  await drawer.getByTestId('metric-bind-save').click()
  await expect(page.getByTestId('metric-bind-ok')).toContainText('已绑定 2 项指标')
}
