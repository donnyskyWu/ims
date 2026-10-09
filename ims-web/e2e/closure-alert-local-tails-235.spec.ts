import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #235 预警本地尾巴：规则表单预校验、日期颠倒、升级时限，以及送达回执里短信未触发的边角文案。
 * 不重做 #184 通道空态、#205 级别筛选与送达率空范围、#218 列表筛选空态。
 */
const shotDir = '/opt/cursor/artifacts/alert-235-screenshots'

test.describe('alert local form and receipt edges', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('form checks, inverted dates, and untriggered sms copy', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const code = `e2e.alert.235.${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/alert/rule')
    await expect(page.locator('h1')).toContainText('预警规则')

    await page.getByRole('button', { name: '新建规则' }).click()
    const modal = page.locator('.card').filter({ has: page.locator('h3', { hasText: '注册预警规则' }) })
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('alert-rule-form-error')).toContainText('规则编码或名称至少填一项')
    await page.screenshot({ path: `${shotDir}/01-rule-required.png` })

    await modal.locator('input[placeholder="live.data.delay"]').fill(code)
    await modal.getByTestId('alert-rule-name').fill(`E2E 校验 ${code}`)
    await modal.getByTestId('alert-rule-threshold').fill('not a dsl')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('alert-rule-threshold-error')).toContainText('delayMinutes>30')
    await page.screenshot({ path: `${shotDir}/02-threshold-invalid.png` })

    await modal.getByTestId('alert-rule-threshold').fill('')
    await modal.getByTestId('alert-dsl-source').fill('ims_fin_cost')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('alert-dsl-error')).toContainText('1009')
    await page.screenshot({ path: `${shotDir}/03-dsl-incomplete.png` })

    await modal.getByTestId('alert-dsl-source').fill('')
    await modal.getByTestId('alert-rule-threshold').fill('delayMinutes>0')
    await modal.locator('label').filter({ hasText: '创建后立即启用' }).locator('input[type="checkbox"]').check()
    await modal.getByRole('button', { name: '保存' }).click()

    const ruleRow = page.locator('tbody tr').filter({ hasText: code })
    await expect(ruleRow).toBeVisible({ timeout: 15_000 })
    await ruleRow.getByTestId('alert-rule-edit').click()
    const edit = page.locator('.card').filter({ has: page.locator('h3', { hasText: '编辑预警规则' }) })
    await edit.getByTestId('alert-rule-name').fill('')
    await edit.getByRole('button', { name: '保存' }).click()
    await expect(edit.getByTestId('alert-rule-name-error')).toContainText('规则名称不能为空')
    await page.screenshot({ path: `${shotDir}/04-name-required.png` })
    await edit.getByRole('button', { name: '取消' }).click()

    await page.getByTestId('alert-hit-open').click()
    const hits = page.getByTestId('alert-hit-modal')
    await hits.getByTestId('alert-hit-start').fill('2099-05-02')
    await hits.getByTestId('alert-hit-end').fill('2099-05-01')
    await hits.getByRole('button', { name: '查询' }).click()
    await expect(hits.getByTestId('alert-hit-error')).toContainText('起始日期不能晚于结束日期')
    await page.screenshot({ path: `${shotDir}/05-hit-dates.png` })
    await hits.getByRole('button', { name: '关闭' }).click()

    await ruleRow.getByRole('button', { name: '试跑' }).click()
    const trialHint = page.locator('p.hint').filter({ hasText: /试跑成功/ })
    await expect(trialHint).toBeVisible({ timeout: 15_000 })
    const alertNo = ((await trialHint.innerText()) || '').match(/AL\d+/)?.[0]
    expect(alertNo).toBeTruthy()

    await page.goto('/ims/alert/live')
    const liveRow = page.locator('tbody tr').filter({ hasText: alertNo! })
    await expect(liveRow).toBeVisible({ timeout: 15_000 })
    await expect(liveRow.getByTestId(`alert-push-${alertNo}`)).toContainText('短信未触发')
    await liveRow.getByTestId('alert-receipt-btn').click()
    const drawer = page.getByTestId('alert-receipt-drawer')
    const sms = drawer.locator('[data-channel="SMS"]')
    await expect(sms).toContainText('未触发')
    await expect(sms.getByTestId('alert-receipt-note')).toContainText('未触发，不外发')
    await page.screenshot({ path: `${shotDir}/06-sms-untriggered.png` })
    await page.getByTestId('alert-receipt-close').click()

    await page.goto('/ims/alert/stats')
    await page.getByTestId('alert-stats-start').fill('2099-02-02')
    await page.getByTestId('alert-stats-end').fill('2099-01-01')
    await page.getByRole('button', { name: '刷新' }).click()
    await expect(page.getByTestId('alert-stats-error')).toContainText('起始日期不能晚于结束日期')
    await expect(page.getByTestId('alert-channel-empty')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/07-stats-dates.png` })

    await page.goto('/ims/alert/escalate')
    await expect(page.locator('h1')).toContainText('升级中心')
    await page.getByTestId('alert-escalate-l1').fill('10081')
    await page.getByTestId('alert-escalate-save').click()
    await expect(page.getByTestId('alert-escalate-form-error')).toContainText('0～10080')
    await expect(page.getByTestId('alert-escalate-saved')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/08-escalate-minutes.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
