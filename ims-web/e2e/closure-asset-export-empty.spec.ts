import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-167-screenshots'
const EMPTY_ACCOUNT = 'AC-E2E-ASSET-OFF'

function xlsxRows(filePath: string): string[][] {
  const script = `
import json, sys, zipfile
from xml.etree import ElementTree
ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
root = ElementTree.fromstring(zipfile.ZipFile(sys.argv[1]).read("xl/worksheets/sheet1.xml"))
rows = []
for row in root.findall("m:sheetData/m:row", ns):
    cells = []
    for cell in row.findall("m:c", ns):
        node = cell.find("m:is/m:t", ns)
        cells.append("" if node is None or node.text is None else node.text)
    rows.append(cells)
print(json.dumps(rows, ensure_ascii=False))
`
  return JSON.parse(execFileSync('python3', ['-c', script, filePath], { encoding: 'utf8' }))
}

async function registerAsset(page: Page, code: string, name: string) {
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  await create.getByTestId('corp-asset-code').fill(code)
  await create.getByTestId('corp-asset-name').fill(name)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  const saved = (await (await saveResp).json()) as { code: number }
  expect(saved.code).toBe(0)
  await expect(create).toBeHidden()
}

/** #167 · 反查空态、场次格式前置拦截、空 xlsx、已归还开关 */
test.describe('corp asset reverse empty export closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('reverse drawer guides before query, blocks a bad session code, and exports an empty stub', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const reverseCalls: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/asset/reverse/')) reverseCalls.push(request.url())
    })

    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    await page.getByTestId('corp-asset-entry-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('asset-entry-guide')).toHaveText('请选择入口维度并输入查询条件')
    await expect(drawer.getByTestId('asset-entry-table')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/01-reverse-guide.png`, fullPage: true })

    await drawer.getByTestId('asset-entry-session').click()
    await drawer.getByTestId('asset-entry-session-code').fill('not-a-session')
    const before = reverseCalls.length
    await drawer.getByTestId('asset-entry-query').click()
    await expect(drawer.getByTestId('asset-entry-error')).toHaveText('场次编号格式不正确')
    expect(reverseCalls.length).toBe(before)
    await page.screenshot({ path: `${shotDir}/02-session-format.png`, fullPage: true })

    await drawer.getByTestId('asset-entry-account').click()
    await drawer.getByTestId('asset-entry-account-no').fill(EMPTY_ACCOUNT)
    const emptyQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await drawer.getByTestId('asset-entry-query').click()
    const emptyBody = (await (await emptyQuery).json()) as { code: number; data?: { summary?: { total?: number } } }
    expect(emptyBody.code).toBe(0)
    expect(emptyBody.data?.summary?.total).toBe(0)
    await expect(drawer.getByTestId('asset-entry-summary')).toContainText('命中 0 条')
    await expect(drawer.getByTestId('asset-entry-table')).toContainText('没有绑定资产')
    await page.screenshot({ path: `${shotDir}/03-empty-account.png`, fullPage: true })

    const downloadPromise = page.waitForEvent('download')
    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await drawer.getByTestId('asset-entry-export').click()
    const exported = (await (await exportResp).json()) as { code: number; data?: { empty?: boolean; fileName?: string } }
    expect(exported.code).toBe(0)
    expect(exported.data?.empty).toBe(true)
    expect(exported.data?.fileName).toBe('asset_reverse_report.xlsx')
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('asset_reverse_report.xlsx')
    const xlsxPath = `${shotDir}/asset_reverse_empty.xlsx`
    await download.saveAs(xlsxPath)
    expect(fs.readFileSync(xlsxPath).subarray(0, 2).toString()).toBe('PK')
    const rows = xlsxRows(xlsxPath)
    expect(rows[0][0]).toBe('汇总')
    expect(rows[0][1]).toContain('命中 0 条')
    expect(rows[2][0]).toBe('暂无绑定资产')
    await expect(drawer.getByTestId('asset-export-note')).toHaveText('已导出空表（命中 0 条）')
    await page.screenshot({ path: `${shotDir}/04-empty-export.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()

    const stamp = Date.now()
    const code = `AS-H167-${stamp}`
    await registerAsset(page, code, `历史归还-${stamp}`)
    await page.locator('.qbar input').first().fill(code)
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    await filtered
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await row.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-owner').selectOption({ label: '管理员' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    await checkout.getByTestId('corp-asset-checkout-save').click()
    await expect(row.getByTestId('corp-asset-status')).toHaveText('在用')
    await row.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    await useDrawer.getByTestId('corp-asset-use-remark').fill('现场使用')
    await useDrawer.getByTestId('corp-asset-use-save').click()
    await expect(useDrawer).toBeHidden()
    await row.getByTestId('corp-asset-return-btn').click()
    const returnDrawer = page.locator('.drawer.on').filter({ hasText: '归还' })
    await returnDrawer.getByTestId('corp-asset-return-save').click()
    await expect(row.getByTestId('corp-asset-status')).toHaveText('已归还')

    await page.getByTestId('corp-asset-entry-open').click()
    const personDrawer = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await personDrawer.getByTestId('asset-entry-person').click()
    await expect(personDrawer.getByTestId('asset-entry-include-history').locator('input')).toBeChecked()
    await personDrawer.getByTestId('asset-entry-user').selectOption({ label: '管理员' })
    const historyQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-person/') && r.url().includes('includeHistory=true') && r.status() === 200,
    )
    await personDrawer.getByTestId('asset-entry-query').click()
    expect((await (await historyQuery).json() as { code: number }).code).toBe(0)
    await expect(personDrawer.locator('tr', { hasText: code }).getByTestId('asset-entry-status')).toHaveText('已归还')
    await page.screenshot({ path: `${shotDir}/05-history-on.png`, fullPage: true })

    await personDrawer.getByTestId('asset-entry-include-history').locator('input').uncheck()
    const currentQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-person/') && r.url().includes('includeHistory=false') && r.status() === 200,
    )
    await personDrawer.getByTestId('asset-entry-query').click()
    expect((await (await currentQuery).json() as { code: number }).code).toBe(0)
    await expect(personDrawer.locator('tr', { hasText: code })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/06-history-off.png`, fullPage: true })

    const hiddenDownload = page.waitForEvent('download')
    await personDrawer.getByTestId('asset-entry-export').click()
    const hiddenFile = await hiddenDownload
    const hiddenPath = `${shotDir}/asset_reverse_history_off.xlsx`
    await hiddenFile.saveAs(hiddenPath)
    expect(xlsxRows(hiddenPath).some((line) => line[0] === code)).toBe(false)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
