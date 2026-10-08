import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-74-screenshots'
const SESSION = 'IMS20261008DYE0072'

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

function pdfText(filePath: string): string {
  const script = `
from pypdf import PdfReader
import sys
print(PdfReader(sys.argv[1]).pages[0].extract_text() or "")
`
  return execFileSync('python3', ['-c', script, filePath], { encoding: 'utf8' })
}

async function registerAsset(
  page: Page,
  code: string,
  name: string,
  opts: { realnameValue?: string; parent?: string; accountNo?: string; sessionCode?: string } = {},
) {
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  await create.getByTestId('corp-asset-code').fill(code)
  await create.getByTestId('corp-asset-name').fill(name)
  if (opts.parent) await create.getByTestId('corp-asset-parent').fill(opts.parent)
  else if (opts.realnameValue) await create.getByTestId('corp-asset-realname').selectOption(opts.realnameValue)
  if (opts.accountNo) await create.getByTestId('corp-asset-bind-account').fill(opts.accountNo)
  if (opts.sessionCode) await create.getByTestId('corp-asset-bind-session').fill(opts.sessionCode)
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  const saved = (await (await saveResp).json()) as { code: number }
  expect(saved.code).toBe(0)
  await expect(create).toBeHidden()
}

/** Checklist **E2E-S5-06**（#74 · 纯 UI · 穿透报告 PDF / 反查 xlsx） */
test.describe('corp asset export closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('office page exports the penetration PDF and reverse xlsx for person account and session', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const codeOf = (level: number) => `AS-EX-${stamp}-${level}`

    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    const select = create.getByTestId('corp-asset-realname')
    await expect.poll(async () => select.locator('option').count()).toBeGreaterThan(1)
    const personValue = await select.locator('option').nth(1).getAttribute('value')
    expect(personValue).toBeTruthy()
    await create.getByRole('button', { name: '取消' }).click()
    await expect(create).toBeHidden()

    await registerAsset(page, codeOf(1), `导出层1-${stamp}`, { realnameValue: personValue! })
    for (let level = 2; level <= 5; level += 1) {
      await registerAsset(page, codeOf(level), `导出层${level}-${stamp}`, { parent: codeOf(level - 1) })
    }

    await page.locator('.qbar input').first().fill(codeOf(5))
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    await filtered

    const row5 = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: codeOf(5) })
    await expect(row5).toBeVisible()
    const traceResp = page.waitForResponse(
      (r) => /\/asset\/forward\/trace\/[1-9]\d*/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row5.getByTestId('corp-asset-forward-btn').click()
    const forward = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    await expect(forward).toBeVisible()
    const traced = (await (await traceResp).json()) as { code: number }
    expect(traced.code).toBe(0)
    const chain = forward.getByTestId('asset-forward-chain')
    await expect(chain).toContainText('第5层')
    await expect(chain).toContainText(codeOf(5))
    const exportBtn = forward.getByTestId('asset-forward-export')
    await expect(exportBtn).toBeVisible()
    await page.screenshot({ path: `${shotDir}/01-forward-export-button.png`, fullPage: true })

    const nodeLines = (await forward.getByTestId('asset-forward-node').allInnerTexts()).map((line) => line.trim())
    const downloadPromise = page.waitForEvent('download')
    const exportResp = page.waitForResponse(
      (r) => /\/asset\/forward\/export\/[1-9]\d*/.test(r.url()) && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await exportBtn.click()
    const exported = (await (await exportResp).json()) as { code: number; data?: { fileName?: string; message?: string } }
    expect(exported.code).toBe(0)
    expect(exported.data?.fileName).toBe('asset_forward_report.pdf')
    expect(exported.data?.message).toBe('穿透报告已生成')
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('asset_forward_report.pdf')
    const pdfPath = `${shotDir}/asset_forward_report.pdf`
    await download.saveAs(pdfPath)
    const pdfBytes = fs.readFileSync(pdfPath)
    expect(pdfBytes.subarray(0, 5).toString()).toBe('%PDF-')
    const text = pdfText(pdfPath)
    expect(text).toContain('资产穿透报告')
    for (const line of nodeLines) expect(text).toContain(line)
    await expect(forward.getByTestId('asset-export-note')).toContainText('已导出穿透报告 PDF')
    await page.screenshot({ path: `${shotDir}/02-forward-export-success.png`, fullPage: true })
    await forward.getByRole('button', { name: '关闭' }).click()

    await page.locator('.qbar input').first().fill('')
    await page.locator('.qbar button[type="submit"]').click()
    await registerAsset(page, codeOf(6), `导出层6-${stamp}`, { parent: codeOf(5) })
    await page.locator('.qbar input').first().fill(codeOf(6))
    await page.locator('.qbar button[type="submit"]').click()
    const row6 = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: codeOf(6) })
    await expect(row6).toBeVisible()
    const blockedTrace = page.waitForResponse(
      (r) => /\/asset\/forward\/trace\/[1-9]\d*/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row6.getByTestId('corp-asset-forward-btn').click()
    const blockedDrawer = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    expect((await (await blockedTrace).json() as { code: number }).code).toBe(1013)
    const blockedExport = page.waitForResponse(
      (r) => /\/asset\/forward\/export\/[1-9]\d*/.test(r.url()) && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await blockedDrawer.getByTestId('asset-forward-export').click()
    expect((await (await blockedExport).json() as { code: number }).code).toBe(1013)
    await expect(blockedDrawer.getByTestId('asset-forward-error')).toContainText('1013')
    await expect(blockedDrawer.getByTestId('asset-forward-error')).toContainText('穿透层级超限')
    await page.screenshot({ path: `${shotDir}/03-forward-export-1013.png`, fullPage: true })
    await blockedDrawer.getByRole('button', { name: '关闭' }).click()

    const personCode = `AS-EX-P-${stamp}`
    const personName = `使用人显示器-${stamp}`
    await page.locator('.qbar input').first().fill('')
    await page.locator('.qbar button[type="submit"]').click()
    await registerAsset(page, personCode, personName)
    await page.locator('.qbar input').first().fill(personCode)
    const personFiltered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    await personFiltered
    const personRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: personCode })
    await personRow.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await checkout.getByTestId('corp-asset-purpose').fill('办公领用')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect((await (await checkoutResp).json() as { code: number }).code).toBe(0)
    await expect(personRow.getByTestId('corp-asset-status')).toHaveText('在用')

    await page.getByTestId('corp-asset-entry-open').click()
    const entry = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await expect(entry).toBeVisible()
    await expect(entry.getByTestId('asset-entry-export')).toBeVisible()
    await entry.getByTestId('asset-entry-person').click()
    await entry.getByTestId('asset-entry-user').selectOption({ label: '管理员' })
    const personQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-person/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await entry.getByTestId('asset-entry-query').click()
    expect((await (await personQuery).json() as { code: number }).code).toBe(0)
    const personTableRow = entry.locator('tr', { hasText: personCode })
    await expect(personTableRow.getByTestId('asset-entry-status')).toHaveText('在用')
    const personSummary = (await entry.getByTestId('asset-entry-summary').innerText()).trim()
    await page.screenshot({ path: `${shotDir}/04-person-export-button.png`, fullPage: true })

    const personDownloadPromise = page.waitForEvent('download')
    await entry.getByTestId('asset-entry-export').click()
    const personDownload = await personDownloadPromise
    expect(personDownload.suggestedFilename()).toBe('asset_reverse_report.xlsx')
    const personXlsx = `${shotDir}/asset_reverse_person.xlsx`
    await personDownload.saveAs(personXlsx)
    expect(fs.readFileSync(personXlsx).subarray(0, 2).toString()).toBe('PK')
    const personRows = xlsxRows(personXlsx)
    expect(personRows[0][0]).toBe('汇总')
    expect(personRows[0][1]).toBe(personSummary)
    expect(personRows[1]).toEqual(['资产编号', '名称', '状态', '绑定', '账号'])
    const personSheet = personRows.find((row) => row[0] === personCode)
    expect(personSheet?.[1]).toBe(personName)
    expect(personSheet?.[2]).toBe('在用')
    await expect(entry.getByTestId('asset-export-note')).toContainText('已导出反查 xlsx')
    await page.screenshot({ path: `${shotDir}/05-person-export-success.png`, fullPage: true })

    await entry.getByTestId('asset-entry-account').click()
    await entry.getByTestId('asset-entry-account-no').fill('AC-NO-SUCH-74')
    const missingExport = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await entry.getByTestId('asset-entry-export').click()
    expect((await (await missingExport).json() as { code: number }).code).toBe(1500)
    await expect(entry.getByTestId('asset-entry-error')).toContainText('1500')
    await expect(entry.getByTestId('asset-entry-error')).toContainText('账号不存在')
    await page.screenshot({ path: `${shotDir}/06-account-export-1500.png`, fullPage: true })

    const accountCode = `AS-EX-A-${stamp}`
    const accountName = `账号导出显示器-${stamp}`
    await entry.getByRole('button', { name: '关闭' }).click()
    await page.locator('.qbar input').first().fill('')
    await page.locator('.qbar button[type="submit"]').click()
    await registerAsset(page, accountCode, accountName, { accountNo: 'AC-E2E-FIN' })
    await page.getByTestId('corp-asset-entry-open').click()
    const accountDrawer = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await accountDrawer.getByTestId('asset-entry-account-no').fill('AC-E2E-FIN')
    const accountQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await accountDrawer.getByTestId('asset-entry-query').click()
    expect((await (await accountQuery).json() as { code: number }).code).toBe(0)
    await expect(accountDrawer.locator('tr', { hasText: accountCode }).getByTestId('asset-entry-status')).toHaveText('待审核')
    const accountSummary = (await accountDrawer.getByTestId('asset-entry-summary').innerText()).trim()
    const accountDownloadPromise = page.waitForEvent('download')
    await accountDrawer.getByTestId('asset-entry-export').click()
    const accountDownload = await accountDownloadPromise
    expect(accountDownload.suggestedFilename()).toBe('asset_reverse_report.xlsx')
    const accountXlsx = `${shotDir}/asset_reverse_account.xlsx`
    await accountDownload.saveAs(accountXlsx)
    const accountRows = xlsxRows(accountXlsx)
    expect(accountRows[0][1]).toBe(accountSummary)
    const accountSheet = accountRows.find((row) => row[0] === accountCode)
    expect(accountSheet?.[1]).toBe(accountName)
    expect(accountSheet?.[2]).toBe('待审核')
    expect(accountSheet?.[4]).toBe('AC-E2E-FIN')

    const sessionCode = `AS-EX-S-${stamp}`
    const sessionName = `场次导出灯-${stamp}`
    await accountDrawer.getByRole('button', { name: '关闭' }).click()
    await registerAsset(page, sessionCode, sessionName, { sessionCode: SESSION })
    await page.getByTestId('corp-asset-entry-open').click()
    const sessionDrawer = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await sessionDrawer.getByTestId('asset-entry-session').click()
    await sessionDrawer.getByTestId('asset-entry-session-code').fill(SESSION)
    const sessionQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-session/') && r.request().method() === 'GET' && r.status() === 200,
    )
    await sessionDrawer.getByTestId('asset-entry-query').click()
    expect((await (await sessionQuery).json() as { code: number }).code).toBe(0)
    await expect(sessionDrawer.locator('tr', { hasText: sessionCode }).getByTestId('asset-entry-status')).toHaveText('待审核')
    await expect(sessionDrawer.locator('tr', { hasText: accountCode })).toHaveCount(0)
    const sessionSummary = (await sessionDrawer.getByTestId('asset-entry-summary').innerText()).trim()
    const sessionDownloadPromise = page.waitForEvent('download')
    await sessionDrawer.getByTestId('asset-entry-export').click()
    const sessionDownload = await sessionDownloadPromise
    const sessionXlsx = `${shotDir}/asset_reverse_session.xlsx`
    await sessionDownload.saveAs(sessionXlsx)
    const sessionRows = xlsxRows(sessionXlsx)
    expect(sessionRows[0][1]).toBe(sessionSummary)
    const sessionSheet = sessionRows.find((row) => row[0] === sessionCode)
    expect(sessionSheet?.[1]).toBe(sessionName)
    expect(sessionSheet?.[2]).toBe('待审核')
    expect(sessionRows.some((row) => row[0] === accountCode)).toBe(false)
    await expect(sessionDrawer.getByTestId('asset-export-note')).toContainText('已导出反查 xlsx')
    await page.screenshot({ path: `${shotDir}/07-session-export-success.png`, fullPage: true })

    const view = await page.context().newPage()
    const body = accountRows
      .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`)
      .join('')
    await view.setContent(
      `<html><head><meta charset="utf-8"><style>body{font-family:"WenQuanYi Micro Hei",sans-serif;padding:24px}table{border-collapse:collapse}td{border:1px solid #ccc;padding:6px 10px}</style></head><body><h1>反查 xlsx 关键行</h1><table>${body}</table></body></html>`,
    )
    await view.screenshot({ path: `${shotDir}/08-xlsx-key-rows.png`, fullPage: true })
    await view.close()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
