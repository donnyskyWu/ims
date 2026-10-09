import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'
fs.mkdirSync(shotDir, { recursive: true })

/**
 * #196 FIN 尾巴：分成规则空页/筛选空态、看板空月导出与过期提示、发放失败留在抽屉。
 */
test.describe('fin share export tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share rule empty page, empty export, and payoff error stay visible', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/fin/share/rule')
    await expect(page.locator('h1')).toHaveText('分成规则', { timeout: 15_000 })
    await expect(page.getByTestId('fin-share-rule-pager')).toBeVisible()

    const farResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rules') && r.url().includes('pageNo=999') && r.request().method() === 'GET',
    )
    await page.getByTestId('fin-share-rule-page').fill('999')
    await page.getByTestId('fin-share-rule-page-go').click()
    const farBody = (await (await farResp).json()) as { code: number; data?: { list?: unknown[]; total?: number } }
    expect(farBody.code).toBe(0)
    expect(farBody.data?.list || []).toEqual([])
    const farTotal = farBody.data?.total || 0
    await expect(page.getByTestId('fin-share-rule-empty')).toContainText(farTotal === 0 ? '暂无分成规则' : '本页无规则')
    await page.screenshot({ path: `${shotDir}/fin-196-share-rule-empty.png`, fullPage: true })

    const filterResp = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/share/rules') &&
        r.url().includes('shareTarget=TEAM') &&
        r.url().includes('status=DISABLED') &&
        r.request().method() === 'GET',
    )
    const filters = page.locator('form.qbar')
    await filters.locator('select').nth(0).selectOption('TEAM')
    await filters.locator('select').nth(1).selectOption('DISABLED')
    await page.getByTestId('fin-share-rule-query').click()
    const filterBody = (await (await filterResp).json()) as { code: number; data?: { total?: number } }
    expect(filterBody.code).toBe(0)
    if ((filterBody.data?.total || 0) === 0) {
      await expect(page.getByTestId('fin-share-rule-empty')).toContainText('无匹配规则')
      await page.screenshot({ path: `${shotDir}/fin-196-share-rule-filter-empty.png`, fullPage: true })
    }

    await page.route('**/fin/share/rules**', (route) => route.abort())
    await page.getByTestId('fin-share-rule-reset').click()
    await expect(page.getByTestId('fin-share-rule-empty')).toContainText('规则列表加载失败')
    await expect(page.getByTestId('fin-share-rule-retry')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/fin-196-share-rule-retry.png`, fullPage: true })
    await page.unroute('**/fin/share/rules**')
    const retryResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rules') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('fin-share-rule-retry').click()
    expect(((await (await retryResp).json()) as { code: number }).code).toBe(0)

    await page.goto('/ims/fin/dashboard')
    await expect(page.locator('h1')).toHaveText('利润看板', { timeout: 15_000 })
    await page.getByTestId('fin-dash-period').fill('1999-01')
    const overviewResp = page.waitForResponse(
      (r) => r.url().includes('/fin/dashboard/overview') && r.url().includes('statPeriod=1999-01') && r.status() === 200,
    )
    await page.getByTestId('fin-dash-query').click()
    await overviewResp
    await page.getByTestId('fin-dash-export').click()
    const dialog = page.getByTestId('fin-dash-export-dialog')
    await expect(dialog.getByTestId('fin-dash-export-ttl')).toContainText('60 秒')
    await expect(dialog.getByTestId('fin-dash-export-ttl')).toContainText('重新发起')
    await expect(dialog.getByTestId('fin-dash-export-scope')).toContainText('1999-01')
    await page.screenshot({ path: `${shotDir}/fin-196-export-empty-dialog.png`, fullPage: true })
    const exportResp = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/dashboard/export') &&
        !r.url().includes('/file') &&
        r.url().includes('statPeriod=1999-01') &&
        r.request().method() === 'GET',
    )
    await dialog.getByTestId('fin-dash-export-confirm').click()
    const exportBody = (await (await exportResp).json()) as {
      code: number
      data?: { empty?: boolean; fileName?: string; expiresIn?: number }
    }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.empty).toBe(true)
    expect(exportBody.data?.expiresIn).toBe(60)
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('导出成功')
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('已导出表头')
    await expect(page.getByTestId('fin-dash-export-msg')).toContainText('过期请重新发起')
    await page.screenshot({ path: `${shotDir}/fin-196-export-empty-done.png`, fullPage: true })

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)
    await page.goto('/ims/fin/share/result')
    await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    await page.getByRole('button', { name: '查询' }).click()
    const row = () => page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: '达人' }).first()
    await expect(row()).toContainText('待审', { timeout: 15_000 })
    const finPut = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const finList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await row().getByTestId('fin-share-audit-finance').click()
    expect(((await (await finPut).json()) as { code: number }).code).toBe(0)
    await finList
    const bizPut = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const bizList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await row().getByTestId('fin-share-audit-business').click()
    expect(((await (await bizPut).json()) as { code: number; data?: { status?: string } }).data?.status).toBe('AUDITED')
    await bizList
    await expect(row()).toContainText('已审', { timeout: 15_000 })
    await row().getByTestId('fin-share-payoff-open').click()
    const drawer = page.getByTestId('fin-share-payoff-drawer')
    await expect(drawer.getByTestId('fin-share-payoff-hint')).toContainText('256')
    await drawer.getByTestId('fin-share-payoff-note').fill('边界失败一次')
    await page.route('**/fin/share/result/**/payoff', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1001, msg: '发放备注不超过 256 字' }),
      }),
    )
    await drawer.getByTestId('fin-share-payoff-submit').click()
    await expect(drawer.getByTestId('fin-share-payoff-error')).toContainText('1001')
    await expect(drawer.getByTestId('fin-share-payoff-error')).toContainText('256')
    await expect(drawer).toBeVisible()
    await page.screenshot({ path: `${shotDir}/fin-196-payoff-error.png`, fullPage: true })
    await page.unroute('**/fin/share/result/**/payoff')
    await drawer.getByTestId('fin-share-payoff-voucher').setInputFiles({
      name: 'fin-196-voucher.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('fin-voucher'),
    })
    const payPut = page.waitForResponse(
      (r) => r.url().includes('/payoff') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const payList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await drawer.getByTestId('fin-share-payoff-submit').click()
    expect(((await (await payPut).json()) as { code: number }).code).toBe(0)
    await payList
    await expect(row()).toContainText('已发放', { timeout: 10_000 })
    await expect(row().getByTestId('fin-share-voucher-name')).toHaveText('fin-196-voucher.txt')
    await page.screenshot({ path: `${shotDir}/fin-196-payoff-done.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})