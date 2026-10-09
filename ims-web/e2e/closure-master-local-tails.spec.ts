import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/**
 * MASTER #229 · 手机卡表单字典校验、关联空态、行业字典对照文案
 * 不重建 #174 筛选、#192 行业下拉、#211 手机类型与公司地址空态。
 * 纯 UI：手机卡经表单新建，不调用 /admin-api 造数。
 */
test.describe('master local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('sim form validation, empty links, and industry dict edge', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    page.on('dialog', (dialog) => dialog.accept())
    let simPosts = 0
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/corp/resource/sim-card')) simPosts += 1
    })

    await loginAdmin(page)
    await page.goto('/ims/system/dict')
    await expect(page.locator('h1')).toContainText('字典管理')
    await page.getByTestId('dict-type-filter').fill('dict_industry')
    const industryType = page.locator('[data-testid="dict-type-row"]', { hasText: 'dict_industry' })
    const industryDictSeeded = (await industryType.count()) > 0

    await page.goto('/ims/corp/resource/company')
    await expect(page.locator('h1')).toContainText('公司')
    await page.getByRole('button', { name: '详情' }).first().click()
    const companyDrawer = page.locator('.drawer.on')
    const industryEdge = companyDrawer.getByTestId('master-company-industry-edge')
    await expect(industryEdge).toBeVisible()
    if (industryDictSeeded) {
      await expect(industryEdge).toContainText('dict_industry')
      await expect(industryEdge).toContainText(/还没有行业|未列入启用的行业字典|行业对照字典/)
    } else {
      await expect(industryEdge).toContainText('字典 dict_industry 没有启用项')
    }
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-company-industry-edge.png',
      fullPage: true,
    })
    await companyDrawer.getByRole('button', { name: '关闭' }).click()

    await page.goto('/ims/corp/resource/realname')
    await expect(page.locator('h1')).toContainText('实名人')
    await expect(page.getByTestId('master-realname-idtype-hint')).toContainText('停用项和未列入字典的类型不会出现在下拉里')
    await expect(page.getByTestId('master-realname-idtype').locator('option', { hasText: '护照' })).toHaveCount(1)
    await page.getByRole('button', { name: '详情' }).first().click()
    const personDrawer = page.locator('.drawer.on')
    await expect(personDrawer.getByTestId('master-realname-intermediary-empty')).toContainText('暂无中介人')
    await expect(personDrawer.getByTestId('master-realname-linked-empty')).toContainText('暂无关联账号')
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-realname-relation-empty.png',
      fullPage: true,
    })

    await page.goto('/ims/corp/resource/sim-card')
    await expect(page.locator('h1')).toContainText('手机卡')
    await expect(page.getByTestId('master-sim-operator')).toBeVisible()
    await page.getByRole('button', { name: '新建手机卡' }).click()
    const form = page.locator('.drawer.on')
    await expect(form.getByTestId('master-sim-dict-hint')).toContainText('停用项不会出现在下拉里')

    await form.getByRole('button', { name: '保存' }).click()
    await expect(form.getByTestId('master-sim-form-error')).toContainText('手机号必填')
    expect(simPosts).toBe(0)

    await form.getByTestId('master-sim-phone').fill('12345')
    await form.getByRole('button', { name: '保存' }).click()
    await expect(form.getByTestId('master-sim-form-error')).toContainText('手机号须为 11 位')
    expect(simPosts).toBe(0)

    const phoneNumber = `139${String(Date.now()).slice(-8)}`
    await form.getByTestId('master-sim-phone').fill(phoneNumber)
    await form.getByTestId('master-sim-rent').fill('abc')
    await form.getByRole('button', { name: '保存' }).click()
    await expect(form.getByTestId('master-sim-form-error')).toContainText('月租须为数字')

    await form.getByTestId('master-sim-rent').fill('-1')
    await form.getByRole('button', { name: '保存' }).click()
    await expect(form.getByTestId('master-sim-form-error')).toContainText('月租不能为负')
    expect(simPosts).toBe(0)
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-sim-form-error.png',
      fullPage: true,
    })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-sim-form-error-mobile.png',
      fullPage: true,
    })
    await page.setViewportSize({ width: 1280, height: 800 })

    await form.getByTestId('master-sim-rent').fill('')
    const created = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/resource/sim-card') &&
        response.request().method() === 'POST' &&
        response.status() === 200,
    )
    await form.getByRole('button', { name: '保存' }).click()
    const createdBody = await (await created).json()
    expect(createdBody.code).toBe(0)
    expect(simPosts).toBe(1)
    await expect(form).toBeHidden()

    await page.locator('input[placeholder="完整手机号"]').fill(phoneNumber)
    const listed = page.waitForResponse(
      (response) =>
        response.url().includes('/corp/resource/sim-card/page') &&
        response.url().includes('phoneNumber=') &&
        response.status() === 200,
    )
    await page.locator('form.qbar button[type="submit"]').click()
    await listed
    const row = page.locator('tr', { hasText: '详情' }).last()
    await row.getByRole('button', { name: '详情' }).click()
    const simDrawer = page.locator('.drawer.on')
    await expect(simDrawer.getByTestId('master-sim-linked-empty')).toContainText('暂无关联账号')
    await page.screenshot({
      path: '/opt/cursor/artifacts/master-sim-linked-empty.png',
      fullPage: true,
    })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
