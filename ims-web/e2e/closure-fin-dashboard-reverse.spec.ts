import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  approveAndPayoffFinSharesViaUi,
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-90-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #90 FIN-004 利润看板 + 分成负向冲销（纯 UI）
 * 复用 LIVE→成本核准→双审发放，再对达人分成红冲，并按 2026-10 / 账号下钻到本场次。
 */
test.describe('fin dashboard and share reverse closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('dashboard drills the month by account and payoff reverse writes a red entry', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)
    await approveAndPayoffFinSharesViaUi(page, sessionCode)

    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp

    const daren = page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' }).first()
    await expect(daren).toContainText('已发放')
    await daren.getByTestId('fin-share-reverse-open').click()
    const drawer = page.getByTestId('fin-share-reverse-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('fin-share-reverse-reason').fill('发放金额有误')
    const reversePut = page.waitForResponse(
      (r) =>
        r.url().includes('/payoff') &&
        r.request().method() === 'PUT' &&
        (r.request().postData() || '').includes('"reverse":true'),
    )
    await drawer.getByTestId('fin-share-reverse-submit').click()
    const reverseBody = (await (await reversePut).json()) as {
      code: number
      data?: { status?: string; redEntries?: Array<{ amount?: number }> }
    }
    expect(reverseBody.code).toBe(0)
    expect(reverseBody.data?.status).toBe('REVERSED')
    expect(reverseBody.data?.redEntries?.[0]?.amount).toBe(-3000)
    await expect(drawer.getByTestId('fin-share-red-amount')).toContainText('3,000.00')
    await expect(drawer.getByTestId('fin-share-reverse-audit')).toContainText('发放金额有误')
    await page.screenshot({ path: `${shotDir}/01-share-red-entry.png`, fullPage: true })

    const again = page.waitForResponse(
      (r) =>
        r.url().includes('/payoff') &&
        r.request().method() === 'PUT' &&
        (r.request().postData() || '').includes('"reverse":true'),
    )
    await drawer.getByTestId('fin-share-reverse-submit').click()
    const againBody = (await (await again).json()) as { code: number; msg?: string }
    expect(againBody.code).toBe(1150)
    await expect(drawer.getByTestId('fin-share-reverse-error')).toContainText('1150')
    await expect(drawer.getByTestId('fin-share-reverse-error')).toContainText('已冲销')
    await page.screenshot({ path: `${shotDir}/02-reverse-error-1150.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()

    await expect(daren).toContainText('已冲销')
    await daren.getByTestId('fin-share-reverse-detail-open').click()
    const detail = page.getByTestId('fin-share-reverse-detail')
    await expect(detail).toContainText('3,000.00')
    await expect(detail.getByTestId('fin-share-reverse-detail-audit')).toContainText('发放金额有误')
    await page.screenshot({ path: `${shotDir}/03-reverse-detail.png`, fullPage: true })

    await page.goto('/ims/fin/dashboard')
    await expect(page.locator('h1')).toHaveText('利润看板', { timeout: 15_000 })
    await page.getByTestId('fin-dash-period').fill('2026-10')
    const overviewResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/overview') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-dash-query').click()
    await overviewResp
    await expect(page.getByTestId('fin-dash-refreshed')).toContainText('缓存时间')
    await expect(page.getByTestId('fin-dash-gmv')).toBeVisible()

    const accountRow = page.locator('[data-testid="fin-dash-drill"] tbody tr', { hasText: 'AC-E2E-FIN' }).first()
    await expect(accountRow).toBeVisible({ timeout: 15_000 })
    await accountRow.getByTestId('fin-dash-expand').click()
    const sessionRow = page.locator('[data-testid="fin-dash-session"]', { hasText: sessionCode })
    await expect(sessionRow).toContainText('81,400.00')
    await expect(sessionRow).toContainText('100,000.00')
    await expect(page.getByTestId('fin-dash-cost-structure')).toContainText('投放成本')
    await expect(page.getByTestId('fin-dash-trend')).toContainText('2026-10')
    await page.screenshot({ path: `${shotDir}/04-dashboard-account-drill.png`, fullPage: true })

    await page.getByTestId('fin-dash-dim-OWNER').click()
    await expect(page.getByTestId('fin-dash-drill')).toContainText('责任人')
    const ownerRow = page.locator('[data-testid="fin-dash-drill"] tbody tr', { hasText: '责任人' }).first()
    await ownerRow.getByTestId('fin-dash-expand').click()
    await expect(page.locator('[data-testid="fin-dash-session"]', { hasText: sessionCode })).toContainText('81,400.00')
    await page.screenshot({ path: `${shotDir}/05-dashboard-owner-drill.png`, fullPage: true })

    await page.getByTestId('fin-dash-export').click()
    const exportDialog = page.getByTestId('fin-dash-export-dialog')
    await expect(exportDialog).toBeVisible()
    await expect(exportDialog.getByTestId('fin-dash-export-scope')).toContainText('2026-10')
    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await exportDialog.getByTestId('fin-dash-export-confirm').click()
    const exportBody = (await (await exportResp).json()) as { code: number }
    expect(exportBody.code).toBe(0)
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('导出成功')
    await page.screenshot({ path: `${shotDir}/06-dashboard-export.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
