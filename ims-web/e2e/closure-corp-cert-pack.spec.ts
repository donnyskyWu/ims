import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-77-screenshots'

function ymd(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function certNo(slot: number) {
  const tail = String(Date.now()).slice(-8)
  return `110101${tail}${slot}`.padEnd(18, '0').slice(0, 18)
}

async function openCertificate(page: Page) {
  const ready = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/resource/certificate')
  await ready
  await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
}

async function createAndApprove(page: Page, holder: string, days: number, slot: number) {
  const number = certNo(slot)
  await page.getByTestId('corp-cert-create-btn').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('corp-cert-holder').fill(holder)
  await drawer.getByTestId('corp-cert-no').fill(number)
  await drawer.getByTestId('corp-cert-issue').fill('2020-01-01')
  await drawer.getByTestId('corp-cert-expire-date').fill(ymd(days))
  const uploadResp = page.waitForResponse(
    (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByTestId('corp-cert-save').click()
  const uploaded = (await (await uploadResp).json()) as { code: number }
  expect(uploaded.code).toBe(0)
  await expect(drawer).toBeHidden()

  await page.locator('input[placeholder="持有人"]').fill(holder)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
  await listResp
  const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
  await expect(row).toBeVisible()
  await row.getByTestId('corp-cert-review-btn').click()
  const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
  const reviewResp = page.waitForResponse(
    (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
  )
  await review.getByTestId('corp-cert-review-approve').click()
  const reviewed = (await (await reviewResp).json()) as { code: number }
  expect(reviewed.code).toBe(0)
  await expect(review).toBeHidden()
}

async function viewOnce(page: Page, holder: string) {
  await page.locator('input[placeholder="持有人"]').fill(holder)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
  await listResp
  const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
  await expect(row).toBeVisible()
  const viewResp = page.waitForResponse(
    (r) => r.url().includes('/certificate/') && r.url().includes('/view') && r.request().method() === 'GET',
  )
  await row.getByTestId('corp-cert-view-btn').click()
  const viewed = (await (await viewResp).json()) as { code: number; data?: { watermarkText?: string } }
  expect(viewed.code).toBe(0)
  expect(viewed.data?.watermarkText || '').toMatch(/admin/i)
  const drawer = page.locator('.drawer.on').filter({ hasText: '证件查看' })
  await drawer.getByRole('button', { name: '关闭' }).click()
  await expect(drawer).toBeHidden()
}

/** Checklist 增量（#77 · 纯 UI）· 催办重复写入工作台；查看审计按证件/人/时间查询；超过 10 次进异常报告 */
test.describe('corp certificate remind and audit closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('remind an expiry alert twice and show cert_remind todos', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await openCertificate(page)

    const holder = `E2E-Cert-Urge-${Date.now()}`
    await createAndApprove(page, holder, 30, 1)
    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
    const scanResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/scan') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scanDrawer.getByTestId('corp-cert-scan-confirm').click()
    const scanned = (await (await scanResp).json()) as { code: number }
    expect(scanned.code).toBe(0)

    const alertRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: holder })
    await expect(alertRow).toBeVisible()
    await expect(alertRow).toContainText('黄色')
    await alertRow.getByTestId('corp-cert-remind-btn').click()
    const remind = page.locator('.drawer.on').filter({ hasText: '催办' })
    await expect(remind).toBeVisible()
    await remind.getByTestId('corp-cert-remind-channel').selectOption('APP')
    await page.screenshot({ path: `${shotDir}/01-remind-channel.png`, fullPage: true })
    const remindResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/') && r.url().includes('/remind') && r.request().method() === 'PUT',
    )
    await remind.getByTestId('corp-cert-remind-confirm').click()
    const reminded = (await (await remindResp).json()) as { code: number; data?: { remindedAt?: string } }
    expect(reminded.code).toBe(0)
    expect(reminded.data?.remindedAt).toBeTruthy()
    await expect(page.getByTestId('corp-cert-remind-message')).toContainText('已催办')
    await page.screenshot({ path: `${shotDir}/02-reminded-message.png`, fullPage: true })

    await alertRow.getByTestId('corp-cert-remind-btn').click()
    const again = page.locator('.drawer.on').filter({ hasText: '催办' })
    await again.getByTestId('corp-cert-remind-channel').selectOption('APP')
    const againResp = page.waitForResponse(
      (r) => r.url().includes('/remind') && r.request().method() === 'PUT',
    )
    await again.getByTestId('corp-cert-remind-confirm').click()
    expect(((await (await againResp).json()) as { code: number }).code).toBe(0)

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/, { timeout: 15_000 })
    const title = `证件催办：${holder}`
    const msgTable = page.locator('.tbl-wrap table').nth(2)
    await expect(msgTable.locator('tbody tr', { hasText: title })).toHaveCount(2)
    await page.screenshot({ path: `${shotDir}/03-workbench-remind-messages.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('query view audit by holder viewer and time, and list hourly risk over ten', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await openCertificate(page)

    const stamp = Date.now()
    const first = `E2E-Cert-AU-${stamp}`
    const second = `E2E-Cert-AV-${stamp}`
    await createAndApprove(page, first, 400, 2)
    await createAndApprove(page, second, 400, 3)
    await viewOnce(page, first)
    for (let n = 0; n < 10; n += 1) await viewOnce(page, second)

    const adminOption = page.getByTestId('corp-cert-audit-viewer').locator('option', { hasText: /^管理员$/ })
    await expect(adminOption).toHaveCount(1)
    await page.getByTestId('corp-cert-audit-holder').fill(first)
    await page.getByTestId('corp-cert-audit-viewer').selectOption(await adminOption.getAttribute('value') || '')
    await page.getByTestId('corp-cert-audit-from').fill(ymd(-1))
    await page.getByTestId('corp-cert-audit-to').fill(ymd(1))
    const auditResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/view-logs') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-audit-search').click()
    const audited = (await (await auditResp).json()) as { code: number; data?: { total?: number } }
    expect(audited.code).toBe(0)
    expect(audited.data?.total).toBe(1)
    const auditTable = page.getByTestId('corp-cert-audit-table')
    await expect(auditTable).toContainText('管理员')
    await expect(auditTable).toContainText(first)
    await expect(auditTable).toContainText('L2')
    await expect(auditTable).toContainText('admin')
    await expect(page.getByTestId('corp-cert-audit-total')).toHaveText('共 1 条')
    await page.screenshot({ path: `${shotDir}/04-audit-by-holder.png`, fullPage: true })

    await page.getByTestId('corp-cert-audit-from').fill('1999-01-01')
    await page.getByTestId('corp-cert-audit-to').fill('1999-01-02')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/view-logs') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-audit-search').click()
    const emptied = (await (await emptyResp).json()) as { code: number; data?: { total?: number } }
    expect(emptied.code).toBe(0)
    expect(emptied.data?.total).toBe(0)
    await expect(page.getByTestId('corp-cert-audit-total')).toHaveText('共 0 条')
    await expect(auditTable).toContainText('没有查看记录')

    await page.getByTestId('corp-cert-audit-holder').fill('')
    await page.getByTestId('corp-cert-audit-from').fill('')
    await page.getByTestId('corp-cert-audit-to').fill('')
    const riskResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/risk-report') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-audit-search').click()
    const risk = (await (await riskResp).json()) as {
      code: number
      data?: { abnormalTotal?: number; highFrequencyUsers?: Array<{ name?: string; viewsInLastHour?: number }> }
    }
    expect(risk.code).toBe(0)
    expect(risk.data?.abnormalTotal || 0).toBeGreaterThanOrEqual(11)
    const hit = (risk.data?.highFrequencyUsers || []).find((item) => (item.viewsInLastHour || 0) >= 11)
    expect(hit?.name).toBeTruthy()
    const riskPanel = page.getByTestId('corp-cert-risk-report')
    await expect(riskPanel).toContainText('超过 10 次')
    await expect(riskPanel).toContainText(String(hit?.name))
    await expect(page.getByTestId('corp-cert-risk-table')).toContainText(String(hit?.viewsInLastHour))
    await page.screenshot({ path: `${shotDir}/05-risk-over-ten.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
