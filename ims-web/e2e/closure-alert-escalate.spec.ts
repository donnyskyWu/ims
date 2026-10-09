import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S11** 升级链切片（acceptance · 纯 UI · #130）
 * Given: 管理员把一级/二级时限设为 0
 * When: 新建启用规则并试跑
 * Then: 待升级清单当前级别为三级，时间轴含一级到三级，确认后升级停止且清单不再出现
 */
const shotDir = '/opt/cursor/artifacts/e2e-130-screenshots'

test.describe('alert escalate chain closure S11', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('zero timeouts escalate to level 3 then confirm stops the chain', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.esc.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await page.getByTestId('alert-escalate-l1').fill('0')
    await page.getByTestId('alert-escalate-l2').fill('0')
    await page.getByTestId('alert-escalate-severe').selectOption('2')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/alert/escalate/config') && r.request().method() === 'PUT',
    )
    await page.getByTestId('alert-escalate-save').click()
    expect((await (await saveResp).json()).code).toBe(0)
    await expect(page.getByTestId('alert-escalate-saved')).toContainText('升级链路已更新')
    await page.screenshot({ path: `${shotDir}/01-config-saved.png`, fullPage: true })

    await page.goto('/ims/alert/rule')
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

    await page.goto('/ims/alert/escalate')
    const row = page.getByTestId(`alert-escalate-row-${alertNo}`)
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.getByTestId('alert-escalate-current')).toHaveText('三级')
    await expect(row).toContainText('终级等待响应')
    await page.screenshot({ path: `${shotDir}/02-pending-level3.png`, fullPage: true })

    await row.getByTestId('alert-escalate-timeline').click()
    const nodes = page.getByTestId('alert-escalate-node')
    await expect(nodes).toHaveCount(3)
    await expect(nodes.nth(0)).toContainText('一级')
    await expect(nodes.nth(0)).toContainText('责任人')
    await expect(nodes.nth(2)).toContainText('三级')
    await expect(nodes.nth(2)).toContainText('钉钉不外发')
    await page.screenshot({ path: `${shotDir}/03-timeline.png`, fullPage: true })
    await page.locator('aside.drawer.on .dr-x').click()

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/alert/check/') && r.url().includes('/respond') && r.request().method() === 'PUT',
    )
    await row.getByTestId('alert-escalate-confirm').click()
    const confirmBody = (await (await confirmResp).json()) as {
      code: number
      data?: { escalationStopped?: boolean; responseStatus?: string }
    }
    expect(confirmBody.code).toBe(0)
    expect(confirmBody.data?.escalationStopped).toBe(true)
    expect(confirmBody.data?.responseStatus).toBe('CONFIRMED')
    await expect(page.getByTestId('alert-escalate-toast')).toContainText('后续升级已停止')
    await expect(row).toHaveCount(0)
    await page.getByTestId('alert-escalate-l1').fill('30')
    await page.getByTestId('alert-escalate-l2').fill('60')
    await page.getByTestId('alert-escalate-severe').selectOption('2')
    await page.getByTestId('alert-escalate-save').click()
    await expect(page.getByTestId('alert-escalate-saved')).toContainText('一级 30 分钟')
    await page.screenshot({ path: `${shotDir}/04-stopped.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
