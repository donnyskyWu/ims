import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * BUG-027 · 登记平台账号（纯 UI）
 * When: 抖音账号页打开「登记账号」，空表单保存，再按名称选择公司 / 小组 / 实名人后保存
 * Then: 必填项逐项提示；成功后列表出现新账号，状态为池可领用，编号自动生成
 */
test.describe('platform account register closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty submit prompts required fields, then save lands in pool', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/account/douyin')
    await expect(page.locator('h1')).toContainText('抖音')

    await page.getByTestId('acct-register-open').click()
    const drawer = page.locator('.drawer.on', { hasText: '登记平台账号' })
    await expect(drawer.getByTestId('acct-register-platform')).toHaveValue('抖音')
    await expect(drawer.locator('input[placeholder*="id"]')).toHaveCount(0)

    await drawer.getByTestId('acct-register-save').click()
    await expect(drawer.getByTestId('acct-register-error-name')).toHaveText('必填项，请填写')
    await expect(drawer.getByTestId('acct-register-error-company')).toHaveText('必填项，请填写')
    await expect(drawer.getByTestId('acct-register-error-ip-group')).toHaveText('必填项，请填写')
    await expect(drawer.getByTestId('acct-register-error-realname')).toHaveText('必填项，请填写')
    await expect(page.getByTestId('acct-register-toast')).toContainText('请先完成必填项')

    const stamp = Date.now().toString().slice(-8)
    const accountName = `UI登记号${stamp}`
    await drawer.getByTestId('acct-register-name').fill(accountName)
    await drawer.getByTestId('acct-register-platform-id').fill(`ui-dy-${stamp}`)

    const company = drawer.getByTestId('acct-register-company')
    await expect(company.locator('option')).not.toHaveCount(1)
    await company.selectOption({ index: 1 })
    const group = drawer.getByTestId('acct-register-ip-group')
    await expect(group.locator('option')).not.toHaveCount(1)
    await group.selectOption({ index: 1 })
    const person = drawer.getByTestId('acct-register-realname')
    await expect(person.locator('option')).not.toHaveCount(1)
    await person.selectOption({ index: 1 })

    const saved = page.waitForResponse(
      (res) => res.url().includes('/master/platform-account') && res.request().method() === 'POST',
    )
    await drawer.getByTestId('acct-register-save').click()
    const response = await saved
    expect(response.ok()).toBeTruthy()
    const payload = await response.json()
    expect(payload.code).toBe(0)
    expect(payload.data.status).toBe('IN_POOL')
    expect(String(payload.data.accountNo || '')).toMatch(/^ACCT-/)

    await expect(page.getByTestId('acct-register-toast')).toHaveText('账号已登记')
    const row = page.locator('tr', { hasText: accountName })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.getByTestId('acct-status-tag')).toContainText('池可领用')
    await expect(row.locator('td').first()).toContainText('ACCT-')
  })
})
