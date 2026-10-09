import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  loginAs,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/fin-207'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #207 FIN 尾巴：看板空月与非法周期、分成单加载失败、单边审等待文案、
 * 驳回进冲销、冲销原因必填、R9 分成金额脱敏。
 * 不覆盖规则 CRUD、导出链接过期、台账跳转空态。
 */
test.describe('fin share audit and empty tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('dashboard empties, share audit edges, and R9 mask', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/fin/dashboard')
    await expect(page.locator('h1')).toHaveText('利润看板', { timeout: 15_000 })
    await page.getByTestId('fin-dash-period').fill('2199-13')
    await page.getByTestId('fin-dash-query').click()
    await expect(page.getByTestId('fin-dash-error')).toContainText('统计周期须为 yyyy-MM')
    await expect(page.getByTestId('fin-dash-drill-empty')).toContainText('统计周期须为 yyyy-MM')
    await expect(page.getByTestId('fin-dash-cost-empty')).toContainText('统计周期须为 yyyy-MM')
    await page.screenshot({ path: `${shotDir}/01-period-invalid.png`, fullPage: true })

    const emptyOverview = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/overview') && r.url().includes('2199-11') && r.status() === 200,
    )
    await page.getByTestId('fin-dash-period').fill('2199-11')
    await page.getByTestId('fin-dash-query').click()
    await emptyOverview
    await expect(page.getByTestId('fin-dash-refreshed')).toContainText('数据截至')
    await expect(page.getByTestId('fin-dash-refreshed')).toContainText('缓存时间')
    await expect(page.getByTestId('fin-dash-cost-empty')).toContainText('本月无成本结构')
    await expect(page.getByTestId('fin-dash-share-empty')).toContainText('本月无分成')
    await expect(page.getByTestId('fin-dash-drill-empty')).toContainText('本月暂无已核算场次')
    await page.screenshot({ path: `${shotDir}/02-empty-month.png`, fullPage: true })

    await page.route('**/fin/share/results**', (route) => route.abort())
    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await expect(page.getByTestId('fin-share-empty')).toContainText('分成单加载失败', { timeout: 15_000 })
    await expect(page.getByTestId('fin-share-retry')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-share-load-fail.png`, fullPage: true })
    await page.unroute('**/fin/share/results**')

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E fin 207 ${Date.now()}`,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await page.getByTestId('fin-share-filter-session').fill(sessionCode)
    await page.getByTestId('fin-share-filter-target').selectOption('DAREN')
    const darenList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.url().includes('DAREN') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await darenList
    const darenRow = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' })
    await expect(darenRow).toBeVisible({ timeout: 15_000 })
    const finAudit = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await darenRow.getByTestId('fin-share-audit-finance').click()
    const finBody = (await (await finAudit).json()) as { code: number; data?: { bothPassed?: boolean } }
    expect(finBody.code).toBe(0)
    expect(finBody.data?.bothPassed).toBe(false)
    await expect(page.getByTestId('fin-share-audit-wait')).toContainText('等待另一角色审核后生效')
    await page.screenshot({ path: `${shotDir}/04-audit-wait.png`, fullPage: true })

    await page.getByTestId('fin-share-filter-target').selectOption('REALNAME')
    const realList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.url().includes('REALNAME') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await realList
    const realRow = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '实名人' })
    await realRow.getByTestId('fin-share-reject-open').click()
    await expect(page.getByTestId('fin-share-reject-hint')).toContainText('冲销通道')
    await page.getByTestId('fin-share-reject-remark').fill('口径不对')
    const rejectPut = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('fin-share-reject-submit').click()
    const rejectBody = (await (await rejectPut).json()) as { code: number }
    expect(rejectBody.code).toBe(0)
    await expect(page.getByTestId('fin-share-audit-wait')).toContainText('已驳回，进入冲销通道')
    await expect(realRow).toContainText('已冲销')
    await page.screenshot({ path: `${shotDir}/05-reject-reversed.png`, fullPage: true })

    await page.getByTestId('fin-share-filter-target').selectOption('DAREN')
    const darenAgain = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.url().includes('DAREN') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await darenAgain
    const audited = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' })
    const bizAudit = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await audited.getByTestId('fin-share-audit-business').click()
    expect(((await (await bizAudit).json()) as { code: number }).code).toBe(0)
    await expect(audited).toContainText('已审')
    await audited.getByTestId('fin-share-reverse-open').click()
    await page.getByTestId('fin-share-reverse-submit').click()
    await expect(page.getByTestId('fin-share-reverse-error')).toContainText('1144 冲销原因必填')
    await expect(page.getByTestId('fin-share-reverse-drawer')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/06-reverse-reason.png`, fullPage: true })

    await loginAs(page, 'e2e_fin_r9')
    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await page.getByTestId('fin-share-filter-session').fill(sessionCode)
    const maskedList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.status() === 200,
    )
    await page.getByTestId('fin-share-filter-query').click()
    await maskedList
    await expect(page.getByTestId('fin-share-amount-mask')).toContainText('金额已脱敏')
    await expect(page.getByTestId('fin-share-amount').first()).toHaveText('***')
    await page.screenshot({ path: `${shotDir}/07-r9-mask.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
