import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S11-切片**（acceptance · **纯 UI** · #44）
 * Given: UI 新建启用规则 → 试跑生成 OPEN 预警
 * When: `/ims/alert/live`「处理」→「处置记录」Tab →「去重合并」Tab
 * Then: 「处理」打开处置抽屉并进入处理中，再「标记恢复」到 RESOLVED；处置记录点编号打开时间线；去重策略表可见 DEDUP-LIVE
 */
test.describe('alert handle tab closure S11', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('trial alert then handle and history dedup tabs', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.handle.${Date.now()}`

    await loginAdmin(page)

    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 处置 ${code}`)
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

    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    await expect(liveRow).toContainText('未处理')

    await liveRow.getByRole('button', { name: '处理' }).click()
    const drawer = page.getByTestId('alert-handle-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('alert-handle-chain')).toContainText('30 分钟')
    await drawer.getByTestId('alert-handle-remark').fill('现场已核对')
    const handleResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await drawer.getByTestId('alert-handle-submit').click()
    const handleBody = (await (await handleResp).json()) as { code: number; data?: { responseStatus?: string } }
    expect(handleBody.code).toBe(0)
    expect(handleBody.data?.responseStatus).toBe('CONFIRMED')

    await expect(page.locator('p.hint').filter({ hasText: /处理中/ })).toBeVisible({ timeout: 10_000 })
    await expect(liveRow).toContainText('处理中')

    const recoverResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await liveRow.getByRole('button', { name: '标记恢复' }).click()
    const recoverBody = (await (await recoverResp).json()) as { code: number; data?: { responseStatus?: string } }
    expect(recoverBody.code).toBe(0)
    expect(recoverBody.data?.responseStatus).toBe('RESOLVED')
    await expect(liveRow).toContainText('已恢复')

    await page.locator('.tab', { hasText: '处置记录' }).click()
    await expect(page.locator('.g4 .stat').filter({ hasText: '已处置' }).locator('.n')).not.toHaveText('0', {
      timeout: 15_000,
    })

    const historyRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(historyRow).toBeVisible({ timeout: 15_000 })
    await expect(historyRow).toContainText('已恢复')
    await historyRow.getByTestId('alert-record-no').click()
    const timeline = page.getByTestId('alert-record-timeline')
    await expect(timeline).toBeVisible()
    await expect(timeline).toContainText('触发')
    await expect(timeline).toContainText('处置')
    await expect(timeline).toContainText('恢复')
    await timeline.getByRole('button', { name: '关闭' }).click()

    await page.locator('.tab', { hasText: '去重合并' }).click()
    await expect(page.locator('tbody tr').filter({ hasText: 'DEDUP-LIVE' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('tbody tr').filter({ hasText: 'DEDUP-COLLECT' })).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
