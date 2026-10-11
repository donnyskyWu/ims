import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

/** BUG-052 · 直播设备行正向穿透：资产 → 账号 → 实名人 → 场次 → 成本 */
test.describe('live asset forward chain closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('row opens the asset to cost chain and keeps reverse lookup', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/ims/corp/device/live')
    await expect(page.locator('h1')).toHaveText('直播设备管理', { timeout: 15_000 })
    await expect(page.getByTestId('corp-asset-entry-open')).toHaveText('账号/场次反查')

    const stamp = Date.now().toString().slice(-6)
    const name = `穿透灯${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on', { hasText: '资产登记' })
    await create.getByTestId('corp-asset-name').fill(name)
    await create.getByTestId('corp-asset-type').selectOption('LIVE')
    const saved = page.waitForResponse(
      (res) => res.url().includes('/asset/ledger') && res.request().method() === 'POST' && res.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    const body = (await (await saved).json()) as { code: number; data?: { assetCode?: string } }
    expect(body.code).toBe(0)
    const code = body.data?.assetCode || ''
    expect(code).toBeTruthy()

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    const layers = page.waitForResponse(
      (res) => res.url().includes('/asset/forward/chain/') && res.url().includes('layer=L1') && res.status() === 200,
    )
    await row.getByTestId('corp-asset-chain-btn').click()
    const drawer = page.locator('.drawer.on', { hasText: '正向穿透' })
    await expect(drawer).toBeVisible()
    const layer = (await (await layers).json()) as { code: number; data?: { asset?: { assetName?: string } } }
    expect(layer.code).toBe(0)
    expect(layer.data?.asset?.assetName).toBe(name)
    await expect(drawer.getByTestId('corp-asset-chain-l1')).toContainText(code)
    await expect(drawer.getByTestId('corp-asset-chain-l1')).toContainText('直播设备')
    await expect(drawer.getByTestId('corp-asset-chain-accounts')).toContainText('没有绑定账号')
    await expect(drawer.getByTestId('corp-asset-chain-persons')).toContainText('没有实名人')
    await expect(drawer.getByTestId('corp-asset-chain-sessions')).toContainText('没有使用场次')
    await expect(drawer.getByTestId('corp-asset-chain-cost-amount')).toHaveText('¥0.00')
    await drawer.getByTestId('corp-asset-chain-tab-graph').click()
    await expect(drawer.getByTestId('corp-asset-chain-graph')).toContainText('资产')
    await expect(drawer.getByTestId('corp-asset-chain-graph')).toContainText('成本')
  })
})
