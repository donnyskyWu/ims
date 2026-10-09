import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-220-screenshots'

function xlsxText(filePath: string): string {
  const script = `
import sys, zipfile
print(zipfile.ZipFile(sys.argv[1]).read("xl/worksheets/sheet1.xml").decode("utf-8"))
`
  return execFileSync('python3', ['-c', script, filePath], { encoding: 'utf8' })
}

async function queryLedger(page: Page, pathPart: string, keyword: string) {
  const listed = page.waitForResponse(
    (r) =>
      r.url().includes(pathPart) &&
      r.url().includes(encodeURIComponent(keyword)) &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.locator('form.qbar button[type="submit"]').click()
  expect((await (await listed).json() as { code: number }).code).toBe(0)
}

/** #220 · 办公/直播筛选空态、空台账导出、无场次成本说明 */
test.describe('corp asset list filter empty and export edge', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filtered office and live lists name the miss, empty export says zero, forward cost stays zero', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const missing = `AS-220-NONE-${stamp}`
    await page.getByTestId('corp-asset-keyword').fill(missing)
    await page.getByTestId('corp-asset-status-filter').selectOption('SCRAPPED')
    await page.getByTestId('corp-asset-owner-filter').selectOption('none')
    await page.getByTestId('corp-asset-link-gap-filter').locator('input').check()
    await queryLedger(page, '/corp/device/office/page', missing)
    const officeEmpty = page.getByTestId('corp-asset-list-empty')
    await expect(officeEmpty).toContainText('没有符合筛选的记录')
    await expect(page.getByTestId('corp-asset-list-empty-hint')).toHaveText('换个编号、责任人、状态或待补关联，或点重置。')
    await expect(officeEmpty).not.toContainText('没有办公设备')
    await page.screenshot({ path: `${shotDir}/01-office-filter-empty.png`, fullPage: true })

    const downloadPromise = page.waitForEvent('download')
    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await page.getByTestId('corp-asset-ledger-export').click()
    const exported = (await (await exportResp).json()) as {
      code: number
      data?: { empty?: boolean; message?: string; exported?: number; fileName?: string }
    }
    expect(exported.code).toBe(0)
    expect(exported.data?.empty).toBe(true)
    expect(exported.data?.exported).toBe(0)
    expect(exported.data?.message).toBe('已导出空台账（当前筛选命中 0 条）')
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('asset_ledger.xlsx')
    const xlsxPath = `${shotDir}/asset_ledger_empty.xlsx`
    await download.saveAs(xlsxPath)
    expect(fs.readFileSync(xlsxPath).subarray(0, 2).toString()).toBe('PK')
    const sheet = xlsxText(xlsxPath)
    expect(sheet).toContain('暂无资产记录')
    expect(sheet).not.toContain(missing)
    await expect(page.getByTestId('corp-asset-ledger-export-note')).toHaveText(
      '已导出空台账（当前筛选命中 0 条） · asset_ledger.xlsx',
    )
    await page.screenshot({ path: `${shotDir}/02-office-empty-export.png`, fullPage: true })

    const reset = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/device/office/page') &&
        !r.url().includes(encodeURIComponent(missing)) &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.locator('form.qbar').getByRole('button', { name: '重置' }).click()
    await reset
    await expect(page.locator('.empty .et', { hasText: '没有符合筛选的记录' })).toHaveCount(0)
    await expect(page.getByTestId('corp-asset-keyword')).toHaveValue('')

    await page.goto('/ims/corp/device/live')
    await expect(page.locator('h1')).toHaveText('直播设备管理', { timeout: 15_000 })
    await page.getByTestId('corp-asset-keyword').fill(missing)
    await page.getByTestId('corp-asset-type-filter').selectOption('SHOOT')
    await queryLedger(page, '/corp/device/live/page', missing)
    await expect(page.getByTestId('corp-asset-list-empty')).toContainText('没有符合筛选的记录')
    await expect(page.getByTestId('corp-asset-list-empty-hint')).toHaveText(
      '换个编号、类型、责任人、状态或待补关联，或点重置。',
    )
    await page.screenshot({ path: `${shotDir}/03-live-type-filter-empty.png`, fullPage: true })
    const liveExport = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    const liveDownload = page.waitForEvent('download')
    await page.getByTestId('corp-asset-ledger-export').click()
    expect((await (await liveExport).json() as { data?: { empty?: boolean } }).data?.empty).toBe(true)
    await liveDownload
    await expect(page.getByTestId('corp-asset-ledger-export-note')).toContainText('已导出空台账（当前筛选命中 0 条）')

    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    const code = `AS-220-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`无场次显示器-${stamp}`)
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
    await expect(forward.getByTestId('asset-forward-cost-empty')).toHaveText('没有关联场次，成本与收入记为 0')
    await expect(forward.getByTestId('asset-forward-finance')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/04-forward-cost-empty.png`, fullPage: true })

    const pdfDownload = page.waitForEvent('download')
    const pdfResp = page.waitForResponse(
      (r) => r.url().includes('/asset/forward/export/') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await forward.getByTestId('asset-forward-export').click()
    const pdf = (await (await pdfResp).json()) as { code: number; data?: { empty?: boolean } }
    expect(pdf.code).toBe(0)
    expect(pdf.data?.empty).toBe(false)
    await pdfDownload
    await expect(forward.getByTestId('asset-export-note')).toHaveText('已导出穿透报告 PDF（该资产没有关联场次）')
    await page.screenshot({ path: `${shotDir}/05-forward-export-note.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
