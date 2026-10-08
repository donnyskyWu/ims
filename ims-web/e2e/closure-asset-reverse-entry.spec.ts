import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-72-screenshots'
const SESSION = 'IMS20261008DYE0072'

async function registerBound(page: Page, code: string, name: string, accountNo: string, sessionCode = '') {
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  await create.getByTestId('corp-asset-code').fill(code)
  await create.getByTestId('corp-asset-name').fill(name)
  if (accountNo) await create.getByTestId('corp-asset-bind-account').fill(accountNo)
  if (sessionCode) await create.getByTestId('corp-asset-bind-session').fill(sessionCode)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  const saved = (await (await saveResp).json()) as { code: number }
  expect(saved.code).toBe(0)
  await expect(create).toBeHidden()
}

/** Checklist **E2E-S5-05**（#72 · 纯 UI · 账号/场次反查） */
test.describe('corp asset account and session reverse closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('bound office assets show under the account and the session, missing session is 1500', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const accountCode = `AS-ACC-${stamp}`
    const sessionCode = `AS-SES-${stamp}`

    await registerBound(page, accountCode, `账号反查显示器-${stamp}`, 'AC-E2E-FIN')
    await registerBound(page, sessionCode, `场次反查灯-${stamp}`, '', SESSION)

    await page.locator('.qbar input').first().fill(accountCode)
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await filtered

    await page.getByTestId('corp-asset-entry-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('asset-entry-account-no').fill('AC-NO-SUCH-72')
    const missingAccount = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await drawer.getByTestId('asset-entry-query').click()
    expect((await (await missingAccount).json() as { code: number }).code).toBe(1500)
    await expect(drawer.getByTestId('asset-entry-error')).toContainText('1500')
    await expect(drawer.getByTestId('asset-entry-error')).toContainText('账号不存在')
    await page.screenshot({ path: `${shotDir}/01-account-missing-1500.png`, fullPage: true })

    await drawer.getByTestId('asset-entry-account-no').fill('AC-E2E-FIN')
    const accountResp = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await drawer.getByTestId('asset-entry-query').click()
    const accountBody = (await (await accountResp).json()) as { code: number; data?: { summary?: { inUse?: number } } }
    expect(accountBody.code).toBe(0)
    await expect(drawer.getByTestId('asset-entry-summary')).toContainText('命中')
    const accountRow = drawer.locator('tr', { hasText: accountCode })
    const sessionOnAccount = drawer.locator('tr', { hasText: sessionCode })
    await expect(accountRow.getByTestId('asset-entry-status')).toHaveText('待审核')
    await expect(sessionOnAccount.getByTestId('asset-entry-status')).toHaveText('待审核')
    await page.screenshot({ path: `${shotDir}/02-account-pending.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: accountCode })
    await expect(row).toBeVisible()
    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect((await (await checkoutResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')

    await page.getByTestId('corp-asset-entry-open').click()
    const again = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await again.getByTestId('asset-entry-account-no').fill('AC-E2E-FIN')
    const inUseResp = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await again.getByTestId('asset-entry-query').click()
    const inUseBody = (await (await inUseResp).json()) as { code: number; data?: { summary?: { inUse?: number } } }
    expect(inUseBody.code).toBe(0)
    expect(inUseBody.data?.summary?.inUse).toBeGreaterThanOrEqual(1)
    await expect(again.locator('tr', { hasText: accountCode }).getByTestId('asset-entry-status')).toHaveText('在用')
    await expect(again.getByTestId('asset-entry-summary')).toContainText('在用')
    await page.screenshot({ path: `${shotDir}/03-account-in-use.png`, fullPage: true })

    await again.getByTestId('asset-entry-session').click()
    await again.getByTestId('asset-entry-session-code').fill('IMS20261008AAA0001')
    const missingSession = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-session/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await again.getByTestId('asset-entry-query').click()
    expect((await (await missingSession).json() as { code: number }).code).toBe(1500)
    await expect(again.getByTestId('asset-entry-error')).toContainText('场次不存在')
    await page.screenshot({ path: `${shotDir}/04-session-missing-1500.png`, fullPage: true })

    await again.getByTestId('asset-entry-session-code').fill(SESSION)
    const sessionResp = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-session/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await again.getByTestId('asset-entry-query').click()
    const sessionBody = (await (await sessionResp).json()) as { code: number }
    expect(sessionBody.code).toBe(0)
    await expect(again.locator('tr', { hasText: sessionCode }).getByTestId('asset-entry-status')).toHaveText('待审核')
    await expect(again.locator('tr', { hasText: accountCode })).toHaveCount(0)
    await expect(again.getByTestId('asset-entry-summary')).toContainText('命中 1 条')
    await page.screenshot({ path: `${shotDir}/05-session-pending.png`, fullPage: true })
    await again.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('corp-asset-detail-btn').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(detail.getByTestId('corp-asset-timeline')).toContainText('绑定账号 AC-E2E-FIN')
    expect(pageErrors).toEqual([])
  })
})