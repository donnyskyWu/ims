import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

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
  return `221${tail}${slot}`.padEnd(12, '0').slice(0, 12)
}

async function openCertificate(page: Page) {
  const ready = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/resource/certificate')
  await ready
  await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
}

async function createCert(page: Page, holder: string, certType: string, expire: string) {
  await page.getByTestId('corp-cert-create-btn').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('corp-cert-holder').fill(holder)
  await drawer.getByTestId('corp-cert-type').selectOption(certType)
  await drawer.getByTestId('corp-cert-no').fill(certNo(certType === 'PASSPORT' ? 2 : 1))
  await drawer.getByTestId('corp-cert-issue').fill('2020-01-01')
  await drawer.getByTestId('corp-cert-expire-date').fill(expire)
  const uploadResp = page.waitForResponse(
    (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByTestId('corp-cert-save').click()
  const uploaded = (await (await uploadResp).json()) as { code: number }
  expect(uploaded.code).toBe(0)
  await expect(drawer).toBeHidden()
}

/** #221 · 证件列表类型/有效期筛选空态，同名审计说明，到期剩余天数文案 */
test.describe('corp certificate list filter tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter by type and expire range, then explain same-name audit and expired remain days', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const holder = `E2E-Cert-221-${Date.now()}`
    await loginAdmin(page)
    await openCertificate(page)

    await createCert(page, holder, 'PASSPORT', ymd(400))
    await createCert(page, holder, 'IDCARD', ymd(20))

    const listForm = page.locator('form.qbar').first()
    await listForm.locator('input[placeholder="持有人"]').fill(holder)
    await page.getByTestId('corp-cert-filter-type').selectOption('PASSPORT')
    const passportResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/resource/certificate/page') &&
        r.url().includes('certType=PASSPORT') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await listForm.getByRole('button', { name: '查询' }).click()
    await passportResp
    const hit = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
    await expect(hit).toHaveCount(1)
    await expect(hit).toContainText('护照')
    await page.screenshot({ path: `${shotDir}/cert-221-type-filter.png`, fullPage: true })

    await page.getByTestId('corp-cert-filter-type').selectOption('OTHER')
    const emptyResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/resource/certificate/page') &&
        r.url().includes('certType=OTHER') &&
        r.status() === 200,
    )
    await listForm.getByRole('button', { name: '查询' }).click()
    await emptyResp
    const empty = page.getByTestId('corp-cert-list-empty')
    await expect(empty).toContainText('当前筛选下没有证件')
    await expect(empty).toContainText('类型')
    await page.screenshot({ path: `${shotDir}/cert-221-type-empty.png`, fullPage: true })

    await page.getByTestId('corp-cert-filter-type').selectOption('PASSPORT')
    await page.getByTestId('corp-cert-filter-from').fill(ymd(50))
    await page.getByTestId('corp-cert-filter-to').fill(ymd(10))
    await listForm.getByRole('button', { name: '查询' }).click()
    await expect(empty).toContainText('开始日期不能晚于结束日期')
    await expect(page.locator('.tbl-wrap').first()).not.toContainText(holder)

    await page.getByTestId('corp-cert-filter-from').fill(ymd(300))
    await page.getByTestId('corp-cert-filter-to').fill(ymd(500))
    const rangeResp = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.url().includes('expireDateRange=') && r.status() === 200,
    )
    await listForm.getByRole('button', { name: '查询' }).click()
    await rangeResp
    await expect(hit).toHaveCount(1)
    await expect(hit).toContainText('护照')

    await page.getByTestId('corp-cert-filter-from').fill(ymd(1))
    await page.getByTestId('corp-cert-filter-to').fill(ymd(30))
    await listForm.getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.tbl-wrap').first()).not.toContainText(holder)
    await expect(empty).toContainText('当前筛选下没有证件')
    await page.screenshot({ path: `${shotDir}/cert-221-range-empty.png`, fullPage: true })

    await page.getByTestId('corp-cert-audit-holder').fill(holder)
    await page.getByTestId('corp-cert-audit-search').click()
    await expect(page.getByTestId('corp-cert-audit-error')).toContainText('有多本同名证件，请改填档案编号')
    await page.screenshot({ path: `${shotDir}/cert-221-audit-same-name.png`, fullPage: true })

    const locked = `E2E-Cert-221-L-${Date.now()}`
    await createCert(page, locked, 'IDCARD', ymd(0))
    await listForm.locator('input[placeholder="持有人"]').fill(locked)
    await page.getByTestId('corp-cert-filter-type').selectOption('')
    await page.getByTestId('corp-cert-filter-from').fill('')
    await page.getByTestId('corp-cert-filter-to').fill('')
    const lockedList = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.url().includes('holderName=') && r.status() === 200,
    )
    await listForm.getByRole('button', { name: '查询' }).click()
    await lockedList
    const lockedRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: locked })
    await lockedRow.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await review.getByTestId('corp-cert-review-approve').click()
    expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
    await expect(review).toBeHidden()

    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
    const scanResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/scan') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scanDrawer.getByTestId('corp-cert-scan-confirm').click()
    expect(((await (await scanResp).json()) as { code: number }).code).toBe(0)

    await page.getByTestId('corp-cert-expire-holder').fill(locked)
    const expireResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/list') && r.url().includes('holderName=') && r.status() === 200,
    )
    await page.getByTestId('corp-cert-expire-search').click()
    await expireResp
    const alertRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: locked })
    await expect(alertRow.getByTestId('corp-cert-remain')).toHaveText('已过期')
    await expect(alertRow).toContainText('锁定')
    await page.screenshot({ path: `${shotDir}/cert-221-remain-expired.png`, fullPage: true })

    await page.getByTestId('corp-cert-expire-holder').fill('ZZ-NO-CERT-221')
    await page.getByTestId('corp-cert-expire-search').click()
    const missed = page.getByTestId('corp-cert-expire-empty')
    await expect(missed).toContainText('没有符合筛选的到期预警')
    await expect(missed).toContainText('持有人')
    await page.screenshot({ path: `${shotDir}/cert-221-expire-filter-empty.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
