import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #218 预警列表筛选空态、级别筛选与回执边角文案（acceptance · 纯 UI）
 * Given: UI 新建 L1 / L3 规则并试跑
 * When: 按级别筛规则，从排行跳进实时列表，再把日期拨到无样本区间
 * Then: 筛选空态、送达样本空态、严重级回执说明可见；通道桩仍不外发
 */
const shotDir = '/opt/cursor/artifacts'

test.describe('alert local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('rule level filter, list empty, delivery sample, and L3 receipt copy', async ({ page }) => {
    test.setTimeout(120_000)
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const suffix = Date.now()
    const codeL1 = `e2e.alert.tail.l1.${suffix}`
    const codeL3 = `e2e.alert.tail.l3.${suffix}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    async function createRule(code: string, level: string) {
      await page.getByRole('button', { name: '新建规则' }).click()
      const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
      await modal.locator('input[placeholder="live.data.delay"]').fill(code)
      await modal.locator('input.fld-in').nth(1).fill(`E2E 边角 ${code}`)
      await modal.getByTestId('alert-rule-form-level').selectOption(level)
      await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
      await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
      await modal.getByRole('button', { name: '保存' }).click()
      await expect(modal).toBeHidden({ timeout: 15_000 })
    }

    await createRule(codeL1, '1')
    await page.getByTestId('alert-rule-filter-name').fill(`E2E 边角 ${codeL1}`)
    await page.getByTestId('alert-rule-filter-level').selectOption('L3')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('alert-rule-empty')).toContainText('当前筛选下暂无规则')
    await page.screenshot({ path: `${shotDir}/alert-218-rule-filter-empty.png`, fullPage: true })

    await page.getByTestId('alert-rule-filter-reset').click()
    await page.getByTestId('alert-rule-filter-name').fill(codeL1)
    await page.getByTestId('alert-rule-filter-level').selectOption('L1')
    await page.getByRole('button', { name: '查询' }).click()
    const ruleRow = page.locator('tbody tr').filter({ hasText: codeL1 })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await expect(ruleRow).toContainText('L1')
    await ruleRow.getByRole('button', { name: '试跑' }).click()
    await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('link', { name: '统计总览' }).click()
    await expect(page.locator('h1')).toContainText('预警统计')
    await expect(page.getByTestId('alert-stats-l3-link')).toBeVisible()
    await page.getByTestId('alert-stats-level-L3').click()
    await expect(page.locator('h1')).toContainText('实时预警')
    await expect(page.getByTestId('alert-filter-level')).toHaveValue('L3')
    await page.getByRole('link', { name: '统计总览' }).click()
    await expect(page.locator('h1')).toContainText('预警统计')
    const ownRank = page.getByTestId('alert-rank-link').filter({ hasText: codeL1 })
    if (await ownRank.count()) {
      await ownRank.click()
      await expect(page.getByTestId('alert-filter-rule')).toHaveValue(codeL1)
    } else {
      const anyRank = page.getByTestId('alert-rank-link').first()
      await expect(anyRank).toBeVisible()
      const rankedCode = (await anyRank.innerText()).trim()
      await anyRank.click()
      await expect(page.getByTestId('alert-filter-rule')).toHaveValue(rankedCode)
    }
    await expect(page.locator('h1')).toContainText('实时预警')

    await page.getByTestId('alert-filter-reset').click()
    await page.getByTestId('alert-filter-rule').fill(codeL1)
    await page.getByTestId('alert-filter-level').selectOption('L1')
    await page.getByRole('button', { name: '查询' }).click()
    const liveRow = page.locator('tbody tr').filter({ hasText: codeL1 })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    await expect(liveRow).toContainText('OPEN')
    await expect(liveRow).toContainText('未响应')

    await page.getByTestId('alert-filter-level').selectOption('L3')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('alert-list-empty')).toContainText('当前筛选下暂无预警')
    await page.screenshot({ path: `${shotDir}/alert-218-list-filter-empty.png`, fullPage: true })

    await page.getByTestId('alert-filter-reset').click()
    await page.getByTestId('alert-filter-from').fill('2099-01-01')
    await page.getByTestId('alert-filter-to').fill('2099-01-02')
    const emptyDelivery = page.waitForResponse(
      (r) => r.url().includes('/alert/check/delivery-stats') && r.url().includes('2099-01-01') && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const deliveryBody = (await (await emptyDelivery).json()) as { code: number; data?: { totalShould?: number } }
    expect(deliveryBody.code).toBe(0)
    expect(deliveryBody.data?.totalShould).toBe(0)
    await expect(page.getByTestId('alert-list-empty')).toContainText('当前筛选下暂无预警')
    await expect(page.getByTestId('alert-delivery-empty')).toContainText('当前没有送达样本')
    await expect(page.getByTestId('alert-delivery-rate')).toHaveAttribute('data-neutral', '1')
    await expect(page.getByTestId('alert-delivery-miss')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/alert-218-delivery-empty.png`, fullPage: true })

    await page.getByTestId('alert-filter-from').fill('2099-03-02')
    await page.getByTestId('alert-filter-to').fill('2099-03-01')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByText('起始日期不能晚于结束日期')).toBeVisible()

    await page.goto('/ims/alert/rule')
    await createRule(codeL3, '3')
    await page.getByTestId('alert-rule-filter-name').fill(codeL3)
    await page.getByTestId('alert-rule-filter-level').selectOption('L3')
    await page.getByRole('button', { name: '查询' }).click()
    const severeRow = page.locator('tbody tr').filter({ hasText: codeL3 })
    await expect(severeRow).toBeVisible({ timeout: 15_000 })
    await severeRow.getByRole('button', { name: '试跑' }).click()
    await expect(page.locator('p.hint').filter({ hasText: /试跑成功/ })).toBeVisible({ timeout: 15_000 })

    await page.getByRole('link', { name: '实时预警' }).click()
    await page.getByTestId('alert-filter-rule').fill(codeL3)
    await page.getByTestId('alert-filter-level').selectOption('L3')
    await page.getByRole('button', { name: '查询' }).click()
    const severeLive = page.locator('tbody tr').filter({ hasText: codeL3 })
    await expect(severeLive).toBeVisible({ timeout: 15_000 })
    await severeLive.getByTestId('alert-detail-btn').click()
    const drawer = page.getByTestId('alert-receipt-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('alert-receipt-priority')).toContainText('ALR-P-R1')
    await expect(drawer.getByTestId('alert-receipt-priority')).toContainText('不外发')
    await expect(drawer.getByTestId('alert-receipt-row').filter({ hasText: '钉钉' })).toContainText('✓')
    await expect(drawer.getByTestId('alert-receipt-row').filter({ hasText: '短信' })).toContainText('✗')
    await page.screenshot({ path: `${shotDir}/alert-218-receipt-l3.png` })
    await drawer.getByTestId('alert-receipt-close').click()

    await page.locator('.tab', { hasText: '去重合并' }).click()
    await expect(page.getByTestId('alert-dedup-filter')).toBeVisible()
    await page.getByTestId('alert-dedup-keyword').fill('DEDUP-NO-SUCH')
    await expect(page.getByTestId('alert-dedup-empty')).toContainText('当前筛选下暂无去重策略')
    await page.screenshot({ path: `${shotDir}/alert-218-dedup-filter-empty.png`, fullPage: true })
    await page.getByTestId('alert-dedup-reset').click()
    await expect(page.locator('tbody tr').filter({ hasText: 'DEDUP-LIVE' })).toBeVisible()

    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await page.getByTestId('alert-escalate-level').selectOption('1')
    const pending = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/pending') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form').filter({ has: page.getByTestId('alert-escalate-level') }).getByRole('button', { name: '刷新' }).click()
    await pending
    const escalateEmpty = page.getByTestId('alert-escalate-empty')
    if (await escalateEmpty.count()) {
      await expect(escalateEmpty).toContainText('该级别暂无待升级预警')
    } else {
      await expect(page.getByTestId('alert-escalate-current').first()).toContainText('一级')
    }
    await page.screenshot({ path: `${shotDir}/alert-218-escalate-level.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
