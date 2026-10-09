import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/acct-return-1024'

async function createUser(page: Page, username: string, nickname: string) {
  await page.goto('/ims/system/user')
  await expect(page.locator('h1')).toHaveText('用户管理', { timeout: 15_000 })
  await page.getByRole('button', { name: '新建用户' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新建用户' })
  await drawer.locator('input').nth(0).fill(username)
  await drawer.locator('input').nth(1).fill(nickname)
  await drawer.locator('input').nth(2).fill(`139${String(Date.now()).slice(-8)}`)
  await drawer.locator('input[type="password"]').fill('Admin@123')
  const saved = page.waitForResponse(
    (r) => r.url().includes('/system/user') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存' }).click()
  const body = (await (await saved).json()) as { code: number; data?: { id?: number } }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
  return Number(body.data?.id)
}

/** #132 · 离职归还单未闭环时关闭权限与闭环确认都返回 1024 */
test.describe('account resign return 1024 closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pending return blocks permission close with 1024, then close succeeds after the item is returned', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)

    const stamp = Date.now()
    const username = `resign${stamp}`
    const nickname = `离职同事${stamp}`
    const userId = await createUser(page, username, nickname)
    expect(userId).toBeGreaterThan(0)

    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    const code = `AS-RT-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`离职显示器-${stamp}`)
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    await expect(create).toBeHidden()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-owner').selectOption({ label: nickname })
    await checkout.getByTestId('corp-asset-purpose').fill('离职前领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect(((await (await checkoutResp).json()) as { code: number }).code).toBe(0)

    await page.goto('/ims/account/return')
    await expect(page.locator('h1')).toHaveText('离职归还', { timeout: 15_000 })
    await page.getByTestId('return-generate-open').click()
    const generate = page.locator('.drawer.on').filter({ hasText: '手动补建归还单' })
    await generate.getByTestId('return-generate-user').selectOption({ label: nickname })
    const generated = page.waitForResponse(
      (r) => r.url().includes('/account/return/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await generate.getByTestId('return-generate-save').click()
    const order = (await (await generated).json()) as { code: number; data?: { returnNo?: string } }
    expect(order.code).toBe(0)
    expect(order.data?.returnNo || '').toMatch(/^RT/)
    const handle = page.locator('.drawer.on').filter({ hasText: '归还单处理' })
    await expect(handle.getByTestId('return-item-label')).toContainText(code)
    await expect(handle.getByTestId('return-item-status')).toHaveText('待归还')
    await page.screenshot({ path: `${shotDir}/01-return-pending.png`, fullPage: true })

    const disableResp = page.waitForResponse(
      (r) => r.url().includes('/system/user/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await handle.getByTestId('return-disable-user').click()
    const disabled = (await (await disableResp).json()) as { code: number; msg?: string }
    expect(disabled.code).toBe(1024)
    await expect(handle.getByTestId('return-detail-error')).toContainText('1024')
    await expect(handle.getByTestId('return-detail-error')).toContainText('禁止关闭权限')

    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/close') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await handle.getByTestId('return-close').click()
    const closedEarly = (await (await closeResp).json()) as { code: number }
    expect(closedEarly.code).toBe(1024)
    await expect(handle.getByTestId('return-detail-error')).toContainText('1024')
    await page.screenshot({ path: `${shotDir}/02-close-1024.png`, fullPage: true })

    const returned = page.waitForResponse(
      (r) => r.url().includes('/account/return/item/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await handle.getByTestId('return-item-returned').click()
    expect(((await (await returned).json()) as { code: number }).code).toBe(0)
    await expect(handle.getByTestId('return-item-status')).toHaveText('已归还')

    const closeOk = page.waitForResponse(
      (r) => r.url().includes('/close') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await handle.getByTestId('return-close').click()
    expect(((await (await closeOk).json()) as { code: number }).code).toBe(0)
    await expect(handle.getByTestId('return-detail-head')).toContainText('已闭环')
    await page.screenshot({ path: `${shotDir}/03-return-closed.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
