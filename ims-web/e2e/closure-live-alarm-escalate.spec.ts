import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * #142 LIVE-003（纯 UI）
 * 满 30 分钟的 L3 显示已升级；2 分钟内的 L3 只记钉钉/短信桩；规则保存后列表立即看到新阈值。
 */
const shotDir = '/opt/cursor/artifacts/slice-142-live-alarm'
const AGED = 'IMS20261009ALM0030'
const FRESH_L3 = 'IMS20261009ALM0003'
const FRESH_L2 = 'IMS20261009ALM0005'

fs.mkdirSync(shotDir, { recursive: true })

test.describe('live alarm 30 minute escalate stub', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('aged L3 escalates in-app while fresh L3 stays a channel stub', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警', { timeout: 15_000 })
    await page.getByTestId('live-alarm-tab-records').click()

    async function showSession(code: string) {
      await page.getByTestId('live-alarm-session').fill(code)
      const listed = page.waitForResponse(
        (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET' && r.status() === 200,
      )
      await page.getByTestId('live-alarm-query').click()
      await listed
    }

    await showSession(AGED)
    const aged = page.getByTestId('live-alarm-row').filter({ hasText: AGED })
    await expect(aged).toBeVisible({ timeout: 15_000 })
    await expect(aged.getByTestId('live-alarm-escalated')).toHaveText('已升级')
    await expect(aged.getByTestId('live-alarm-stub')).toContainText('钉钉桩')
    await expect(aged.getByTestId('live-alarm-stub')).toContainText('未外发')

    await showSession(FRESH_L3)
    const freshL3 = page.getByTestId('live-alarm-row').filter({ hasText: FRESH_L3 })
    await expect(freshL3).toBeVisible()
    await expect(freshL3.getByTestId('live-alarm-stub')).toContainText('短信桩')
    await expect(freshL3.getByTestId('live-alarm-escalated')).toHaveCount(0)

    await showSession(FRESH_L2)
    const freshL2 = page.getByTestId('live-alarm-row').filter({ hasText: FRESH_L2 })
    await expect(freshL2).toBeVisible()
    await expect(freshL2.getByTestId('live-alarm-escalated')).toHaveCount(0)
    await expect(freshL2.getByTestId('live-alarm-stub')).toHaveText('站内')
    await expect(page.getByTestId('live-alarm-banner')).toContainText('未外发')
    await page.screenshot({ path: `${shotDir}/01-escalate-and-stub.png`, fullPage: true })

    await showSession(AGED)
    await aged.getByTestId('live-alarm-handle').click()
    await expect(page.getByTestId('live-alarm-handle-remark')).toBeVisible()
    await page.getByTestId('live-alarm-handle-remark').fill('场观已回落，站内处置')
    const handleResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/record/') && r.url().includes('/handle') && r.request().method() === 'PUT',
    )
    await page.getByTestId('live-alarm-handle-submit').click()
    const handleBody = (await (await handleResp).json()) as { code: number }
    expect(handleBody.code).toBe(0)
    await expect(aged).toContainText('已处理')
    await expect(aged.getByTestId('live-alarm-escalated')).toHaveText('已升级')
    await page.screenshot({ path: `${shotDir}/02-handled-keeps-escalated.png`, fullPage: true })

    await page.getByTestId('live-alarm-tab-rules').click()
    await page.getByTestId('live-alarm-rule-create').click()
    await page.getByTestId('live-alarm-rule-name').fill('场观骤降热更新')
    await page.getByTestId('live-alarm-rule-threshold').fill('30')
    await page.getByTestId('live-alarm-rule-window').fill('5')
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/rule') && r.request().method() === 'POST',
    )
    await page.getByTestId('live-alarm-rule-save').click()
    const createBody = (await (await createResp).json()) as { code: number; data?: { id?: number } }
    expect(createBody.code).toBe(0)
    const ruleRow = page.getByTestId('live-alarm-rule-row').filter({ hasText: '场观骤降热更新' })
    await expect(ruleRow.getByTestId('live-alarm-rule-summary')).toContainText('30')
    await expect(page.getByTestId('live-alarm-rule-hint')).toContainText('ALM-R4')

    await ruleRow.getByRole('button', { name: '编辑' }).click()
    await page.getByTestId('live-alarm-rule-threshold').fill('40')
    const updateResp = page.waitForResponse(
      (r) => /\/live\/alarm\/rule\/\d+/.test(r.url()) && r.request().method() === 'PUT',
    )
    await page.getByTestId('live-alarm-rule-save').click()
    const updateBody = (await (await updateResp).json()) as { code: number }
    expect(updateBody.code).toBe(0)
    await expect(ruleRow.getByTestId('live-alarm-rule-summary')).toContainText('40')
    await page.screenshot({ path: `${shotDir}/03-rule-hot-update.png`, fullPage: true })

    await ruleRow.getByTestId('live-alarm-rule-delete').click()
    await page.getByTestId('live-alarm-delete-text').fill('DELETE')
    await page.getByTestId('live-alarm-delete-confirm').click()
    await expect(ruleRow).toHaveCount(0)

    await page.getByTestId('live-alarm-tab-stats').click()
    await expect(page.getByTestId('live-alarm-stats-severe')).not.toHaveText('0')
    await page.screenshot({ path: `${shotDir}/04-stats.png`, fullPage: true })

    await loginAs(page, 'live_director')
    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心', { timeout: 15_000 })
    const msg = page.locator('tbody tr').filter({ hasText: `直播告警已升级：${AGED}` })
    await expect(msg).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/05-director-inbox.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
