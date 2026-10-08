import fs from 'node:fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/** Checklist **E2E-S6-04**（#67 · 纯 UI）· 同一证件 1 小时内第 11 次查看 → 1035 */
const HOLDER = 'E2E-Cert-Freq'
const SHOTS = '/opt/cursor/artifacts/e2e-67-screenshots'

async function openCertificate(page: Page) {
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
}

async function searchFreq(page: Page) {
  const listResp = page.waitForResponse(
    (r) =>
      r.url().includes('/corp/resource/certificate/page') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await page.locator('input[placeholder="持有人"]').fill(HOLDER)
  await page.getByRole('button', { name: '查询' }).click()
  const body = (await (await listResp).json()) as {
    code: number
    data?: { list?: Array<{ holderName?: string }> }
  }
  expect(body.code).toBe(0)
  expect(body.data?.list?.some((row) => row.holderName === HOLDER)).toBe(true)
  const row = page.locator('tbody tr', { hasText: HOLDER }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  return row
}

async function viewCert(page: Page, row: Locator) {
  const viewResp = page.waitForResponse(
    (r) =>
      r.url().includes('/certificate/') &&
      r.url().includes('/view') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await row.getByTestId('corp-cert-view-btn').click()
  return (await (await viewResp).json()) as {
    code: number
    msg?: string
    data?: { watermarkText?: string }
  }
}

async function closeDrawer(page: Page) {
  const drawer = page.locator('.drawer.on').filter({ hasText: '证件查看' })
  await drawer.getByRole('button', { name: '关闭' }).click()
  await expect(drawer).toBeHidden()
}

test.describe('corp certificate view frequency closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('eleventh view of the same certificate within an hour returns 1035', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(SHOTS, { recursive: true })
    await loginAdmin(page)
    await openCertificate(page)
    const row = await searchFreq(page)
    await page.screenshot({ path: `${SHOTS}/01-freq-cert-list.png`, fullPage: true })

    for (let n = 1; n <= 10; n += 1) {
      const body = await viewCert(page, row)
      expect(body.code).toBe(0)
      expect(body.data?.watermarkText).toMatch(/admin/i)
      const hint = page.getByTestId('corp-cert-watermark-hint')
      await expect(hint).toBeVisible()
      await expect(hint).toContainText('admin')
      await expect(hint).toContainText('本接口不返回原图')
      await expect(page.getByTestId('corp-cert-view-error')).toHaveCount(0)
      if (n === 1) {
        await page.screenshot({ path: `${SHOTS}/02-first-view-watermark.png`, fullPage: true })
      }
      if (n === 10) {
        await page.screenshot({ path: `${SHOTS}/03-tenth-view-still-open.png`, fullPage: true })
      }
      await closeDrawer(page)
    }

    const blocked = await viewCert(page, row)
    expect(blocked.code).toBe(1035)
    expect(blocked.msg || '').toContain('1035')
    const error = page.getByTestId('corp-cert-view-error')
    await expect(error).toBeVisible()
    await expect(error).toContainText('1035')
    await expect(page.getByTestId('corp-cert-watermark-hint')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/04-eleventh-view-1035.png`, fullPage: true })

    await closeDrawer(page)
    const stillBlocked = await viewCert(page, row)
    expect(stillBlocked.code).toBe(1035)
    await expect(page.getByTestId('corp-cert-view-error')).toContainText('1035')
    await page.screenshot({ path: `${SHOTS}/05-still-blocked-1035.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})