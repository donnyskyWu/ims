import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * MASTER #211 · 手机类型筛选空态 + 公司未填行业/地址/扩容空态
 * 纯 UI：新建手机走表单，不调用 /admin-api 造数。
 */
test.describe('master phone type and company detail tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter phones by dictionary type and show blank company edges', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    page.on('dialog', (dialog) => dialog.accept())

    await loginAdmin(page)
    const stamp = String(Date.now()).slice(-8)
    const phoneNumber = `139${stamp}`
    const deviceNumber = `M211-${stamp}`

    await page.goto('/ims/corp/device/phone')
    await expect(page.locator('h1')).toContainText('手机')
    await expect(page.getByTestId('master-phone-type-hint')).toContainText('dict_phone_type')
    await expect(page.getByTestId('master-phone-type')).toBeVisible()

    await page.getByRole('button', { name: '新建手机' }).click()
    const form = page.locator('.drawer.on')
    await expect(form.getByText('新建手机')).toBeVisible()
    await form.locator('.fld', { hasText: '手机号' }).locator('input').fill(phoneNumber)
    await form.locator('.fld', { hasText: '设备编号' }).locator('input').fill(deviceNumber)
    const keeper = form.locator('.fld', { hasText: '保管人' }).locator('select')
    if ((await keeper.inputValue()) === '') {
      const value = await keeper.locator('option').nth(1).getAttribute('value')
      expect(value).toBeTruthy()
      await keeper.selectOption(value || '')
    }
    await form.getByTestId('master-phone-form-type').selectOption({ label: 'Android' })
    const created = page.waitForResponse(
      (response) =>
        response.url().includes('/master/phone') &&
        response.request().method() === 'POST' &&
        response.status() === 200,
    )
    await form.getByRole('button', { name: '保存' }).click()
    const createdBody = await (await created).json()
    expect(createdBody.code).toBe(0)
    await expect(form).toBeHidden()

    await page.locator('input[placeholder="设备编号 / 型号"]').fill(deviceNumber)
    await page.getByTestId('master-phone-type').selectOption({ label: 'Android' })
    const matched = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/device/phone/page') &&
        response.url().includes('phoneType=ANDROID') &&
        response.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await matched
    await expect(page.locator('tr', { hasText: deviceNumber })).toBeVisible()
    await expect(page.locator('tr', { hasText: deviceNumber })).toContainText('Android')

    await page.getByTestId('master-phone-type').selectOption({ label: 'iPhone' })
    const missed = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/device/phone/page') &&
        response.url().includes('phoneType=IPHONE') &&
        response.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await missed
    await expect(page.getByTestId('master-phone-empty')).toContainText('没有符合筛选的记录')

    await page.getByRole('button', { name: '重置' }).click()
    await expect(page.getByTestId('master-phone-type')).toHaveValue('')
    await expect(page.locator('input[placeholder="设备编号 / 型号"]')).toHaveValue('')

    await page.goto('/ims/corp/resource/company')
    await expect(page.locator('h1')).toContainText('公司')
    const companyRow = page.locator('tr', { hasText: '未填写行业' }).first()
    await expect(companyRow).toBeVisible()
    await companyRow.getByRole('button', { name: '详情' }).click()
    const drawer = page.locator('.drawer.on')
    await expect(drawer).toContainText('未填写行业')
    await expect(drawer.getByTestId('master-company-address')).toHaveText('未填写地址')
    await expect(drawer.getByTestId('master-company-expansion-empty')).toContainText('暂无扩容记录')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
