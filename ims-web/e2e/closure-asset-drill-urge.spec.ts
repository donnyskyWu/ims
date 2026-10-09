import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-181-screenshots'

/** #181 · 正向穿透无场次空态、未使用不可归还、校验逾期钉钉本地桩说明 */
test.describe('corp asset drill-through empty and return edge', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('forward drill shows no session, return stays blocked until use, verify names the dingtalk stub', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const code = `AS-181-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`空场次显示器-${stamp}`)
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect((await (await saveResp).json() as { code: number }).code).toBe(0)
    await expect(create).toBeHidden()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    const detailResp = page.waitForResponse(
      (r) => /\/asset\/forward\/detail\/[1-9]\d*/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row.getByTestId('corp-asset-forward-btn').click()
    const forward = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    await expect(forward).toBeVisible()
    expect((await (await detailResp).json() as { code: number }).code).toBe(0)
    await expect(forward.getByTestId('asset-forward-session-empty')).toHaveText('该资产没有关联场次')
    await expect(forward.getByTestId('asset-forward-sessions')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/01-forward-no-session.png`, fullPage: true })
    await forward.getByRole('button', { name: '关闭' }).click()
    await expect(forward).toBeHidden()

    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect((await (await checkoutResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')

    await row.getByTestId('corp-asset-return-btn').click()
    const blocked = page.locator('.drawer.on').filter({ hasText: '归还' })
    await expect(blocked.getByTestId('corp-asset-return-blocked')).toHaveText('尚未登记使用，不能归还。请先登记使用。')
    await expect(blocked.getByTestId('corp-asset-return-save')).toBeDisabled()
    await page.screenshot({ path: `${shotDir}/02-return-blocked.png`, fullPage: true })
    await blocked.getByRole('button', { name: '取消' }).click()
    await expect(blocked).toBeHidden()

    await row.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    await useDrawer.getByTestId('corp-asset-use-remark').fill('现场使用')
    const useResp = page.waitForResponse(
      (r) => r.url().includes('/use') && r.request().method() === 'POST' && r.status() === 200,
    )
    await useDrawer.getByTestId('corp-asset-use-save').click()
    expect((await (await useResp).json() as { code: number }).code).toBe(0)
    await expect(useDrawer).toBeHidden()

    await row.getByTestId('corp-asset-return-btn').click()
    const ready = page.locator('.drawer.on').filter({ hasText: '归还' })
    await expect(ready.getByTestId('corp-asset-return-ready')).toHaveText('已登记使用，可以归还入库。')
    await expect(ready.getByTestId('corp-asset-return-blocked')).toHaveCount(0)
    await expect(ready.getByTestId('corp-asset-return-save')).toBeEnabled()
    await page.screenshot({ path: `${shotDir}/03-return-ready.png`, fullPage: true })
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/return') && r.request().method() === 'POST' && r.status() === 200,
    )
    await ready.getByTestId('corp-asset-return-save').click()
    expect((await (await returnResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')

    const board = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/batches') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-asset-verify-open').click()
    await board
    const verify = page.locator('.drawer.on').filter({ hasText: '登记关联校验' })
    await expect(verify.getByTestId('asset-verify-dingtalk')).toHaveText('逾期未闭环会升级部门负责人。钉钉通知为本地桩，未外发。')
    await page.screenshot({ path: `${shotDir}/04-verify-dingtalk-stub.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
