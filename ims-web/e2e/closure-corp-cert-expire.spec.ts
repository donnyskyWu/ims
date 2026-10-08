import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-61-screenshots'

function ymd(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function certNo(slot: number) {
  const tail = String(Date.now()).slice(-10)
  return `110101${tail}${slot}`.padEnd(18, '0').slice(0, 18)
}

/** Checklist **E2E-S6-02**（#61 · 纯 UI）· T−30/T−7/T−0 黄红锁定 + 工作台提醒 */
test.describe('corp certificate expiry alert closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('register T-30 T-7 T-0 then scan shows three alerts and workbench reminders', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    const stamp = Date.now()
    const samples = [
      { holder: `E2E-Cert-Y-${stamp}`, days: 30, level: '黄色', status: '即将到期' },
      { holder: `E2E-Cert-R-${stamp}`, days: 7, level: '红色', status: '即将到期' },
      { holder: `E2E-Cert-L-${stamp}`, days: 0, level: '锁定', status: '已过期' },
    ]

    for (const [index, sample] of samples.entries()) {
      const number = certNo(index + 1)
      await page.getByTestId('corp-cert-create-btn').click()
      const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
      await expect(drawer).toBeVisible()
      await drawer.getByTestId('corp-cert-holder').fill(sample.holder)
      await drawer.getByTestId('corp-cert-no').fill(number)
      await drawer.getByTestId('corp-cert-issue').fill('2020-01-01')
      await drawer.getByTestId('corp-cert-expire-date').fill(ymd(sample.days))
      if (index === 0) {
        await page.screenshot({ path: `${shotDir}/01-upload-t30.png`, fullPage: true })
      }
      const uploadResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
      )
      await drawer.getByTestId('corp-cert-save').click()
      const uploaded = (await (await uploadResp).json()) as { code: number; data?: { certNoMasked?: string } }
      expect(uploaded.code).toBe(0)
      expect(JSON.stringify(uploaded)).not.toContain(number)
      await expect(drawer).toBeHidden()

      await page.locator('input[placeholder="持有人"]').fill(sample.holder)
      const listResp = page.waitForResponse(
        (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
      )
      await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
      await listResp
      const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: sample.holder })
      await expect(row).toBeVisible()
      await expect(row).toContainText('待审')
      await row.getByTestId('corp-cert-review-btn').click()
      const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
      await expect(review).toBeVisible()
      const reviewResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
      )
      await review.getByTestId('corp-cert-review-approve').click()
      const reviewed = (await (await reviewResp).json()) as { code: number }
      expect(reviewed.code).toBe(0)
      await expect(review).toBeHidden()
    }

    await page.screenshot({ path: `${shotDir}/02-approved-before-scan.png`, fullPage: true })
    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
    await expect(scanDrawer).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-scan-confirm.png`, fullPage: true })
    const scanResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/scan') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scanDrawer.getByTestId('corp-cert-scan-confirm').click()
    const scanned = (await (await scanResp).json()) as { code: number; data?: { created?: number } }
    expect(scanned.code).toBe(0)
    expect(scanned.data?.created).toBeGreaterThanOrEqual(3)

    const expireTable = page.getByTestId('corp-cert-expire-table')
    for (const sample of samples) {
      const alertRow = expireTable.locator('tbody tr', { hasText: sample.holder })
      await expect(alertRow).toBeVisible()
      await expect(alertRow).toContainText(sample.level)
    }
    await expect(page.getByTestId('corp-cert-scan-message')).toContainText('工作台')
    await page.screenshot({ path: `${shotDir}/04-expire-three-levels.png`, fullPage: true })

    await page.locator('input[placeholder="持有人"]').fill(samples[2].holder)
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: samples[2].holder })).toContainText('已过期')

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    const msgTable = page.locator('.tbl-wrap table').nth(2)
    for (const sample of samples) {
      const title = `证件${sample.level}预警：${sample.holder}`
      await expect(msgTable.locator('tbody tr', { hasText: title })).toBeVisible()
    }
    await page.screenshot({ path: `${shotDir}/05-workbench-reminders.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
