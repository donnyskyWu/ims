import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #205 预警本地尾巴：规则级别筛选与重置、命中日期清空、
 * 送达率空范围、回执状态文案、统计级别跳转、升级统计空样本与级别重置。
 * 不重做 #151 记录筛选，也不重建 #165/#184 的排行与通道回执。
 */
const shotDir = '/opt/cursor/artifacts/alert-205-screenshots'

test.describe('alert local tails #205', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('rule level reset, empty delivery, and escalate sample edge', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.205.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 205 ${code}`)
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
    const alertNo = trialBody.data?.alertNo || ''
    expect(alertNo).toBeTruthy()

    const ruleFilter = page.getByTestId('alert-rule-filter')
    await ruleFilter.getByTestId('alert-rule-filter-name').fill(code)
    await ruleFilter.getByTestId('alert-rule-filter-level').selectOption('L1')
    const emptyRule = page.waitForResponse(
      (r) => r.url().includes('/alert/rule/list') && r.request().method() === 'GET',
    )
    await ruleFilter.getByRole('button', { name: '查询' }).click()
    expect((await (await emptyRule).json()).code).toBe(0)
    await expect(page.getByTestId('alert-rule-empty')).toContainText('当前筛选条件下暂无规则')
    await page.screenshot({ path: `${shotDir}/01-rule-filter-empty.png`, fullPage: true })

    await ruleFilter.getByTestId('alert-rule-filter-reset').click()
    await expect(ruleFilter.getByTestId('alert-rule-filter-level')).toHaveValue('')
    await expect(ruleRow).toBeVisible()

    await ruleFilter.getByTestId('alert-rule-filter-name').fill(code)
    await ruleFilter.getByTestId('alert-rule-filter-level').selectOption('L2')
    await ruleFilter.getByRole('button', { name: '查询' }).click()
    await expect(ruleRow).toBeVisible()
    await expect(ruleRow).toContainText('L2')

    await page.getByTestId('alert-hit-open').click()
    const hit = page.getByTestId('alert-hit-modal')
    await hit.getByTestId('alert-hit-start').fill('2099-01-01')
    await hit.getByTestId('alert-hit-end').fill('2099-01-02')
    await hit.getByRole('button', { name: '查询' }).click()
    await expect(hit).toContainText('该范围内暂无命中')
    await hit.getByTestId('alert-hit-reset').click()
    await expect(hit.getByTestId('alert-hit-start')).toHaveValue('')
    await expect(hit.getByTestId('alert-hit-end')).toHaveValue('')
    await expect(hit).toContainText(code)
    await page.screenshot({ path: `${shotDir}/02-hit-reset.png` })
    await hit.getByRole('button', { name: '关闭' }).click()

    await page.goto('/ims/alert/live')
    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    await liveRow.getByTestId('alert-detail-btn').click()
    const drawer = page.getByTestId('alert-receipt-drawer')
    await expect(drawer.getByTestId('alert-receipt-status')).toContainText('未响应（OPEN）')
    await expect(drawer.getByTestId('alert-receipt-source')).toContainText('查看来源')
    await page.screenshot({ path: `${shotDir}/03-receipt-status.png` })
    await drawer.getByTestId('alert-receipt-close').click()

    await page.getByTestId('alert-delivery-from').fill('2099-01-01')
    await page.getByTestId('alert-delivery-to').fill('2099-01-02')
    const deliveryResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/delivery-stats') && r.request().method() === 'GET',
    )
    await page.getByTestId('alert-delivery-apply').click()
    const deliveryBody = (await (await deliveryResp).json()) as { code: number; data?: { totalShould?: number } }
    expect(deliveryBody.code).toBe(0)
    expect(deliveryBody.data?.totalShould).toBe(0)
    await expect(page.getByTestId('alert-delivery-empty')).toContainText('不记未达标')
    await expect(page.getByTestId('alert-delivery-short')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/04-delivery-empty.png`, fullPage: true })
    await page.getByTestId('alert-delivery-reset').click()
    await expect(page.getByTestId('alert-delivery-empty')).toHaveCount(0)

    await page.goto('/ims/alert/stats')
    await expect(page.getByTestId('alert-stats-level-L3')).toBeVisible()
    await page.getByTestId('alert-stats-level-L3').click()
    await expect(page).toHaveURL(/level=L3/)
    await expect(page.getByTestId('alert-filter-level')).toHaveValue('L3')
    await expect(page.locator('tbody tr').filter({ hasText: alertNo })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/05-stats-level-jump.png`, fullPage: true })

    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await page.getByTestId('alert-escalate-stats-from').fill('2099-01-01')
    await page.getByTestId('alert-escalate-stats-to').fill('2099-01-02')
    const statsResp = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/response-stats') && r.request().method() === 'GET',
    )
    await page.getByTestId('alert-escalate-stats-apply').click()
    const statsBody = (await (await statsResp).json()) as { code: number; data?: { totalAlerts?: number } }
    expect(statsBody.code).toBe(0)
    expect(statsBody.data?.totalAlerts).toBe(0)
    await expect(page.getByTestId('alert-escalate-rate-hint')).toContainText('当前没有预警样本，不记未达标')
    await expect(page.getByTestId('alert-escalate-trend-empty')).toContainText('暂无趋势')
    await page.screenshot({ path: `${shotDir}/06-escalate-empty-range.png`, fullPage: true })
    await page.getByTestId('alert-escalate-stats-reset').click()
    await expect(page.getByTestId('alert-escalate-stats-from')).toHaveValue('')
    await expect(page.getByTestId('alert-escalate-rate-hint')).not.toContainText('不记未达标')

    const pending = page.getByTestId(`alert-escalate-row-${alertNo}`)
    await expect(pending).toBeVisible({ timeout: 15_000 })
    const current = await pending.getByTestId('alert-escalate-current').innerText()
    const other = current.includes('三级') ? '1' : '3'
    await page.getByTestId('alert-escalate-level').selectOption(other)
    await expect(pending).toBeHidden()
    if (await page.getByTestId('alert-escalate-empty').count()) {
      await expect(page.getByTestId('alert-escalate-empty')).toContainText('当前级别暂无待升级预警')
      await page.screenshot({ path: `${shotDir}/07-escalate-level-empty.png`, fullPage: true })
    }
    await page.getByTestId('alert-escalate-level-reset').click()
    await expect(page.getByTestId('alert-escalate-level')).toHaveValue('')
    await expect(pending).toBeVisible()
    await page.screenshot({ path: `${shotDir}/08-escalate-level-reset.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
