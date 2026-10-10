import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * PERF-001 覆盖率 / 试取数 + PERF-004 预警处置 / 连续两月辅导（acceptance · 纯 UI · #137）
 * Given: 指标页可创建指标，种子里有 R5 员工
 * When: 创建手工与自动指标、试取数、把 2026-07/08 补成 40 分并核准
 * Then: 覆盖率计数变化、手工不能取数、自动通道可用、预警可处置、辅导名单含两期、员工只见本人提示
 */
const shotDir = '/opt/cursor/artifacts/e2e-137-screenshots'
const STAFF = '绩效员工甲'

test.describe('perf coverage and rank alert closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('coverage card, local fetch, alert handle, two-month coaching', async ({ page }) => {
    test.setTimeout(240_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const manualCode = `E2E_MAN_${stamp}`
    const autoCode = `E2E_AUTO_${stamp}`

    await loginAdmin(page)
    const coverageReady = page.waitForResponse(
      (res) => res.url().includes('/perf/metric/auto-coverage') && res.request().method() === 'GET',
    )
    await page.goto('/ims/perf/metric')
    await coverageReady
    await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })
    await expect(page.getByTestId('metric-coverage-count')).toBeVisible()
    const before = await readCoverage(page)

    await createMetric(page, { code: manualCode, name: `手工 ${stamp}`, source: 'MANUAL' })
    const afterManual = await readCoverage(page)
    expect(afterManual.enabled).toBe(before.enabled + 1)
    expect(afterManual.auto).toBe(before.auto)
    await page.getByTestId('metric-coverage-manual').click()
    await expect(page.getByTestId('metric-coverage-manual-list')).toContainText(manualCode)
    await page.screenshot({ path: `${shotDir}/01-coverage-manual.png` })

    await createMetric(page, {
      code: autoCode,
      name: `自动 ${stamp}`,
      source: 'AUTO',
      expression: 'finish_rate',
    })
    const afterAuto = await readCoverage(page)
    expect(afterAuto.auto).toBe(before.auto + 1)
    expect(afterAuto.enabled).toBe(before.enabled + 2)

    const autoRow = page.locator('tbody tr').filter({ hasText: autoCode })
    await autoRow.getByTestId('metric-fetch').click()
    await page.getByTestId('metric-fetch-period').fill('2026-09')
    await page.getByTestId('metric-fetch-run').click()
    await expect(page.getByTestId('metric-fetch-result')).toContainText('通道可用', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/02-fetch-auto.png` })
    await page.locator('.drawer.on .dr-x').click()

    const manualRow = page.locator('tbody tr').filter({ hasText: manualCode })
    await manualRow.getByTestId('metric-fetch').click()
    await page.getByTestId('metric-fetch-period').fill('2026-09')
    await page.getByTestId('metric-fetch-run').click()
    await expect(page.getByTestId('metric-fetch-result')).toContainText('手工指标不支持自动取数')
    await page.screenshot({ path: `${shotDir}/03-fetch-manual.png` })
    await page.locator('.drawer.on .dr-x').click()

    await page.locator('input[placeholder="指标名称"]').fill(String(stamp))
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('tbody tr').filter({ hasText: manualCode })).toBeVisible()
    await page.getByTestId('metric-bind-open').click()
    const bindDrawer = page.locator('.drawer.on')
    await bindDrawer.getByTestId('bind-position').selectOption('R5')
    await bindDrawer.getByTestId(`bind-check-${manualCode}`).check()
    await bindDrawer.getByTestId(`bind-weight-${manualCode}`).fill('100')
    await bindDrawer.getByTestId('metric-bind-save').click()
    await expect(page.getByTestId('metric-bind-ok')).toContainText('已绑定 1 项指标')

    await publishLow(page, '2026-07')
    await publishLow(page, '2026-08')

    await page.goto('/ims/perf/rank')
    await expect(page.locator('h1')).toHaveText('排名与预警', { timeout: 15_000 })
    await page.getByTestId('perf-rank-period').fill('2026-08')
    await page.getByTestId('perf-rank-period').press('Tab')
    await expect(page.getByTestId(`perf-rank-row-${STAFF}`)).toContainText('待改进', { timeout: 15_000 })
    await expect(page.getByTestId('perf-rank-distribution')).toContainText('待改进')
    await page.screenshot({ path: `${shotDir}/04-rank-board.png` })

    await page.getByTestId('perf-rank-tab-alerts').click()
    const alertRow = page.getByTestId('perf-alert-row').filter({ hasText: STAFF }).first()
    await expect(alertRow).toContainText('本人')
    await expect(alertRow).toContainText('直属上级')
    await expect(alertRow).toContainText('HR')
    await expect(alertRow.getByTestId('perf-alert-status')).toContainText('待处置')
    await page.screenshot({ path: `${shotDir}/05-alert-list.png` })
    await alertRow.getByTestId('perf-alert-handle').click()
    await page.getByTestId('perf-alert-save').click()
    await expect(page.getByTestId('perf-alert-error')).toContainText('1001')
    await page.getByTestId('perf-alert-remark').fill('安排辅导')
    await page.getByTestId('perf-alert-plan').fill('每周复盘')
    await page.getByTestId('perf-alert-save').click()
    await expect(alertRow.getByTestId('perf-alert-status')).toContainText('已处置', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/06-alert-handled.png` })

    await page.getByTestId('perf-rank-tab-coaching').click()
    const coachRow = page.getByTestId('perf-coaching-row').filter({ hasText: STAFF })
    await expect(coachRow).toContainText('2')
    await expect(coachRow).toContainText('2026-07')
    await expect(coachRow).toContainText('2026-08')
    await coachRow.getByTestId('perf-coaching-detail').click()
    await expect(page.getByTestId('perf-coaching-periods')).toContainText('待改进')
    await page.screenshot({ path: `${shotDir}/07-coaching.png` })
    await page.locator('.drawer.on .dr-x').click()

    await logout(page)
    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await page.getByTestId('perf-mine-period').fill('2026-08')
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-alert')).toContainText('本期得分低于 60', { timeout: 15_000 })
    await expect(page.getByText('绩效员工乙')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/08-mine-alert.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})

async function readCoverage(page: Page) {
  const text = await page.getByTestId('metric-coverage-count').innerText()
  const matched = text.match(/自动\s+(\d+)\s+\/\s+启用\s+(\d+)/)
  expect(matched, text).toBeTruthy()
  return { auto: Number(matched?.[1]), enabled: Number(matched?.[2]) }
}

async function createMetric(
  page: Page,
  item: { code: string; name: string; source: 'MANUAL' | 'AUTO'; expression?: string },
) {
  await page.goto('/ims/perf/metric')
  await page.getByTestId('metric-create-open').click()
  const drawer = page.locator('.drawer.on')
  await drawer.getByTestId('metric-code').fill(item.code)
  await drawer.getByTestId('metric-name').fill(item.name)
  await drawer.getByTestId('metric-source').selectOption(item.source)
  if (item.source === 'AUTO') {
    await drawer.getByTestId('metric-module').selectOption('TRAIN')
    await drawer.getByTestId('metric-expression').fill(item.expression || 'finish_rate')
  }
  await drawer.getByTestId('metric-weight').fill('10')
  await drawer.getByTestId('metric-rule-type').selectOption('LINEAR')
  await drawer.getByTestId('metric-save').click()
  await expect(page.locator('tbody tr').filter({ hasText: item.code })).toBeVisible({ timeout: 15_000 })
}

async function publishLow(page: Page, period: string) {
  await page.goto('/ims/perf/calc')
  await expect(page.locator('h1')).toHaveText('绩效计算与核准', { timeout: 15_000 })
  await page.getByTestId('perf-period').fill(period)
  await page.getByTestId('perf-run-open').click()
  await page.getByTestId('perf-run-period').fill(period)
  const runResp = page.waitForResponse(
    (res) => res.url().includes('/perf/calc/run') && res.request().method() === 'POST',
  )
  await page.getByTestId('perf-run-confirm').click()
  const runJson = (await (await runResp).json()) as { code: number; msg?: string }
  if (runJson.code === 1155) {
    await expect(page.getByTestId(`perf-status-${STAFF}`)).toContainText('已发布', { timeout: 15_000 })
    return
  }
  expect(runJson.code, runJson.msg || '').toBe(0)
  await expect(page.getByTestId(`perf-row-${STAFF}`)).toBeVisible({ timeout: 15_000 })
  for (const name of [STAFF, '绩效员工乙']) {
    const row = page.getByTestId(`perf-row-${name}`)
    const status = row.getByTestId(`perf-status-${name}`)
    const label = await status.innerText()
    if (label.includes('待核准') || label.includes('已发布')) continue
    await row.getByTestId('perf-supplement').click()
    await page.getByTestId('perf-manual-reason').fill('预警演示补录')
    await page.getByTestId('perf-manual-value').fill('40')
    await page.getByTestId('perf-manual-save').click()
    await expect(status).toContainText('待核准', { timeout: 15_000 })
  }
  if ((await page.getByTestId(`perf-status-${STAFF}`).innerText()).includes('已发布')) return
  await page.getByTestId('perf-approve-open').click()
  await page.getByTestId('perf-approve-confirm').click()
  await expect(page.getByTestId('perf-approve-result')).toContainText('已发布', { timeout: 15_000 })
  await expect(page.getByTestId(`perf-status-${STAFF}`)).toContainText('已发布')
  await page.locator('.drawer.on .dr-x').click()
}

async function logout(page: Page) {
  const close = page.locator('.drawer.on .dr-x')
  if (await close.count()) await close.first().click()
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}
