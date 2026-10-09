import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/fin-154'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #154 FIN 分成列表筛选、发放锁期提示、异常清单空态、期间格式提示。
 * 不覆盖 PDF 导出、趋势粒度、R9 脱敏、台账跳转。
 */
test.describe('fin share tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share filters, locked payoff, abnormal empty, and period format', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const stamp = Date.now()
    const year = 3100 + (stamp % 4000)
    const month = String((Math.floor(stamp / 4000) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    const planStartTime = `${periodMonth}-15T20:00:00+08:00`

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    await page.getByTestId('fin-period-month').fill('2099-13')
    await page.getByTestId('fin-period-month').blur()
    await expect(page.getByTestId('fin-period-error')).toContainText('期间格式须为 yyyy-MM')
    await expect(page.getByTestId('fin-period-close')).toBeDisabled()
    await page.screenshot({ path: `${shotDir}/01-period-format.png`, fullPage: true })

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E share tails ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await page.getByTestId('fin-share-filter-session').fill(sessionCode)
    await page.getByTestId('fin-share-filter-status').selectOption('PAID_OFF')
    const emptyList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await emptyList
    await expect(page.getByTestId('fin-share-empty')).toContainText('当前筛选无分成单')
    await expect(page.getByTestId('fin-share-pager')).toContainText('共 0 条')
    await page.screenshot({ path: `${shotDir}/02-share-filter-empty.png`, fullPage: true })

    const resetList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-reset').click()
    await resetList
    await page.getByTestId('fin-share-filter-session').fill(sessionCode)
    await page.getByTestId('fin-share-filter-target').selectOption('DAREN')
    const darenList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.url().includes('DAREN') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await darenList
    const darenRow = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' })
    await expect(darenRow).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('tbody tr', { hasText: '实名人' })).toHaveCount(0)
    await expect(page.getByTestId('fin-share-pager')).toContainText('共 1 条')
    await page.screenshot({ path: `${shotDir}/03-share-filter-daren.png`, fullPage: true })

    for (const role of ['fin-share-audit-finance', 'fin-share-audit-business'] as const) {
      const auditPut = page.waitForResponse(
        (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
      )
      const auditList = page.waitForResponse(
        (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
      )
      await darenRow.getByTestId(role).click()
      const auditBody = (await (await auditPut).json()) as { code: number }
      expect(auditBody.code).toBe(0)
      await auditList
    }
    await expect(darenRow).toContainText('已审')

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    const periodGet = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/period') &&
        r.url().includes(encodeURIComponent(periodMonth)) &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('fin-period-month').fill(periodMonth)
    await page.getByTestId('fin-period-month').blur()
    await periodGet
    await expect(page.getByTestId('fin-period-close')).toBeEnabled()
    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/fin/period/close') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('fin-period-close').click()
    const closeBody = (await (await closeResp).json()) as { code: number; data?: { financeStatus?: string } }
    expect(closeBody.code).toBe(0)
    expect(closeBody.data?.financeStatus).toBe('LOCKED')
    await expect(page.getByTestId('fin-period-status')).toHaveText('LOCKED')
    await expect(page.getByTestId('fin-period-lock-banner')).toContainText('财务期间已结账')
    await expect(page.getByTestId('fin-period-locked-by')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-period-locked-by.png`, fullPage: true })

    await page.goto('/ims/fin/share/result')
    await page.getByTestId('fin-share-filter-session').fill(sessionCode)
    await page.getByTestId('fin-share-filter-target').selectOption('DAREN')
    const lockedList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await lockedList
    const lockedRow = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' })
    await lockedRow.getByTestId('fin-share-payoff-open').click()
    const drawer = page.getByTestId('fin-share-payoff-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('fin-share-payoff-note').fill('锁后不应发放')
    const payPut = page.waitForResponse(
      (r) => r.url().includes('/payoff') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await drawer.getByTestId('fin-share-payoff-submit').click()
    const payBody = (await (await payPut).json()) as { code: number; msg?: string }
    expect(payBody.code).toBe(1142)
    await expect(drawer.getByTestId('fin-share-payoff-error')).toContainText('1142')
    await expect(drawer.getByTestId('fin-share-payoff-error')).toContainText('财务期间已结账')
    await expect(drawer).toBeVisible()
    await page.screenshot({ path: `${shotDir}/05-payoff-locked.png`, fullPage: true })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.getByTestId('fin-profit-tab-abnormal').click()
    await page.getByTestId('fin-profit-abnormal-from').fill('1999-01-01')
    await page.getByTestId('fin-profit-abnormal-query').click()
    await expect(page.getByTestId('fin-profit-abnormal-error')).toContainText('请同时填写开始日与结束日')
    await page.getByTestId('fin-profit-abnormal-from').fill('')
    await page.getByTestId('fin-profit-abnormal-platform').fill(`NO_SUCH_${stamp}`)
    const abnormalResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/abnormal') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-abnormal-query').click()
    await abnormalResp
    await expect(page.getByTestId('fin-profit-abnormal-empty')).toContainText('当前筛选下暂无偏离 2σ 的场次')
    await page.screenshot({ path: `${shotDir}/06-abnormal-empty.png`, fullPage: true })

    const resetResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/abnormal') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-profit-abnormal-reset').click()
    await resetResp
    const emptyAfter = page.getByTestId('fin-profit-abnormal-empty')
    if (await emptyAfter.count()) {
      await expect(emptyAfter).not.toContainText('当前筛选下')
    }

    expect(pageErrors).toEqual([])
  })
})
