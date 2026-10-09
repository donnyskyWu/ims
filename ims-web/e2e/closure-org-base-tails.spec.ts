import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-175-screenshots'

/**
 * #175 组织 / 系统基座本地尾巴（acceptance · 纯 UI）
 * 人员与同步事件按同步状态筛选空态、字典类型/停用值、参数与角色关键字空态。
 * 不造钉钉通讯录事件。
 */
test.describe('org and system-base local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('sync status, dict disabled values, and param/role filter empties', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/auth/org')
    await expect(page.locator('h1')).toContainText('组织架构同步')
    await page.getByTestId('org-sync-status').selectOption('DEAD_LETTER')
    const deadResp = page.waitForResponse(
      (r) => r.url().includes('/auth/org/users') && r.url().includes('syncStatus=DEAD_LETTER') && r.status() === 200,
    )
    await page.getByTestId('org-user-search').click()
    await deadResp
    const userEmpty = page.getByTestId('org-user-empty')
    const userTags = page.getByTestId('org-sync-tag')
    if (await userEmpty.count()) {
      await expect(userEmpty).toContainText('没有该同步状态的人员')
    } else {
      await expect(userTags.first()).toHaveText('死信')
    }
    await page.screenshot({ path: `${SHOTS}/01-org-sync-status.png`, fullPage: true })

    await page.getByTestId('org-user-reset').click()
    await page.getByTestId('org-user-keyword').fill('no-such-org-zz175')
    const missResp = page.waitForResponse(
      (r) => r.url().includes('/auth/org/users') && r.url().includes('no-such-org-zz175') && r.status() === 200,
    )
    await page.getByTestId('org-user-search').click()
    await missResp
    await expect(page.getByTestId('org-user-empty')).toContainText('没有匹配的人员')
    await page.screenshot({ path: `${SHOTS}/02-org-user-filter-empty.png`, fullPage: true })

    await page.locator('.tab', { hasText: '同步事件' }).click()
    await page.getByTestId('org-event-type').selectOption('resign')
    await page.getByTestId('org-event-status').selectOption('SUCCESS')
    const eventResp = page.waitForResponse(
      (r) =>
        r.url().includes('/auth/org/events') &&
        r.url().includes('eventType=resign') &&
        r.url().includes('syncStatus=SUCCESS') &&
        r.status() === 200,
    )
    await page.getByTestId('org-event-search').click()
    await eventResp
    const eventEmpty = page.getByTestId('org-event-empty')
    const eventTags = page.getByTestId('org-event-sync-tag')
    if (await eventEmpty.count()) {
      await expect(eventEmpty).toContainText('没有符合条件的同步事件')
    } else {
      await expect(eventTags.first()).toHaveText('成功')
    }
    await page.screenshot({ path: `${SHOTS}/03-org-event-filter.png`, fullPage: true })

    await page.goto('/ims/system/dict')
    await expect(page.locator('h1')).toContainText('字典管理')
    await expect(page.getByTestId('dict-type-row').first()).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('dict-type-filter').fill('no-such-dict-zz175')
    await expect(page.getByTestId('dict-type-empty')).toContainText('没有匹配的字典类型')
    await page.screenshot({ path: `${SHOTS}/04-dict-type-empty.png`, fullPage: true })

    await page.getByTestId('dict-type-filter').fill('平台')
    const platform = page.getByTestId('dict-type-row').filter({ hasText: 'dict_platform_type' })
    await expect(platform).toBeVisible()
    await platform.click()
    await page.getByTestId('dict-status-disabled').click()
    const disabled = page.getByTestId('dict-value-row').filter({ hasText: 'LEGACY_OFF' })
    await expect(disabled).toBeVisible()
    await expect(disabled.getByTestId('dict-disabled-lock')).toHaveText('停用不可删')
    await expect(disabled.getByTestId('dict-delete')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/05-dict-disabled-lock.png`, fullPage: true })

    await page.getByTestId('dict-status-enabled').click()
    await expect(page.getByTestId('dict-value-row').filter({ hasText: 'LEGACY_OFF' })).toHaveCount(0)
    await expect(page.getByTestId('dict-delete').first()).toBeVisible()

    await page.goto('/ims/system/param')
    await expect(page.locator('h1')).toContainText('系统参数')
    await page.getByTestId('param-keyword').fill('no-such-param-zz175')
    await expect(page.getByTestId('param-empty')).toContainText('没有匹配的参数')
    await page.screenshot({ path: `${SHOTS}/06-param-filter-empty.png`, fullPage: true })
    await page.getByTestId('param-keyword').fill('dingtalk.corpId')
    await expect(page.getByTestId('param-row').filter({ hasText: 'dingtalk.corpId' })).toBeVisible()
    await page.getByTestId('param-reset').click()
    await expect(page.getByTestId('param-row').first()).toBeVisible()

    await page.goto('/ims/system/role')
    await expect(page.locator('h1')).toContainText('角色权限')
    await expect(page.getByTestId('role-row').first()).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('role-keyword').fill('no-such-role-zz175')
    await expect(page.getByTestId('role-list-empty')).toContainText('没有匹配的角色')
    await page.screenshot({ path: `${SHOTS}/07-role-filter-empty.png`, fullPage: true })
    await page.getByTestId('role-keyword').fill('sys:admin')
    await expect(page.getByTestId('role-row').filter({ hasText: 'sys:admin' })).toBeVisible()
    await page.getByTestId('role-reset').click()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
