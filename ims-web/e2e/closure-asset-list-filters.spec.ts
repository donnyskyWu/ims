import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/slice-149'

function xlsxText(filePath: string): string {
  const script = `
import sys, zipfile
print(zipfile.ZipFile(sys.argv[1]).read("xl/worksheets/sheet1.xml").decode("utf-8"))
`
  return execFileSync('python3', ['-c', script, filePath], { encoding: 'utf8' })
}

async function registerAsset(page: Page, code: string, name: string, accountNo = '') {
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  await create.getByTestId('corp-asset-code').fill(code)
  await create.getByTestId('corp-asset-name').fill(name)
  if (accountNo) await create.getByTestId('corp-asset-bind-account').fill(accountNo)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  const saved = (await (await saveResp).json()) as { code: number }
  expect(saved.code).toBe(0)
  await expect(create).toBeHidden()
}

/** #149 · 办公设备列表按责任人 / 待补关联筛选，并导出当前结果 */
test.describe('corp asset list filters closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('office ledger filters by owner and link gap then exports the current rows', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    await expect(page.getByTestId('corp-asset-owner-filter')).toBeVisible()
    await expect(page.getByTestId('corp-asset-link-gap-banner')).toBeVisible()

    const stamp = Date.now()
    const gapCode = `AS-FLT-${stamp}-G`
    const keptCode = `AS-FLT-${stamp}-K`
    const gapName = `待补关联显示器-${stamp}`
    const keptName = `已关联显示器-${stamp}`

    await registerAsset(page, gapCode, gapName)
    await registerAsset(page, keptCode, keptName, 'AC-E2E-FIN')

    const keyword = page.locator('.qbar input').first()
    await keyword.fill(`AS-FLT-${stamp}`)
    const listed = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    expect((await (await listed).json() as { code: number }).code).toBe(0)

    const gapRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: gapCode })
    const keptRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: keptCode })
    await expect(gapRow).toBeVisible()
    await expect(keptRow).toBeVisible()
    await expect(gapRow.getByTestId('corp-asset-bind-count')).toContainText('0')
    await expect(gapRow.getByTestId('corp-asset-link-gap')).toHaveText('待补关联')
    await expect(keptRow.getByTestId('corp-asset-bind-count')).toContainText('1')
    await expect(keptRow.getByTestId('corp-asset-link-gap')).toHaveText('待补关联')
    await page.screenshot({ path: `${shotDir}/01-both-pending-link.png`, fullPage: true })

    await keptRow.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await expect(checkout).toBeVisible()
    await checkout.getByTestId('corp-asset-owner').selectOption({ label: '管理员' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect((await (await checkoutResp).json() as { code: number }).code).toBe(0)
    await expect(keptRow.getByTestId('corp-asset-status')).toHaveText('在用')
    await expect(keptRow.getByTestId('corp-asset-link-gap')).toHaveCount(0)
    await expect(keptRow).toContainText('管理员')
    await page.screenshot({ path: `${shotDir}/02-kept-in-use.png`, fullPage: true })

    await page.getByTestId('corp-asset-owner-filter').selectOption({ label: '管理员' })
    const owned = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.url().includes('ownerUserId=') && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    expect((await (await owned).json() as { code: number }).code).toBe(0)
    await expect(keptRow).toBeVisible()
    await expect(gapRow).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-owner-filter.png`, fullPage: true })

    await page.getByTestId('corp-asset-owner-filter').selectOption({ label: '全部责任人' })
    await page.getByTestId('corp-asset-link-gap-entry').click()
    await expect(page.getByTestId('corp-asset-link-gap-filter').locator('input')).toBeChecked()
    await expect(gapRow).toBeVisible()
    await expect(keptRow).toHaveCount(0)
    await expect(page.getByTestId('corp-asset-link-gap-banner')).toContainText('待补关联')
    await page.screenshot({ path: `${shotDir}/04-link-gap-only.png`, fullPage: true })

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('corp-asset-ledger-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('asset_ledger.xlsx')
    const filePath = `${shotDir}/asset_ledger.xlsx`
    await download.saveAs(filePath)
    expect(fs.readFileSync(filePath).subarray(0, 2).toString()).toBe('PK')
    const sheet = xlsxText(filePath)
    expect(sheet).toContain(gapCode)
    expect(sheet).not.toContain(keptCode)
    expect(sheet).toContain('待补关联')
    await expect(page.getByTestId('corp-asset-ledger-export-note')).toContainText('台账已按当前筛选导出')
    await expect(page.getByTestId('corp-asset-ledger-export-note')).toContainText('asset_ledger.xlsx')
    await page.screenshot({ path: `${shotDir}/05-export-note.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
