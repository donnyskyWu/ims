import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-200-screenshots'

/** #200 校验空批次、今日补跑空扫提示，以及终态不能再领用、空原因不能报废。 */
test.describe('asset verify and lifecycle local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty verify batch, schedule catch-up, and terminal lifecycle edges', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const board = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/batches') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-asset-verify-open').click()
    await board
    const verify = page.locator('.drawer.on').filter({ hasText: '登记关联校验' })
    await expect(verify).toBeVisible()
    await expect(verify.getByTestId('asset-verify-schedule-today')).toContainText('今日已补跑')
    await expect(verify.getByTestId('asset-verify-schedule-today')).toContainText(/全量|增量/)
    await expect(verify.getByTestId('asset-verify-counts')).toContainText('待处理异常工单')
    await expect(verify.getByTestId('asset-verify-counts')).toContainText('本周批次')
    await page.screenshot({ path: `${shotDir}/01-schedule-today.png`, fullPage: true })

    await verify.getByTestId('asset-verify-batch-filter').fill('AV-NO-SUCH-200')
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/batches') && r.url().includes('AV-NO-SUCH-200') && r.status() === 200,
    )
    await verify.getByTestId('asset-verify-batch-query').click()
    await filtered
    await expect(verify.getByTestId('asset-verify-filter-empty')).toHaveText('没有符合条件的校验批次')
    await page.screenshot({ path: `${shotDir}/02-verify-batch-empty.png`, fullPage: true })
    await verify.getByRole('button', { name: '关闭' }).click()
    await expect(verify).toBeHidden()

    const stamp = Date.now()
    const code = `AS-E2E-200-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`终态边角-${stamp}`)
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect((await (await saveResp).json()).code).toBe(0)
    await expect(create).toBeHidden()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-owner').selectOption({ label: '请选择本地用户' })
    await checkout.getByTestId('corp-asset-checkout-save').click()
    await expect(checkout.getByTestId('corp-asset-checkout-error')).toHaveText('责任人必填')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('待审核')
    await page.screenshot({ path: `${shotDir}/03-checkout-owner-required.png`, fullPage: true })

    await checkout.getByTestId('corp-asset-owner').selectOption({ label: '管理员' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse((r) => r.url().includes('/checkout') && r.request().method() === 'POST')
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect((await (await checkoutResp).json()).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')

    await row.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    const useResp = page.waitForResponse((r) => r.url().includes('/use') && r.request().method() === 'POST')
    await useDrawer.getByTestId('corp-asset-use-save').click()
    expect((await (await useResp).json()).code).toBe(0)
    await expect(useDrawer).toBeHidden()

    await row.getByTestId('corp-asset-return-btn').click()
    const returnDrawer = page.locator('.drawer.on').filter({ hasText: '归还' })
    const returnResp = page.waitForResponse((r) => r.url().includes('/return') && r.request().method() === 'POST')
    await returnDrawer.getByTestId('corp-asset-return-save').click()
    expect((await (await returnResp).json()).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')

    await row.getByTestId('corp-asset-detail-btn').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(detail.getByTestId('corp-asset-terminal')).toHaveText('已归还，不能再领用，只能报废。')
    await page.screenshot({ path: `${shotDir}/04-returned-terminal.png`, fullPage: true })
    await detail.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('corp-asset-scrap-btn').click()
    const scrap = page.locator('.drawer.on').filter({ hasText: '报废' })
    await scrap.getByTestId('corp-asset-scrap-save').click()
    await expect(scrap.getByTestId('corp-asset-scrap-error')).toHaveText('报废原因必填')
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')
    await page.screenshot({ path: `${shotDir}/05-scrap-reason-required.png`, fullPage: true })

    await scrap.getByTestId('corp-asset-scrap-reason').fill('无法修复')
    const scrapResp = page.waitForResponse((r) => r.url().includes('/scrap') && r.request().method() === 'POST')
    await scrap.getByTestId('corp-asset-scrap-save').click()
    expect((await (await scrapResp).json()).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已报废')
    await row.getByTestId('corp-asset-detail-btn').click()
    const closed = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(closed.getByTestId('corp-asset-terminal')).toHaveText('已报废为终态，不能再领用。')
    await page.screenshot({ path: `${shotDir}/06-scrapped-terminal.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
