import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S11-01** 剩余 + **E2E-S11-05** 切片（acceptance · **纯 UI** · #81）
 * Given: 规则表单可填 JSON DSL / 阈值表达式
 * When: 非法操作符保存、同编码再保存、启用规则试跑后点「误报」再点一次
 * Then: 红字 **1009**、编码红字 **1165**、状态 **FALSE_ALARM**、再响应 toast **1167**
 */
const shotDir = '/opt/cursor/artifacts/e2e-81-screenshots'

test.describe('alert rule guard and false alarm closure S11', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('illegal DSL 1009 and duplicate rule code 1165', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.guard.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 拦截 ${code}`)
    await modal.getByTestId('alert-dsl-source').fill('ims_fin_cost')
    await modal.getByTestId('alert-dsl-field').fill('hours_since_approve')
    await modal.getByTestId('alert-dsl-op').fill('BAD')
    await modal.getByTestId('alert-dsl-value').fill('48')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('alert-dsl-error')).toContainText('1009')
    await page.screenshot({ path: `${shotDir}/01-dsl-1009.png`, fullPage: true })

    await modal.getByTestId('alert-dsl-op').fill('GT')
    await modal.getByRole('button', { name: '保存' }).click()
    const row = page.locator('tbody tr').filter({ hasText: code })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('ims_fin_cost.hours_since_approve GT 48')

    await page.getByRole('button', { name: '新建规则' }).click()
    const again = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await again.locator('input[placeholder="live.data.delay"]').fill(code)
    await again.locator('input.fld-in').nth(1).fill(`E2E 重复 ${code}`)
    await again.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>1')
    await again.getByRole('button', { name: '保存' }).click()
    await expect(again.getByTestId('alert-rule-code-error')).toContainText('1165')
    await page.screenshot({ path: `${shotDir}/02-dup-1165.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('false alarm close then repeat respond 1167', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.false.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.locator('input.fld-in').nth(1).fill(`E2E 误报 ${code}`)
    await modal.locator('input[placeholder="delayMinutes>30"]').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await ruleRow.getByRole('button', { name: '试跑' }).click()
    const trialHint = page.locator('p.hint').filter({ hasText: /试跑成功/ })
    await expect(trialHint).toBeVisible({ timeout: 15_000 })
    const alertNo = ((await trialHint.innerText()) || '').match(/AL\d+/)?.[0]
    expect(alertNo).toBeTruthy()

    await page.getByRole('link', { name: '实时预警' }).click()
    await expect(page.locator('h1')).toContainText('实时预警')
    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    await expect(liveRow).toContainText('OPEN')
    await liveRow.getByTestId('alert-false-alarm-btn').click()
    const falseModal = page.getByTestId('alert-false-modal')
    await expect(falseModal).toBeVisible()
    await expect(falseModal).toContainText('ALR-S-R3')
    await falseModal.getByTestId('alert-false-reason').fill('阈值过严')
    await page.screenshot({ path: `${shotDir}/03-false-alarm.png`, fullPage: true })
    await falseModal.getByTestId('alert-false-submit').click()
    await expect(liveRow).toContainText('FALSE_ALARM', { timeout: 15_000 })
    await expect(page.locator('p.hint').filter({ hasText: /已标记误报/ })).toBeVisible()

    await liveRow.getByTestId('alert-false-alarm-btn').click()
    await page.getByTestId('alert-false-submit').click()
    await expect(page.locator('p.hint').filter({ hasText: /1167/ })).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${shotDir}/04-repeat-1167.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
