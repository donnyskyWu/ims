import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S11-切片**（acceptance · **纯 UI** · #44）
 * Given: UI 新建启用规则 → 试跑生成 OPEN 预警
 * When: `/ims/alert/live`「处理」→「处置记录」Tab →「去重合并」Tab
 * Then: toast 处置成功 · 处置记录含 RESOLVED · 去重策略表可见 DEDUP-LIVE
 * 状态已对齐契约：直接「处理」仍从 OPEN 到 RESOLVED（旧试跑→处理闭环）
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
    await expect(liveRow).toContainText('OPEN')

    const handleResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await liveRow.getByRole('button', { name: '处理' }).click()
    const handleBody = (await (await handleResp).json()) as { code: number; data?: { responseStatus?: string } }
    expect(handleBody.code).toBe(0)
    expect(handleBody.data?.responseStatus).toBe('RESOLVED')

    await expect(page.locator('p.hint').filter({ hasText: /处置成功/ })).toBeVisible({ timeout: 10_000 })
    await expect(liveRow).toContainText('RESOLVED')

    await page.locator('.tab', { hasText: '处置记录' }).click()
    await expect(page.locator('.g4 .stat').filter({ hasText: '已处置' }).locator('.n')).not.toHaveText('0', {
      timeout: 15_000,
    })

    const historyRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(historyRow).toBeVisible({ timeout: 15_000 })
    await expect(historyRow).toContainText('RESOLVED')

    await page.locator('.tab', { hasText: '去重合并' }).click()
    await expect(page.locator('tbody tr').filter({ hasText: 'DEDUP-LIVE' })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('tbody tr').filter({ hasText: 'DEDUP-COLLECT' })).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
