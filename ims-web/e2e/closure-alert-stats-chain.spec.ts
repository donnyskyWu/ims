import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S11-04** 全状态链 + **E2E-S11-06** 统计总览（acceptance · **纯 UI** · #83）
 * Given: UI 新建并启用规则，热更新阈值
 * When: 试跑 → 确认 → 处理，再打开统计总览
 * Then: OPEN → CONFIRMED → RESOLVED；总览展示响应时长、响应率、解决率，且已解决数 +1
 */
const shotDir = '/opt/cursor/artifacts/e2e-83-screenshots'

type Overview = {
  totalAlertCount: number
  responseRate: number
  resolutionRate: number
  avgResponseMinutes: number
  resolvedCount: number
  respondedCount: number
  byLevel: { L1: number; L2: number; L3: number }
}

test.describe('alert stats and status chain closure S11', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('confirm then resolve, then stats overview shows rates', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.stats.${Date.now()}`

    await loginAdmin(page)

    const beforeResp = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/overview') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/alert/stats')
    await expect(page.locator('h1')).toContainText('预警统计')
    const beforeBody = (await (await beforeResp).json()) as { code: number; data: Overview }
    expect(beforeBody.code).toBe(0)
    const before = beforeBody.data

    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')
    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 统计 ${code}`)
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await ruleRow.getByTestId('alert-rule-edit').click()
    const edit = page.locator('.card').filter({ has: page.locator('h3', { hasText: '编辑预警规则' }) })
    await expect(edit.locator('input[placeholder="live.data.delay"]')).toHaveValue(code)
    await edit.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>5')
    await edit.getByRole('button', { name: '保存' }).click()
    await expect(page.locator('p.hint').filter({ hasText: '阈值已即时生效' })).toBeVisible({ timeout: 10_000 })
    await expect(ruleRow).toContainText('delayMinutes>5')
    await page.screenshot({ path: `${shotDir}/01-rule-hot-update.png`, fullPage: true })

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

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await liveRow.getByTestId('alert-confirm-btn').click()
    const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { responseStatus?: string } }
    expect(confirmBody.code).toBe(0)
    expect(confirmBody.data?.responseStatus).toBe('CONFIRMED')
    await expect(liveRow).toContainText('CONFIRMED')
    await expect(page.locator('p.hint').filter({ hasText: /已确认/ })).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-status-confirmed.png`, fullPage: true })

    const resolveResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await liveRow.getByTestId('alert-resolve-btn').click()
    const resolveBody = (await (await resolveResp).json()) as { code: number; data?: { responseStatus?: string } }
    expect(resolveBody.code).toBe(0)
    expect(resolveBody.data?.responseStatus).toBe('RESOLVED')
    await expect(liveRow).toContainText('RESOLVED')
    await page.screenshot({ path: `${shotDir}/03-status-resolved.png`, fullPage: true })

    const afterResp = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/overview') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('link', { name: '统计总览' }).click()
    await expect(page.locator('h1')).toContainText('预警统计')
    const afterBody = (await (await afterResp).json()) as { code: number; data: Overview }
    expect(afterBody.code).toBe(0)
    const after = afterBody.data
    expect(after.totalAlertCount).toBe(before.totalAlertCount + 1)
    expect(after.resolvedCount).toBe(before.resolvedCount + 1)
    expect(after.respondedCount).toBe(before.respondedCount + 1)
    await expect(page.getByTestId('alert-stats-total')).toHaveText(String(after.totalAlertCount))
    await expect(page.getByTestId('alert-stats-avg-minutes')).toHaveText(String(after.avgResponseMinutes))
    await expect(page.getByTestId('alert-stats-response-rate')).toHaveText(`${after.responseRate}%`)
    await expect(page.getByTestId('alert-stats-resolution-rate')).toHaveText(`${after.resolutionRate}%`)
    await expect(page.getByTestId('alert-stats-resolved-count')).toContainText(`已解决 ${after.resolvedCount}`)
    await expect(page.getByTestId('alert-stats-l1')).toContainText('L1')
    await expect(page.getByTestId('alert-stats-l2')).toContainText('L2')
    await expect(page.getByTestId('alert-stats-l3')).toContainText('L3')
    await page.screenshot({ path: `${shotDir}/04-stats-overview.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
