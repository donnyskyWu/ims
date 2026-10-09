import fs from 'node:fs'
import { inflateRawSync } from 'node:zlib'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #120 · 已核对记录解锁后再编辑，成本汇总导出 xlsx/csv。
 * 纯 UI。种子账号 AC-E2E-TAIL。月份 2026-02，避开 #64/#70 用过的 3/4/8/9 月。
 */
const TAIL_NO = 'AC-E2E-TAIL'
const SHOTS = '/opt/cursor/artifacts/e2e-120-screenshots'

function zipEntry(buf: Buffer, name: string): string {
  let offset = 0
  while (offset + 30 < buf.length) {
    if (buf.readUInt32LE(offset) !== 0x04034b50) break
    const method = buf.readUInt16LE(offset + 8)
    const compSize = buf.readUInt32LE(offset + 18)
    const nameLen = buf.readUInt16LE(offset + 26)
    const extraLen = buf.readUInt16LE(offset + 28)
    const nameStart = offset + 30
    const dataStart = nameStart + nameLen + extraLen
    const entryName = buf.subarray(nameStart, nameStart + nameLen).toString('utf8')
    const data = buf.subarray(dataStart, dataStart + compSize)
    if (entryName === name) {
      const raw = method === 0 ? data : inflateRawSync(data)
      return raw.toString('utf8')
    }
    offset = dataStart + compSize
  }
  throw new Error(`zip entry missing: ${name}`)
}

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchTail(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(TAIL_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: TAIL_NO })
  await expect(row).toBeVisible()
  return row
}

function tailRecord(page: Page) {
  return page.getByTestId('acct-recharge-row').filter({ hasText: TAIL_NO }).first()
}

async function registerRecharge(page: Page, row: Locator, amount: string, rechargeDate: string) {
  await row.getByRole('button', { name: '冲话费' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '登记冲话费' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-recharge-amount').fill(amount)
  await drawer.getByTestId('acct-recharge-date').fill(rechargeDate)
  const resp = page.waitForResponse(
    (r) =>
      r.url().includes('/account/recharge') &&
      !r.url().includes('/list') &&
      !r.url().includes('/verify') &&
      !r.url().includes('/summary') &&
      !r.url().includes('/unlock') &&
      r.request().method() === 'POST',
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

async function editAmount(page: Page, record: Locator, amount: string) {
  await record.getByTestId('acct-recharge-edit').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '编辑冲话费' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-recharge-amount').fill(amount)
  const resp = page.waitForResponse(
    (r) => r.url().includes('/account/recharge/') && r.request().method() === 'PUT',
  )
  await drawer.getByRole('button', { name: '保存更正' }).click()
  const body = (await (await resp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

async function verifyMonth(page: Page, row: Locator, month: string, platform: string) {
  await row.getByRole('button', { name: '账实核对' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '月度账实核对' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('acct-verify-month').fill(month)
  await drawer.getByTestId('acct-verify-platform').fill(platform)
  const resp = page.waitForResponse(
    (r) => r.url().includes('/account/recharge/verify') && r.request().method() === 'POST',
  )
  await drawer.getByTestId('acct-verify-submit').click()
  const body = (await (await resp).json()) as { code: number; data?: { verifyStatus?: string } }
  return { drawer, body }
}

test.describe('CORP reconciled recharge unlock and summary export', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('unlock a matched recharge then edit, and export the cost summary (#120)', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await openDouyin(page)
    const row = await searchTail(page)

    await registerRecharge(page, row, '80', '2026-02-11')
    const created = tailRecord(page)
    await expect(created).toContainText('80.00')
    await expect(created).toContainText('未核对')
    await expect(created.getByTestId('acct-recharge-edit')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/01-unverified.png`, fullPage: true })

    await editAmount(page, created, '85')
    const edited = tailRecord(page)
    await expect(edited).toContainText('85.00')
    await expect(edited).toContainText('未核对')
    await page.screenshot({ path: `${SHOTS}/02-edited-before-verify.png`, fullPage: true })

    const passed = await verifyMonth(page, row, '2026-02', '85')
    expect(passed.body.code).toBe(0)
    expect(passed.body.data?.verifyStatus).toBe('MATCHED')
    await expect(passed.drawer.getByTestId('acct-verify-result')).toContainText('一致')
    await page.screenshot({ path: `${SHOTS}/03-verified-matched.png`, fullPage: true })
    await passed.drawer.getByRole('button', { name: '关闭' }).click()
    await expect(passed.drawer).toBeHidden()

    const locked = tailRecord(page)
    await expect(locked).toContainText('一致')
    await expect(locked.getByTestId('acct-recharge-unlock')).toBeVisible()
    await expect(locked.getByTestId('acct-recharge-edit')).toHaveCount(0)

    await locked.getByTestId('acct-recharge-unlock').click()
    const unlockDrawer = page.locator('.drawer.on').filter({ hasText: '解锁已核对记录' })
    await expect(unlockDrawer.getByTestId('acct-unlock-status')).toContainText('一致')
    const unlockResp = page.waitForResponse(
      (r) => r.url().includes('/unlock') && r.request().method() === 'POST',
    )
    await unlockDrawer.getByTestId('acct-unlock-submit').click()
    const unlockBody = (await (await unlockResp).json()) as { code: number; data?: { verifyStatus?: string } }
    expect(unlockBody.code).toBe(0)
    expect(unlockBody.data?.verifyStatus).toBe('UNVERIFIED')
    await expect(unlockDrawer.getByTestId('acct-unlock-msg')).toContainText('已解锁')
    await page.screenshot({ path: `${SHOTS}/04-unlocked.png`, fullPage: true })
    await unlockDrawer.getByRole('button', { name: '关闭' }).click()

    const reopened = tailRecord(page)
    await expect(reopened).toContainText('未核对')
    await editAmount(page, reopened, '90')
    const corrected = tailRecord(page)
    await expect(corrected).toContainText('90.00')
    await expect(corrected).toContainText('未核对')
    await page.screenshot({ path: `${SHOTS}/05-edited-after-unlock.png`, fullPage: true })

    await page.getByTestId('acct-summary-month').fill('2026-02')
    await page.getByTestId('acct-summary-groupby').selectOption('ACCOUNT')
    const summaryResp = page.waitForResponse(
      (r) =>
        r.url().includes('/account/recharge/summary') &&
        !r.url().includes('/export') &&
        r.request().method() === 'GET',
    )
    await page.getByTestId('acct-summary-query').click()
    const summaryBody = (await (await summaryResp).json()) as { code: number }
    expect(summaryBody.code).toBe(0)
    const accountRow = page.getByTestId('acct-summary-row').filter({ hasText: TAIL_NO })
    await expect(accountRow).toContainText('¥90.00')
    await page.getByTestId('acct-recharge-summary').scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${SHOTS}/06-summary.png`, fullPage: true })

    const [xlsx] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('acct-summary-export-xlsx').click(),
    ])
    expect(xlsx.suggestedFilename()).toBe('recharge_summary_2026-02_ACCOUNT.xlsx')
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('已导出')
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('90.00')
    const xlsxPath = await xlsx.path()
    expect(xlsxPath).toBeTruthy()
    const xml = zipEntry(fs.readFileSync(xlsxPath!), 'xl/worksheets/sheet1.xml')
    expect(xml).toContain('90.00')
    expect(xml).toContain(TAIL_NO)
    await page.screenshot({ path: `${SHOTS}/07-export-xlsx.png`, fullPage: true })

    const [csv] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('acct-summary-export-csv').click(),
    ])
    expect(csv.suggestedFilename()).toBe('recharge_summary_2026-02_ACCOUNT.csv')
    const csvPath = await csv.path()
    const csvText = fs.readFileSync(csvPath!, 'utf8')
    expect(csvText).toContain('90.00')
    expect(csvText).toContain(TAIL_NO)
    expect(csvText).toContain('合计')
    await expect(page.getByTestId('acct-summary-export-note')).toContainText('.csv')
    await page.screenshot({ path: `${SHOTS}/08-export-csv.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
