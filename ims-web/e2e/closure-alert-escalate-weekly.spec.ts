import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #141 本地尾巴：命中统计弹窗、周报、升级中心 30 秒轮询。
 * 钉钉/短信保持页面桩文案，不要求真实外发。
 */
const shotDir = '/opt/cursor/artifacts/e2e-141-screenshots'

test.describe('alert hit-stats weekly escalate closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('hit stats modal, weekly report, and 30s escalate poll', async ({ page }) => {
    test.setTimeout(120_000)
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.tail.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')
    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 升级 ${code}`)
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

    const hitResp = page.waitForResponse(
      (r) => r.url().includes('/alert/rule/hit-stats') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('alert-hit-open').click()
    const hitBody = (await (await hitResp).json()) as {
      code: number
      data: Array<{ ruleCode: string; alertCount: number; falseAlarmCount: number }>
    }
    expect(hitBody.code).toBe(0)
    const hit = hitBody.data.find((row) => row.ruleCode === code)
    expect(hit?.alertCount).toBeGreaterThanOrEqual(1)
    const hitRow = page.getByTestId('alert-hit-row').filter({ hasText: code })
    await expect(hitRow).toBeVisible()
    await expect(hitRow.getByTestId('alert-hit-count')).toHaveText(String(hit?.alertCount))
    await expect(hitRow.getByTestId('alert-hit-false-mark')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/01-hit-stats-modal.png`, fullPage: true })
    await page.locator('[data-testid="alert-hit-modal"]').getByRole('button', { name: '关闭' }).click()

    const weeklyResp = page.waitForResponse(
      (r) => r.url().includes('/alert/stats/weekly-report') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/alert/stats')
    await expect(page.locator('h1')).toContainText('预警统计')
    const weeklyBody = (await (await weeklyResp).json()) as {
      code: number
      data: { totalAlerts: number; weekRange: string[]; suggestions: string[]; topRules: Array<{ ruleCode: string }> }
    }
    expect(weeklyBody.code).toBe(0)
    expect(weeklyBody.data.totalAlerts).toBeGreaterThanOrEqual(1)
    expect(weeklyBody.data.weekRange).toHaveLength(2)
    expect(weeklyBody.data.suggestions.join(' ')).toContain('本地桩')
    await expect(page.getByTestId('alert-weekly-total')).toHaveText(String(weeklyBody.data.totalAlerts))
    await expect(page.getByTestId('alert-weekly-suggestions')).toContainText('本地桩')
    const listedTop = weeklyBody.data.topRules.some((row) => row.ruleCode === code)
    if (listedTop) {
      await expect(page.getByTestId('alert-weekly-top').filter({ hasText: code })).toBeVisible()
    } else {
      expect(weeklyBody.data.topRules.length).toBeGreaterThan(0)
      await expect(page.getByTestId('alert-weekly-top').first()).toBeVisible()
    }
    await page.screenshot({ path: `${shotDir}/02-weekly-report.png`, fullPage: true })

    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await page.getByTestId('alert-escalate-l1').fill('30')
    await page.getByTestId('alert-escalate-l2').fill('60')
    await page.getByTestId('alert-escalate-severe').selectOption('2')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/config') && r.request().method() === 'PUT',
    )
    await page.getByTestId('alert-escalate-save').click()
    expect((await (await saveResp).json()).code).toBe(0)

    await page.clock.install()
    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/pending') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await pendingResp
    const escRow = page.getByTestId('alert-escalate-row').filter({ hasText: alertNo! })
    await expect(escRow).toBeVisible({ timeout: 15_000 })
    await expect(escRow.getByTestId('alert-escalate-next')).toContainText('min')
    await expect(page.getByTestId('alert-escalate-poll-state')).toContainText('30 秒轮询中')
    await expect(page.getByTestId('alert-escalate-channel-stub')).toContainText('本地桩')
    await escRow.getByTestId('alert-escalate-detail').click()
    const timeline = page.locator('aside.drawer.on')
    await expect(timeline.getByTestId('alert-escalate-node').first()).toContainText('责任人')
    await expect(timeline).toContainText('本地桩')
    await page.screenshot({ path: `${shotDir}/03-escalate-timeline.png`, fullPage: true })
    await timeline.getByRole('button', { name: '关闭' }).click()

    const polled = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/pending') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.clock.fastForward(30_000)
    await polled
    await expect(escRow).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-escalate-polled.png`, fullPage: true })

    await page.route('**/alert/escalate/pending**', (route) => route.abort())
    await page.clock.fastForward(30_000)
    await page.clock.fastForward(30_000)
    await page.clock.fastForward(30_000)
    await expect(page.getByTestId('alert-escalate-poll-hint')).toContainText('连续刷新失败，请手动刷新')
    await page.screenshot({ path: `${shotDir}/05-escalate-poll-failed.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
