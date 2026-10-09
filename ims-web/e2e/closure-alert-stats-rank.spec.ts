import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #165 统计排行、合并筛选、空范围与通道本地桩（acceptance · 纯 UI）
 * Given: UI 新建启用规则并试跑两次
 * When: 统计页按规则看合并，再把日期收成没有预警的区间
 * Then: 两次试跑归成 30 分钟合并；空范围不把 0% 画成未达标；钉钉/短信显示不外发
 */
const shotDir = '/opt/cursor/artifacts/e2e-165-screenshots'

test.describe('alert stats rank merge channel closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('rank merge filter, empty range, and local channel stub', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.rank.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')
    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 排行 ${code}`)
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await ruleRow.getByRole('button', { name: '试跑' }).click()
    await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('link', { name: '统计总览' }).click()
    await expect(page.locator('h1')).toContainText('预警统计')
    const channel = page.getByTestId('alert-channel-stub')
    await expect(channel).toBeVisible()
    await expect(channel.getByTestId('alert-channel-DINGTALK')).toContainText('不外发')
    await expect(channel.getByTestId('alert-channel-SMS')).toContainText('不外发')
    await expect(channel.getByTestId('alert-channel-WORKBENCH')).toContainText('本地记录')

    await page.getByTestId('alert-stats-rule').fill(code)
    const alone = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/merge-logs') && r.url().includes(code) && r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    const aloneBody = (await (await alone).json()) as { code: number; data?: { total?: number } }
    expect(aloneBody.code).toBe(0)
    expect(aloneBody.data?.total).toBe(0)
    await expect(page.getByTestId('alert-stats-merge-empty')).toContainText('该规则在当前筛选下没有合并记录')
    await page.screenshot({ path: `${shotDir}/01-merge-filter-empty.png`, fullPage: true })

    await page.getByRole('link', { name: '预警规则' }).click()
    await page.locator('input[placeholder="规则名称"]').fill(code)
    await page.getByRole('button', { name: '查询' }).click()
    const again = page.locator('tbody tr').filter({ hasText: code })
    await expect(again).toBeVisible({ timeout: 15_000 })
    await again.getByRole('button', { name: '试跑' }).click()
    await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('link', { name: '统计总览' }).click()
    await page.getByTestId('alert-stats-rule').fill(code)
    const merged = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/merge-logs') && r.url().includes(code) && r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    const mergedBody = (await (await merged).json()) as {
      code: number
      data?: { total?: number; list?: Array<{ mergedCount?: number; mergeWindowMinutes?: number }> }
    }
    expect(mergedBody.code).toBe(0)
    expect(mergedBody.data?.total).toBe(1)
    expect(mergedBody.data?.list?.[0]?.mergedCount).toBe(2)
    expect(mergedBody.data?.list?.[0]?.mergeWindowMinutes).toBe(30)
    const mergeRow = page.getByTestId('alert-merge-row')
    await expect(mergeRow).toContainText(code)
    await expect(mergeRow).toContainText('30 分钟')
    await page.screenshot({ path: `${shotDir}/02-merge-window.png`, fullPage: true })

    await page.getByTestId('alert-stats-rule').fill('')
    await page.getByTestId('alert-stats-start').fill('1999-01-01')
    await page.getByTestId('alert-stats-end').fill('1999-01-02')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/overview') && r.url().includes('1999-01-01') && r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    const emptyBody = (await (await emptyResp).json()) as { code: number; data?: { totalAlertCount?: number } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.totalAlertCount).toBe(0)
    await expect(page.getByTestId('alert-stats-range-empty')).toContainText('当前筛选范围内暂无预警')
    await expect(page.getByTestId('alert-stats-rank-empty')).toContainText('当前筛选范围内没有规则命中')
    await expect(page.getByTestId('alert-stats-merge-empty')).toContainText('当前筛选下没有合并记录')
    await expect(page.getByTestId('alert-stats-false-hint')).toContainText('没有误报样本')
    await expect(page.getByTestId('alert-stats-response-rate')).toHaveAttribute('style', /inherit/)
    await expect(page.getByTestId('alert-channel-DINGTALK')).toContainText('不外发')
    await page.screenshot({ path: `${shotDir}/03-range-empty-channel.png`, fullPage: true })

    await page.goto('/ims/alert/live?tab=history')
    await expect(page.locator('h1')).toContainText('实时预警')
    await expect(page.locator('.tab.on')).toContainText('处置记录')
    await expect(page.getByTestId('alert-history-status')).not.toContainText('待响应')
    await page.screenshot({ path: `${shotDir}/04-history-status.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
