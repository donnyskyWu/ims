import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist E2E-S8-05 / E2E-S8-09 的页面侧（acceptance · 纯 UI）。
 * 第 61 次 429 与换新后的分钟窗在 pytest 覆盖；这里只核对限额配置和列表展示。
 */
const shotDir = '/opt/cursor/artifacts/e2e-85-screenshots'

test.describe('air key qpm closure S8', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('generate key then renew shows the new QPM', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/air/cfg?tab=key')
    await expect(page.locator('h1')).toContainText('模型与提示词')
    await expect(page.getByRole('button', { name: 'Key 管理' })).toBeVisible()

    const seedRow = page.locator('tbody tr').filter({ hasText: 'KEY-0001' })
    await expect(seedRow).toBeVisible({ timeout: 15_000 })
    await expect(seedRow.getByTestId('air-qpm-cell')).toHaveText('60')
    await page.screenshot({ path: `${shotDir}/01-key-list-qpm-60.png`, fullPage: true })

    for (let i = 0; i < 6; i++) {
      const revoke = page.locator('tbody tr', { hasText: 'e2e_author' }).getByTestId('air-key-revoke').first()
      if ((await revoke.count()) === 0) break
      const done = page.waitForResponse(
        (response) =>
          response.url().includes('/air/key/') &&
          response.url().includes('/revoke') &&
          response.request().method() === 'POST',
      )
      const listed = page.waitForResponse(
        (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
      )
      await revoke.click()
      await page.getByTestId('air-key-revoke-ok').click()
      await done
      await listed
    }

    await page.getByTestId('air-key-generate').click()
    const form = page.getByTestId('air-key-form')
    await form.getByTestId('air-key-user-search').fill('e2e_author')
    const users = page.waitForResponse((response) => response.url().includes('/system/user/page'))
    await form.getByRole('button', { name: '查找' }).click()
    await users
    await expect(form.getByTestId('air-key-user')).not.toHaveValue('')
    await form.getByTestId('air-qpm-limit').fill('60')
    await page.screenshot({ path: `${shotDir}/02-generate-form-qpm.png`, fullPage: true })
    await form.getByTestId('air-key-save').click()

    const plain = page.getByTestId('air-key-plain')
    await expect(plain).toBeVisible({ timeout: 15_000 })
    const plainText = ((await plain.innerText()) || '').trim()
    expect(plainText.startsWith('air-')).toBeTruthy()
    const keyCode = ((await page.getByTestId('air-key-code').innerText()) || '').trim()
    await expect(page.getByTestId('air-key-issued-qpm')).toContainText('60')
    await page.screenshot({ path: `${shotDir}/03-plain-key-once.png`, fullPage: true })
    await page.getByTestId('air-key-plain-close').click()
    await expect(page.getByTestId('air-key-plain')).toHaveCount(0)
    await expect(page.locator('body')).not.toContainText(plainText)

    const created = page.locator('tbody tr').filter({ hasText: keyCode })
    await expect(created).toBeVisible()
    await expect(created).toContainText('e2e_author')
    await expect(created.getByTestId('air-qpm-cell')).toHaveText('60')
    const mask = ((await created.getByTestId('air-key-mask').innerText()) || '').trim()
    expect(mask).not.toBe(plainText)
    expect(mask.startsWith('air-')).toBeTruthy()
    await page.screenshot({ path: `${shotDir}/04-mask-and-qpm-60.png`, fullPage: true })

    await created.getByTestId('air-key-renew').click()
    const renew = page.getByTestId('air-key-form')
    await renew.getByTestId('air-qpm-limit').fill('12')
    await page.screenshot({ path: `${shotDir}/05-renew-qpm-12.png`, fullPage: true })
    await renew.getByTestId('air-key-save').click()

    const plainNext = page.getByTestId('air-key-plain')
    await expect(plainNext).toBeVisible({ timeout: 15_000 })
    const plainTextNext = ((await plainNext.innerText()) || '').trim()
    expect(plainTextNext.startsWith('air-')).toBeTruthy()
    expect(plainTextNext).not.toBe(plainText)
    const keyCodeNext = ((await page.getByTestId('air-key-code').innerText()) || '').trim()
    await expect(page.getByTestId('air-key-issued-qpm')).toContainText('12')
    await page.getByTestId('air-key-plain-close').click()
    await expect(page.locator('body')).not.toContainText(plainTextNext)

    const renewed = page.locator('tbody tr').filter({ hasText: keyCodeNext })
    await expect(renewed.getByTestId('air-qpm-cell')).toHaveText('12')
    await page.screenshot({ path: `${shotDir}/06-qpm-12-visible.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
