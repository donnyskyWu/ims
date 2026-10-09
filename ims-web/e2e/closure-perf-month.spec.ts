import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * Checklist E2E-S9-03 / S9-04 / S9-05 / S9-06（acceptance · 纯 UI · #95）
 * Given: 种子已放入 R5 员工、2026-09 培训完成与日报按时
 * When: 页面创建指标集 → 月度计算 → 缺原因补充 → 核准发布 → 员工查看
 * Then: 待核准/待人工、1158、已发布、发布前 1157、员工只见本人；锁定重算 1155
 */
const shotDir = '/opt/cursor/artifacts/e2e-95-screenshots'
const PERIOD = '2026-09'
const STAFF = '绩效员工甲'
const PEER = '绩效员工乙'

test.describe('perf month closure S9-03..06', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('calc, supplement 1158, publish, employee sees only self', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const trainCode = `E2E_TR_${stamp}`
    const meetCode = `E2E_MT_${stamp}`

    await loginAdmin(page)
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
      (r) => r.url().includes('/perf/calc/run') && r.request().method() === 'POST',
    )
    await page.getByTestId('perf-run-confirm').click()
    const runJson = (await (await runResp).json()) as { code: number; data?: { targetUserCount?: number } }
    expect(runJson.code).toBe(0)
    expect(runJson.data?.targetUserCount).toBe(2)
    await expect(page.getByTestId('perf-calc-toast')).toContainText('2 人')

    const staffRow = page.getByTestId(`perf-row-${STAFF}`)
    const peerRow = page.getByTestId(`perf-row-${PEER}`)
    await expect(staffRow).toContainText('100.00')
    await expect(staffRow.getByTestId(`perf-status-${STAFF}`)).toContainText('待核准')
    await expect(staffRow.getByTestId(`perf-grade-${STAFF}`)).toContainText('优秀')
    await expect(peerRow.getByTestId(`perf-status-${PEER}`)).toContainText('待人工')
    await staffRow.getByTestId('perf-detail').click()
    const detail = page.locator('.drawer.on')
    await expect(detail).toContainText('培训完成率')
    await expect(detail).toContainText('日报按时率')
    await expect(detail).toContainText('AUTO')
    await page.screenshot({ path: `${shotDir}/01-s9-03-calc-multisource.png` })
    await detail.locator('.dr-x').click()

    await logout(page)
    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await expect(page.locator('h1')).toHaveText('我的绩效', { timeout: 15_000 })
    await page.getByTestId('perf-mine-period').fill(PERIOD)
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-empty')).toContainText('尚未发布', { timeout: 15_000 })
    await expect(page.getByTestId('perf-mine-empty')).toContainText('1157')
    await expect(page.getByText(PEER)).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-s9-06-before-publish-1157.png` })

    await logout(page)
    await loginAdmin(page)
    await page.goto('/ims/perf/calc')
    await page.getByTestId('perf-period').fill(PERIOD)
    await page.getByTestId('perf-period').press('Tab')
    await expect(page.getByTestId(`perf-row-${PEER}`)).toBeVisible({ timeout: 15_000 })
    await page.getByTestId(`perf-row-${PEER}`).getByTestId('perf-supplement').click()
    await expect(page.getByTestId('perf-manual-save')).toBeDisabled()
    await expect(page.getByTestId('perf-manual-hint')).toContainText('1158')
    await page.screenshot({ path: `${shotDir}/03-s9-04-reason-1158.png` })
    await page.getByTestId('perf-manual-reason').fill('现场补录')
    await page.getByTestId('perf-manual-value').fill('80')
    await page.getByTestId('perf-manual-save').click()
    await expect(page.getByTestId(`perf-row-${PEER}`).getByTestId(`perf-status-${PEER}`)).toContainText('待核准', {
      timeout: 15_000,
    })
    await expect(page.getByTestId(`perf-row-${PEER}`)).toContainText('40.00')
    await page.screenshot({ path: `${shotDir}/04-s9-04-supplement-ok.png` })

    await page.getByTestId('perf-approve-open').click()
    await page.getByTestId('perf-approve-confirm').click()
    await expect(page.getByTestId('perf-approve-result')).toContainText('已发布 2 人', { timeout: 15_000 })
    await expect(page.getByTestId(`perf-status-${STAFF}`)).toContainText('已发布')
    await expect(page.getByTestId(`perf-status-${PEER}`)).toContainText('已发布')
    await page.screenshot({ path: `${shotDir}/05-s9-05-published.png` })
    await page.locator('.drawer.on .dr-x').click()

    await logout(page)
    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await page.getByTestId('perf-mine-period').fill(PERIOD)
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-score')).toHaveText('100.00', { timeout: 15_000 })
    await expect(page.getByTestId('perf-mine-grade')).toContainText('优秀')
    await expect(page.getByTestId('perf-mine-detail').filter({ hasText: '培训完成率' })).toBeVisible()
    await expect(page.getByText(PEER)).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/06-s9-06-employee-own.png` })

    await logout(page)
    await loginAdmin(page)
    await page.goto('/ims/perf/calc')
    await page.getByTestId('perf-period').fill(PERIOD)
    await page.getByTestId('perf-period').press('Tab')
    await expect(page.getByTestId(`perf-row-${STAFF}`)).toBeVisible({ timeout: 15_000 })
    await page.getByTestId(`perf-row-${STAFF}`).getByTestId('perf-detail').click()
    await page.getByTestId('perf-recalc').click()
    await expect(page.getByTestId('perf-lock-error')).toContainText('1155', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/07-locked-recalc-1155.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
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
