import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-63-screenshots'

/** Checklist **E2E-S5-02**（#63 · 纯 UI）· 领用 → 使用 → 归还 → 报废 */
test.describe('corp asset lifecycle closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('register then checkout use return and scrap through visible status', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const code = `AS-E2E-${stamp}`
    const name = `E2E显示器-${stamp}`

    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(name)
    await create.getByTestId('corp-asset-spec').fill('27寸')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/checkout') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    const saved = (await (await saveResp).json()) as { code: number; data?: { status?: string } }
    expect(saved.code).toBe(0)
    expect(saved.data?.status).toBe('PENDING_REVIEW')
    await expect(create).toBeHidden()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await expect(row.getByTestId('corp-asset-status')).toHaveText('待审核')
    await page.screenshot({ path: `${shotDir}/01-registered-pending.png`, fullPage: true })

    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await expect(checkout).toBeVisible()
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    const checked = (await (await checkoutResp).json()) as { code: number; data?: { status?: string } }
    expect(checked.code).toBe(0)
    expect(checked.data?.status).toBe('IN_USE')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')
    await expect(row).toContainText('管理员')
    await page.screenshot({ path: `${shotDir}/02-checked-out-in-use.png`, fullPage: true })

    await row.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    await expect(useDrawer).toBeVisible()
    await useDrawer.getByTestId('corp-asset-use-remark').fill('现场使用')
    const useResp = page.waitForResponse(
      (r) => r.url().includes('/use') && r.request().method() === 'POST' && r.status() === 200,
    )
    await useDrawer.getByTestId('corp-asset-use-save').click()
    const used = (await (await useResp).json()) as { code: number; data?: { status?: string } }
    expect(used.code).toBe(0)
    expect(used.data?.status).toBe('IN_USE')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')

    await row.getByTestId('corp-asset-detail-btn').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(detail).toBeVisible()
    const timeline = detail.getByTestId('corp-asset-timeline')
    await expect(timeline).toContainText('领用')
    await expect(timeline).toContainText('使用')
    await expect(timeline).toContainText('现场使用')
    await page.screenshot({ path: `${shotDir}/03-used-timeline.png`, fullPage: true })
    await detail.getByRole('button', { name: '关闭' }).click()
    await expect(detail).toBeHidden()

    await row.getByTestId('corp-asset-return-btn').click()
    const returnDrawer = page.locator('.drawer.on').filter({ hasText: '归还' })
    await expect(returnDrawer).toBeVisible()
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/return') && r.request().method() === 'POST' && r.status() === 200,
    )
    await returnDrawer.getByTestId('corp-asset-return-save').click()
    const returned = (await (await returnResp).json()) as { code: number; data?: { status?: string } }
    expect(returned.code).toBe(0)
    expect(returned.data?.status).toBe('RETURNED')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')
    await page.screenshot({ path: `${shotDir}/04-returned.png`, fullPage: true })

    await row.getByTestId('corp-asset-scrap-btn').click()
    const scrap = page.locator('.drawer.on').filter({ hasText: '报废' })
    await expect(scrap).toBeVisible()
    await scrap.getByTestId('corp-asset-scrap-reason').fill('无法修复')
    const scrapResp = page.waitForResponse(
      (r) => r.url().includes('/scrap') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scrap.getByTestId('corp-asset-scrap-save').click()
    const scrapped = (await (await scrapResp).json()) as { code: number; data?: { status?: string } }
    expect(scrapped.code).toBe(0)
    expect(scrapped.data?.status).toBe('SCRAPPED')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已报废')
    await expect(row.getByTestId('corp-asset-checkout-btn')).toHaveCount(0)
    await expect(row.getByTestId('corp-asset-scrap-btn')).toHaveCount(0)

    await row.getByTestId('corp-asset-detail-btn').click()
    const done = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(done.getByTestId('corp-asset-detail-status')).toHaveText('已报废')
    const doneLine = done.getByTestId('corp-asset-timeline')
    await expect(doneLine).toContainText('登记')
    await expect(doneLine).toContainText('领用')
    await expect(doneLine).toContainText('使用')
    await expect(doneLine).toContainText('归还')
    await expect(doneLine).toContainText('报废')
    await page.screenshot({ path: `${shotDir}/05-scrapped-timeline.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
