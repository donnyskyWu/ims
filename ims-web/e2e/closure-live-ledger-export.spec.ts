import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

/**
 * #82 · 纯 UI
 * 台账「导出」异步 Excel；财务角色只见 GMV/成本且不能导出；下播成本明细负数拦截后可提交。
 */
const shotDir = '/opt/cursor/artifacts/e2e-82-screenshots'
const SESSION = 'IMS20261008DYS0082'
const FINANCE_USER = 'e2e_acct_r3'

fs.mkdirSync(shotDir, { recursive: true })

async function openSession(page: Page, code: string) {
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(code)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const row = page.locator('tbody tr', { hasText: code }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.getByRole('button', { name: '详情' }).click()
  const detail = page.locator('.drawer.on')
  await expect(detail).toBeVisible({ timeout: 15_000 })
  await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
  await expect(detail.getByTestId('live-report-gmv')).toBeVisible()
  return detail
}

test.describe('live ledger export and finance report', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('admin exports ledger xlsx and sees full report', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await expect(page.getByTestId('live-ledger-export')).toBeEnabled()
    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('tbody tr', { hasText: SESSION })).toBeVisible({ timeout: 15_000 })

    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('live-ledger-export').click()
    const exportBody = (await (await exportResp).json()) as {
      code: number
      data?: { message?: string; fileName?: string; exportTaskId?: string }
    }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.message).toContain('导出任务已提交')
    expect(exportBody.data?.fileName).toBe('live_ledger.xlsx')
    expect(exportBody.data?.exportTaskId).toBeTruthy()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('live_ledger.xlsx')
    await expect(page.getByTestId('live-export-note')).toContainText('导出任务已提交')
    await page.screenshot({ path: `${shotDir}/01-export-submitted.png`, fullPage: true })

    const detail = await openSession(page, SESSION)
    await expect(detail.getByTestId('live-report-viewers')).toHaveValue('4321')
    await expect(detail.getByTestId('live-report-gmv')).toHaveValue('12800.5')
    await expect(detail.getByTestId('live-report-ad')).toHaveValue('860')
    await expect(detail.getByTestId('live-cost-details')).toContainText('投放')
    await expect(detail.getByTestId('live-cost-details')).toContainText('500.00')
    await expect(detail.getByTestId('live-report-finance-scope')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-admin-full-report.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('finance sees gmv and cost only and export is denied', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAs(page, FINANCE_USER)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(SESSION)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('tbody tr', { hasText: SESSION }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    const detailResp = page.waitForResponse(
      (r) => r.url().includes(`/live/sessions/${SESSION}`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row.getByRole('button', { name: '详情' }).click()
    const reportBody = (await (await detailResp).json()) as {
      code: number
      data?: { report?: { fieldScope?: string; viewerCount?: number; gmv?: number; adCost?: number } }
    }
    expect(reportBody.code).toBe(0)
    expect(reportBody.data?.report?.fieldScope).toBe('FINANCE')
    expect(reportBody.data?.report?.viewerCount).toBeUndefined()
    expect(reportBody.data?.report?.gmv).toBe(12800.5)
    expect(reportBody.data?.report?.adCost).toBe(860)
    const detail = page.locator('.drawer.on')
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(detail.getByTestId('live-report-finance-scope')).toContainText('财务字段')
    await expect(detail.getByTestId('live-report-gmv')).toHaveValue('12800.5')
    await expect(detail.getByTestId('live-report-ad')).toHaveValue('860')
    await expect(detail.getByTestId('live-report-viewers')).toHaveCount(0)
    await expect(detail.getByTestId('live-report-orders')).toHaveCount(0)
    await expect(detail.getByTestId('live-cost-details')).toContainText('打赏')
    await expect(detail.getByTestId('live-cost-details')).toContainText('360.00')
    await expect(detail.getByTestId('live-report-submit')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-finance-trimmed-report.png`, fullPage: true })

    await detail.locator('.dr-x').click()
    await expect(page.locator('.drawer.on')).toHaveCount(0)
    const deniedResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/export') && !r.url().includes('/file') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-ledger-export').click()
    const denied = (await (await deniedResp).json()) as { code: number; msg?: string }
    expect(denied.code).toBe(1008)
    await expect(page.getByTestId('live-export-error')).toContainText('1008')
    await page.screenshot({ path: `${shotDir}/04-finance-export-denied.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('negative cost detail is rejected then a gift line submits', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建场次登记' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '开播登记' })
    await expect(drawer).toBeVisible()
    await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
    await drawer.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
    await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
    await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(`E2E 成本明细 ${Date.now()}`)
    const regResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const regBody = (await (await regResp).json()) as { code: number }
    expect(regBody.code).toBe(0)

    const detail = page.locator('.drawer.on').filter({ hasText: '场次' })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await detail.getByTestId('live-cost-type').selectOption('GIFT')
    await detail.getByTestId('live-cost-amount').fill('-1')
    const badResp = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && r.request().method() === 'POST',
    )
    await detail.getByTestId('live-report-submit').click()
    const badBody = (await (await badResp).json()) as { code: number }
    expect(badBody.code).toBe(1001)
    await expect(detail.getByTestId('live-report-error')).toContainText('1001')
    await page.screenshot({ path: `${shotDir}/05-cost-negative.png`, fullPage: true })

    await detail.getByTestId('live-cost-amount').fill('12.5')
    const okResp = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && r.request().method() === 'POST',
    )
    await detail.getByTestId('live-report-submit').click()
    const okBody = (await (await okResp).json()) as {
      code: number
      data?: { costDetails?: { costType?: string; amount?: number }[]; entryStatus?: string }
    }
    expect(okBody.code).toBe(0)
    expect(okBody.data?.entryStatus).toBe('SUBMITTED')
    expect(okBody.data?.costDetails?.[0]?.costType).toBe('GIFT')
    expect(okBody.data?.costDetails?.[0]?.amount).toBe(12.5)
    await expect(detail.getByTestId('live-cost-details')).toContainText('打赏')
    await expect(detail.getByTestId('live-cost-details')).toContainText('12.50')
    await page.screenshot({ path: `${shotDir}/06-cost-saved.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
