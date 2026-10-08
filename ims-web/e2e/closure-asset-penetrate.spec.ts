import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-65-screenshots'

async function registerAsset(
  page: Page,
  code: string,
  name: string,
  opts: { realnameValue?: string; parent?: string } = {},
) {
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  await create.getByTestId('corp-asset-code').fill(code)
  await create.getByTestId('corp-asset-name').fill(name)
  if (opts.parent) await create.getByTestId('corp-asset-parent').fill(opts.parent)
  else if (opts.realnameValue) await create.getByTestId('corp-asset-realname').selectOption(opts.realnameValue)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/checkout') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  const saved = (await (await saveResp).json()) as { code: number }
  expect(saved.code).toBe(0)
  await expect(create).toBeHidden()
}

/** Checklist **E2E-S5-03 / E2E-S5-04**（#65 · 纯 UI） */
test.describe('corp asset penetration closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('forward penetration returns the chain within five layers and 1013 beyond', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const codeOf = (level: number) => `AS-PEN-${stamp}-${level}`

    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    const select = create.getByTestId('corp-asset-realname')
    await expect.poll(async () => select.locator('option').count()).toBeGreaterThan(1)
    const personValue = await select.locator('option').nth(1).getAttribute('value')
    const personLabel = (await select.locator('option').nth(1).innerText()).trim()
    expect(personValue).toBeTruthy()
    await create.getByRole('button', { name: '取消' }).click()
    await expect(create).toBeHidden()

    await registerAsset(page, codeOf(1), `穿透层1-${stamp}`, { realnameValue: personValue! })
    for (let level = 2; level <= 5; level += 1) {
      await registerAsset(page, codeOf(level), `穿透层${level}-${stamp}`, { parent: codeOf(level - 1) })
    }

    await page.getByTestId('corp-asset-forward-open').click()
    const forward = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    await expect(forward).toBeVisible()
    await forward.getByTestId('asset-forward-realname').selectOption(personValue!)
    const okResp = page.waitForResponse(
      (r) => r.url().includes('/asset/forward/trace/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await forward.getByTestId('asset-forward-query').click()
    const within = (await (await okResp).json()) as { code: number; data?: { depth?: number } }
    expect(within.code).toBe(0)
    expect(within.data?.depth).toBe(5)
    const chain = forward.getByTestId('asset-forward-chain')
    await expect(chain).toBeVisible()
    await expect(forward.getByTestId('asset-forward-node')).toHaveCount(6)
    await expect(chain).toContainText(personLabel)
    await expect(chain).toContainText('实名人')
    for (let level = 1; level <= 5; level += 1) {
      await expect(chain).toContainText(`第${level}层`)
      await expect(chain).toContainText(codeOf(level))
    }
    await page.screenshot({ path: `${shotDir}/01-forward-five-layers.png`, fullPage: true })
    await forward.getByRole('button', { name: '关闭' }).click()
    await expect(forward).toBeHidden()

    await registerAsset(page, codeOf(6), `穿透层6-${stamp}`, { parent: codeOf(5) })
    await page.getByTestId('corp-asset-forward-open').click()
    const again = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    await expect(again).toBeVisible()
    await again.getByTestId('asset-forward-realname').selectOption(personValue!)
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/asset/forward/trace/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await again.getByTestId('asset-forward-query').click()
    const blocked = (await (await blockedResp).json()) as { code: number }
    expect(blocked.code).toBe(1013)
    await expect(again.getByTestId('asset-forward-error')).toContainText('1013')
    await expect(again.getByTestId('asset-forward-chain')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-forward-1013.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('reverse penetration distinguishes in-use returned and scrapped holders', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const code = `AS-REV-${stamp}`
    await registerAsset(page, code, `反向显示器-${stamp}`)
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
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

    await row.getByTestId('corp-asset-reverse-btn').click()
    const reverse = page.locator('.drawer.on').filter({ hasText: '反向穿透' })
    await expect(reverse.getByTestId('asset-reverse-status')).toHaveText(['在用'])
    await expect(reverse.getByTestId('asset-reverse-user')).toHaveText(['管理员'])
    await page.screenshot({ path: `${shotDir}/03-reverse-in-use.png`, fullPage: true })
    await reverse.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    await useDrawer.getByTestId('corp-asset-use-remark').fill('现场使用')
    await useDrawer.getByTestId('corp-asset-use-save').click()
    await expect(useDrawer).toBeHidden()

    await row.getByTestId('corp-asset-return-btn').click()
    const returnDrawer = page.locator('.drawer.on').filter({ hasText: '归还' })
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/return') && r.request().method() === 'POST' && r.status() === 200,
    )
    await returnDrawer.getByTestId('corp-asset-return-save').click()
    expect((await (await returnResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')

    await row.getByTestId('corp-asset-reverse-btn').click()
    const returned = page.locator('.drawer.on').filter({ hasText: '反向穿透' })
    await expect(returned.getByTestId('asset-reverse-status')).toHaveText(['在用', '已归还'])
    await page.screenshot({ path: `${shotDir}/04-reverse-returned.png`, fullPage: true })
    await returned.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('corp-asset-scrap-btn').click()
    const scrap = page.locator('.drawer.on').filter({ hasText: '报废' })
    await scrap.getByTestId('corp-asset-scrap-reason').fill('无法修复')
    const scrapResp = page.waitForResponse(
      (r) => r.url().includes('/scrap') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scrap.getByTestId('corp-asset-scrap-save').click()
    expect((await (await scrapResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已报废')

    await row.getByTestId('corp-asset-reverse-btn').click()
    const done = page.locator('.drawer.on').filter({ hasText: '反向穿透' })
    await expect(done.getByTestId('asset-reverse-status')).toHaveText(['在用', '已归还', '已报废'])
    await expect(done.getByTestId('asset-reverse-user')).toHaveText(['管理员', '管理员', '管理员'])
    await page.screenshot({ path: `${shotDir}/05-reverse-scrapped.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
