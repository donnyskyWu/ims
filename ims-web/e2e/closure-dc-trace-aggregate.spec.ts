import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  E2E_FIN_ACCOUNT_NO,
  loginAdmin,
  openDcAccountTraceViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-91-screenshots'

/**
 * Checklist E2E-S12-01 聚合/性能切片（#91 · 纯 UI）
 * 复用账号穿透链 → 关系图成本/利润节点、面包屑截断、聚合表、性能监控页。
 */
test.describe('dc trace aggregate and perf closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('aggregate table, cost profit nodes, breadcrumb truncate and perf metrics', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const registered = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, registered.sessionCode)

    const trace = await openDcAccountTraceViaUi(page, E2E_FIN_ACCOUNT_NO, registered.sessionCode)
    const accountNode = trace?.nodes?.find(
      (node) => node.nodeType === 'ACCOUNT' && node.nodeLabel?.includes(E2E_FIN_ACCOUNT_NO),
    ) as { nodeId?: string; nodeLabel?: string } | undefined
    expect(accountNode?.nodeId).toBeTruthy()

    const costNode = page.locator(
      `[data-testid="dc-trace-cost-node"][data-node-id="cost:${registered.sessionCode}"]`,
    )
    const profitNode = page.locator(
      `[data-testid="dc-trace-profit-node"][data-node-id="profit:${registered.sessionCode}"]`,
    )
    await expect(costNode).toContainText('16,600.00')
    await expect(profitNode).toContainText('81,400.00')
    await expect(page.getByTestId('dc-trace-breadcrumb')).toContainText('源头：')
    await expect(page.locator('[data-testid="dc-trace-crumb"]')).toHaveCount(1)
    await page.screenshot({ path: `${SHOTS}/01-cost-profit-nodes.png`, fullPage: true })

    const personBtn = page.locator('[data-testid="dc-trace-node-drill"][data-node-type="PERSON"]').first()
    await expect(personBtn).toBeVisible()
    const drillResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await personBtn.click()
    expect((await (await drillResp).json()).code).toBe(0)
    await expect(page.locator('[data-testid="dc-trace-crumb"]')).toHaveCount(2)
    await expect(page.getByTestId('dc-trace-breadcrumb')).toContainText('关联：实名人')

    const backResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.locator('[data-testid="dc-trace-crumb"][data-crumb-index="0"]').click()
    expect((await (await backResp).json()).code).toBe(0)
    await expect(page.locator('[data-testid="dc-trace-crumb"]')).toHaveCount(1)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('账号')
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText(E2E_FIN_ACCOUNT_NO)
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/02-breadcrumb-truncate.png`, fullPage: true })

    const aggResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/aggregate') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('dc-trace-mode-aggregate').click()
    const aggBody = (await (await aggResp).json()) as {
      code: number
      data?: Array<{
        dimensionValue?: string
        dimensionLabel?: string
        sessionCount?: number
        gmv?: number | null
        totalCost?: number | null
        netProfit?: number | null
      }>
    }
    expect(aggBody.code).toBe(0)
    const accountRow = aggBody.data?.find((row) => row.dimensionValue === accountNode!.nodeId)
    expect(accountRow?.sessionCount).toBeGreaterThanOrEqual(1)
    expect(accountRow?.gmv ?? 0).toBeGreaterThanOrEqual(100_000)
    expect(accountRow?.totalCost ?? 0).toBeGreaterThanOrEqual(16_600)
    expect(accountRow?.netProfit).not.toBeNull()
    const yuan = (value: number) =>
      Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    const table = page.getByTestId('dc-trace-aggregate')
    await expect(table).toContainText(accountRow?.dimensionLabel || E2E_FIN_ACCOUNT_NO)
    await expect(table).toContainText(yuan(accountRow!.gmv!))
    await expect(table).toContainText(yuan(accountRow!.totalCost!))
    await expect(table).toContainText(yuan(accountRow!.netProfit!))
    await page.screenshot({ path: `${SHOTS}/03-aggregate-account.png`, fullPage: true })

    const teamResp = page.waitForResponse(
      (r) =>
        r.url().includes('/dc/trace/aggregate') &&
        r.url().includes('aggregateBy=TEAM') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('dc-trace-aggregate-by').selectOption('TEAM')
    const teamBody = (await (await teamResp).json()) as { code: number; data?: Array<{ dimensionLabel?: string }> }
    expect(teamBody.code).toBe(0)
    expect((teamBody.data || []).length).toBeGreaterThanOrEqual(1)
    await expect(table).toContainText(teamBody.data?.[0]?.dimensionLabel || '团队')
    await page.screenshot({ path: `${SHOTS}/04-aggregate-team.png`, fullPage: true })

    const perfResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/perf-metrics') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('dc-trace-query-cost').click()
    const perfBody = (await (await perfResp).json()) as {
      code: number
      data?: { queryCount?: number; targetP95Ms?: number; p95Ms?: number; dailyPressureTestPassed?: boolean }
    }
    expect(perfBody.code).toBe(0)
    expect(perfBody.data?.targetP95Ms).toBe(3000)
    expect(perfBody.data?.queryCount ?? 0).toBeGreaterThanOrEqual(1)
    expect(typeof perfBody.data?.p95Ms).toBe('number')
    expect(typeof perfBody.data?.dailyPressureTestPassed).toBe('boolean')
    await expect(page.locator('h1')).toHaveText('穿透性能监控')
    await expect(page.getByTestId('dc-trace-perf-target')).toContainText('3,000ms')
    await expect(page.getByTestId('dc-trace-perf-count')).toContainText(String(perfBody.data?.queryCount))
    await expect(page.getByTestId('dc-trace-perf-slow')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/05-perf-metrics.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
