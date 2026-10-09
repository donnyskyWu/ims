import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #184 通道回执空态与本地桩（acceptance · 纯 UI）
 * Given: 统计页选一个没有预警的日期
 * When: 新建 L3 规则并试跑，打开回执
 * Then: 空范围显示通道空态且比率不标未达标；回执里钉钉为本地桩、短信未触发、文案标明不外发
 */
const shotDir = '/opt/cursor/artifacts/alert-184-screenshots'

test.describe('alert channel receipt empty and stub', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty range has no channel receipts, trial receipt stays local', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.rcpt.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/stats')
    await expect(page.locator('h1')).toContainText('预警统计')
    await page.getByTestId('alert-stats-start').fill('2098-01-01')
    await page.getByTestId('alert-stats-end').fill('2098-01-02')
    const emptyResp = page.waitForResponse(
      (r) =>
        r.url().includes('/alert/stats/overview') &&
        r.url().includes('dateRange=2098-01-01') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '刷新' }).click()
    const emptyBody = (await (await emptyResp).json()) as {
      code: number
      data: { totalAlertCount: number; channelReceipts: Array<{ empty: boolean; outbound: boolean }> }
    }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data.totalAlertCount).toBe(0)
    expect(emptyBody.data.channelReceipts.every((item) => item.empty && item.outbound === false)).toBe(true)
    await expect(page.getByTestId('alert-channel-empty')).toContainText('当前范围内暂无通道回执')
    await expect(page.getByTestId('alert-stats-response-rate')).toHaveAttribute('data-neutral', '1')
    await expect(page.getByTestId('alert-stats-delivery-rate')).toHaveAttribute('data-neutral', '1')
    await page.screenshot({ path: `${shotDir}/01-channel-empty.png` })

    await page.goto('/ims/alert/rule')
    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 回执 ${code}`)
    await modal.getByTestId('alert-rule-level').selectOption('3')
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await expect(ruleRow).toContainText('L3')

    const trialResp = page.waitForResponse(
      (r) => r.url().includes('/alert/rule/') && r.url().includes('/trial') && r.request().method() === 'POST',
    )
    await ruleRow.getByRole('button', { name: '试跑' }).click()
    const trialBody = (await (await trialResp).json()) as { code: number; data?: { alertNo?: string } }
    expect(trialBody.code).toBe(0)
    const alertNo = trialBody.data?.alertNo
    expect(alertNo).toBeTruthy()

    await page.goto('/ims/alert/live')
    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    const receiptResp = page.waitForResponse(
      (r) => r.url().includes(`/alert/check/${alertNo}`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await liveRow.getByTestId('alert-receipt-btn').click()
    const receiptBody = (await (await receiptResp).json()) as {
      code: number
      data: {
        priorityNote: string
        pushChannels: Array<{ channel: string; outbound: boolean; empty?: boolean; stub?: boolean; success: boolean }>
      }
    }
    expect(receiptBody.code).toBe(0)
    expect(receiptBody.data.priorityNote).toContain('ALR-P-R1')
    expect(receiptBody.data.pushChannels.every((item) => item.outbound === false)).toBe(true)
    const drawer = page.getByTestId('alert-receipt-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('不外发')
    await expect(drawer).toContainText('ALR-P-R1')
    const sms = drawer.locator('[data-channel="SMS"]')
    await expect(sms).toContainText('未触发')
    const ding = drawer.locator('[data-channel="DINGTALK"]')
    await expect(ding).toContainText('钉钉')
    await expect(ding).toContainText('✓')
    await page.screenshot({ path: `${shotDir}/02-receipt-stub.png` })

    await page.getByTestId('alert-receipt-close').click()
    await expect(drawer).toHaveCount(0)

    expect(pageErrors).toEqual([])
  })
})
