import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #151 实时预警筛选、推送回执与统计空态（acceptance · 纯 UI）
 * Given: UI 新建启用规则并试跑
 * When: 按规则编码筛选，打开回执抽屉，再把统计日期拨到无数据区间
 * Then: 列表只剩该预警且回执含工作台/钉钉桩；统计出现空态与周报未生成
 */
const shotDir = '/opt/cursor/artifacts'

test.describe('alert receipt filter closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter trial alert and open local push receipt', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.receipt.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 回执 ${code}`)
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    const trialResp = page.waitForResponse(
      (r) => r.url().includes('/alert/rule/') && r.url().includes('/trial') && r.request().method() === 'POST',
    )
    await ruleRow.getByRole('button', { name: '试跑' }).click()
    const trialBody = (await (await trialResp).json()) as { code: number; data?: { alertNo?: string } }
    expect(trialBody.code).toBe(0)
    const alertNo = trialBody.data?.alertNo
    expect(alertNo).toBeTruthy()

    await page.getByRole('link', { name: '实时预警' }).click()
    await expect(page.locator('h1')).toContainText('实时预警')
    await expect(page.getByTestId('alert-my-card')).toBeVisible()

    await page.getByTestId('alert-filter-rule').fill(code)
    await page.getByTestId('alert-filter-level').selectOption('L2')
    await page.getByTestId('alert-filter-push').selectOption('DELIVERED')
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/records') && r.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    const listBody = (await (await listResp).json()) as { code: number; data?: { list?: { alertNo: string }[] } }
    expect(listBody.code).toBe(0)
    expect(listBody.data?.list?.map((row) => row.alertNo)).toEqual([alertNo])

    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(liveRow).toBeVisible()
    await expect(liveRow).toContainText('已送达')
    await expect(liveRow).toContainText('工作台✓')
    await expect(liveRow).toContainText('钉钉✓')
    await expect(page.getByTestId('alert-my-item').filter({ hasText: alertNo! })).toBeVisible()

    await liveRow.getByTestId('alert-detail-btn').click()
    const drawer = page.getByTestId('alert-receipt-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('工作台')
    await expect(drawer).toContainText('钉钉')
    await expect(drawer).toContainText('短信')
    await expect(drawer).toContainText('本地回执桩，未实际外发')
    await expect(drawer.getByTestId('alert-receipt-row').filter({ hasText: '工作台' })).toContainText('✓')
    await expect(drawer.getByTestId('alert-receipt-row').filter({ hasText: '钉钉' })).toContainText('✓')
    await expect(drawer.getByTestId('alert-receipt-row').filter({ hasText: '短信' })).toContainText('✗')
    await page.screenshot({ path: `${shotDir}/alert-receipt-drawer.png` })

    await drawer.getByTestId('alert-receipt-close').click()
    await expect(drawer).toBeHidden()
    await page.getByTestId('alert-filter-rule').fill(`${code}.missing`)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('alert-list-empty')).toContainText('暂无预警')
    await page.screenshot({ path: `${shotDir}/alert-filter-empty.png`, fullPage: true })

    await page.goto('/ims/alert/stats')
    await expect(page.locator('h1')).toContainText('预警统计')
    await page.getByTestId('alert-stats-start').fill('2099-01-01')
    await page.getByTestId('alert-stats-end').fill('2099-01-02')
    const emptyResp = page.waitForResponse(
      (r) =>
        r.url().includes('/alert/stats/overview') &&
        r.url().includes('dateRange=2099-01-01') &&
        r.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '刷新' }).click()
    const emptyBody = (await (await emptyResp).json()) as { code: number; data?: { totalAlertCount?: number } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.totalAlertCount).toBe(0)
    await expect(page.getByTestId('alert-stats-empty')).toContainText('当前筛选范围内暂无预警')
    await expect(page.getByTestId('alert-stats-weekly-empty')).toContainText('本周期周报尚未生成')
    await page.screenshot({ path: `${shotDir}/alert-stats-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
