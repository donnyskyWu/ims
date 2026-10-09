import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/fin-226'

/**
 * #226 台账查询空态、结账边角文案、成本录入校验、反查筛选空态。
 * 不重建 #196 导出过期，也不重建 #207 分成/看板筛选空态。
 */
test.describe('fin ledger form and checkout tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('ledger query, checkout copy, cost validation, and trace filter empty', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/fin/ledger')
    await expect(page.locator('h1')).toHaveText('台账对账', { timeout: 15_000 })
    await expect(page.getByTestId('fin-ledger-jump-empty')).toContainText('按场次核对四账')
    await page.getByTestId('fin-ledger-search').click()
    await expect(page.getByTestId('fin-ledger-query-empty')).toContainText('请填写场次 ID')
    await page.screenshot({ path: `${SHOT_DIR}/01-ledger-query-empty.png`, fullPage: true })

    await page.getByTestId('fin-ledger-query').fill('IMS-226')
    await page.getByTestId('fin-ledger-search').click()
    await expect(page.getByTestId('fin-ledger-query-invalid')).toContainText('场次号仅支持字母与数字')
    await page.screenshot({ path: `${SHOT_DIR}/02-ledger-query-invalid.png`, fullPage: true })

    await page.getByTestId('fin-ledger-query').fill('IMS209901019990001')
    await page.getByTestId('fin-ledger-search').click()
    await expect(page.getByTestId('fin-ledger-missing')).toContainText('未找到场次', { timeout: 15_000 })

    const pendingReady = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.ok(),
    )
    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    await pendingReady
    await page.route('**/fin/cost/pending-sessions**', (route) => route.abort())
    await page.locator('.tab', { hasText: '待录入清单' }).click()
    await expect(page.getByTestId('fin-cost-pending-empty')).toContainText('待录入清单加载失败，请重试', { timeout: 15_000 })
    await page.screenshot({ path: `${SHOT_DIR}/03-cost-pending-load-fail.png`, fullPage: true })
    await page.unroute('**/fin/cost/pending-sessions**')
    const recovered = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.ok(),
    )
    await page.getByRole('button', { name: '查询' }).click()
    await recovered

    const stamp = Date.now()
    const year = 2800 + (stamp % 700)
    const month = String((Math.floor(stamp / 700) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    await page.getByTestId('fin-period-month').fill(periodMonth)
    await page.getByTestId('fin-period-month').blur()
    await expect(page.getByTestId('fin-period-close-hint')).toContainText('结账后该月场次录入/核准/重算冻结')
    await expect(page.getByTestId('fin-period-close')).toBeEnabled()
    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/fin/period/close') && r.request().method() === 'POST' && r.ok(),
    )
    await page.getByTestId('fin-period-close').click()
    const closeBody = (await (await closeResp).json()) as { code: number; data?: { financeStatus?: string } }
    expect(closeBody.code).toBe(0)
    expect(closeBody.data?.financeStatus).toBe('LOCKED')
    await expect(page.getByTestId('fin-period-status')).toHaveText('LOCKED')
    await expect(page.getByTestId('fin-period-close-done')).toContainText(`已结账 · ${periodMonth}`)
    await expect(page.getByTestId('fin-period-close-done')).toContainText('录入、核准、更正均冻结')
    await expect(page.getByTestId('fin-period-close-hint')).toHaveText('本月已结账，无需重复结账')
    await expect(page.getByTestId('fin-period-close')).toBeDisabled()
    await expect(page.getByTestId('fin-period-close')).toHaveAttribute('title', '本月已结账，无需重复结账')
    await page.screenshot({ path: `${SHOT_DIR}/04-period-close-done.png`, fullPage: true })

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E fin 226 ${stamp}`,
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.ok(),
    )
    await page.getByRole('button', { name: '查询' }).click()
    await pendingResp
    const pendingRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await pendingRow.getByRole('button', { name: '录入' }).click()
    const entryDrawer = page.locator('.drawer.on').filter({ hasText: '成本录入' })
    await expect(entryDrawer).toBeVisible()
    await entryDrawer.getByRole('spinbutton', { name: '佣金率' }).fill('0')
    await entryDrawer.getByRole('button', { name: '提交' }).click()
    await expect(entryDrawer.getByTestId('fin-cost-entry-error')).toContainText('1001 佣金率须大于 0 且不超过 1')
    await expect(entryDrawer).toBeVisible()
    await page.screenshot({ path: `${SHOT_DIR}/05-cost-rate-invalid.png`, fullPage: true })

    await entryDrawer.getByRole('spinbutton', { name: '佣金率' }).fill('0.05')
    await entryDrawer.getByRole('spinbutton', { name: '投放成本' }).fill('-1')
    await entryDrawer.getByRole('button', { name: '提交' }).click()
    await expect(entryDrawer.getByTestId('fin-cost-entry-error')).toContainText('1001 金额不能为负')

    await entryDrawer.getByRole('spinbutton', { name: '投放成本' }).fill('1.239')
    await entryDrawer.getByRole('button', { name: '提交' }).click()
    await expect(entryDrawer.getByTestId('fin-cost-entry-error')).toContainText('1001 金额最多两位小数')

    await entryDrawer.getByRole('spinbutton', { name: '投放成本' }).fill('10.50')
    await entryDrawer.getByRole('spinbutton', { name: '冲话费摊销' }).fill('0')
    await entryDrawer.getByRole('spinbutton', { name: '固定成本' }).fill('0')
    await entryDrawer.getByRole('spinbutton', { name: '样品成本' }).fill('0')
    await entryDrawer.getByRole('spinbutton', { name: '达人分成' }).fill('0')
    await entryDrawer.getByRole('spinbutton', { name: '实名人分成' }).fill('0')
    await expect(entryDrawer.getByTestId('fin-cost-entry-total')).toContainText('¥5,010.50')
    await page.screenshot({ path: `${SHOT_DIR}/06-cost-total-preview.png`, fullPage: true })

    await submitAndConfirmFinCostViaUi(page, sessionCode)
    await page.locator('.tab', { hasText: '已录入管理' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.ok(),
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const enteredRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(enteredRow).toContainText('已核准', { timeout: 15_000 })
    await enteredRow.getByTestId('fin-cost-correction-open').click()
    const correction = page.locator('.drawer.on').filter({ hasText: '成本更正' })
    await expect(correction).toBeVisible()
    await expect(correction.getByTestId('fin-cost-correction-reason-hint')).toContainText('不超过 512 字')
    await correction.getByTestId('fin-cost-correction-reason').fill('测'.repeat(513))
    await correction.getByTestId('fin-cost-correction-submit').click()
    await expect(correction.getByTestId('fin-lock-adjust-error')).toContainText('1001 更正原因不超过 512 字')
    await expect(correction).toBeVisible()
    await page.screenshot({ path: `${SHOT_DIR}/07-correction-reason-long.png`, fullPage: true })

    await page.goto('/ims/fin/profit-trace')
    await expect(page.locator('h1')).toHaveText('利润反查', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(`NO-SUCH-${stamp}`)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('fin-trace-list-empty')).toHaveText('当前筛选无已核算利润', { timeout: 15_000 })
    await page.screenshot({ path: `${SHOT_DIR}/08-trace-list-filter-empty.png`, fullPage: true })

    await page.getByTestId('fin-trace-tab-aggregate').click()
    await page.getByTestId('fin-trace-aggregate-from').fill('1999-01-01')
    await page.getByTestId('fin-trace-aggregate-to').fill('1999-01-31')
    await page.getByTestId('fin-trace-aggregate-query').click()
    await expect(page.getByTestId('fin-trace-aggregate-empty')).toContainText('当前筛选下该维度暂无已核算利润', {
      timeout: 15_000,
    })

    await page.getByTestId('fin-trace-tab-abnormal').click()
    await page.getByTestId('fin-trace-abnormal-platform').fill('ZZZ')
    await page.getByTestId('fin-trace-abnormal-query').click()
    await expect(page.getByTestId('fin-trace-abnormal-empty')).toContainText('当前筛选下暂无异常利润', {
      timeout: 15_000,
    })
    await page.screenshot({ path: `${SHOT_DIR}/09-trace-abnormal-filter-empty.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
