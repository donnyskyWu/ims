import fs from 'fs'
import { test, expect } from '@playwright/test'
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

function certNo() {
  const tail = String(Date.now()).slice(-12)
  return `110101${tail}`.padEnd(18, '0').slice(0, 18)
}

/** #155 账号池状态空态、责任人筛选，以及证件到期催办筛选。 */
test.describe('account list filters and cert expiry reminder filters', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('pool status empty state and holder filter on the douyin ledger', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/account/douyin')
    await expect(page.locator('h1')).toContainText('抖音')

    await page.getByTestId('acct-filter-keyword').fill('ZZ-NO-ACCT-155')
    await page.getByTestId('acct-filter-status').selectOption('IN_POOL')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.url().includes('status=IN_POOL') && r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await emptyResp
    const empty = page.getByTestId('acct-list-empty')
    await expect(empty).toContainText('当前没有「池可领用」账号符合当前筛选')
    await expect(empty).toContainText('换一个池状态或责任人')
    await page.screenshot({ path: `${shotDir}/acct-cert-155-pool-empty.png`, fullPage: true })

    await page.getByTestId('acct-list-filters').getByRole('button', { name: '重置' }).click()
    await page.getByTestId('acct-filter-keyword').fill('AC-E2E-POOL')
    await page.getByTestId('acct-filter-holder').selectOption({ label: '管理员' })
    const hitResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.url().includes('holderUserId=') && r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await hitResp
    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: 'AC-E2E-POOL' })
    await expect(row).toBeVisible()
    await expect(row).toContainText('管理员')
    await page.screenshot({ path: `${shotDir}/acct-cert-155-holder-filter.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('cert expiry reminder filters by level and shows the urge on the row', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const holder = `E2E-Cert-155-${Date.now()}`
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    await page.getByTestId('corp-cert-create-btn').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await drawer.getByTestId('corp-cert-holder').fill(holder)
    await drawer.getByTestId('corp-cert-no').fill(certNo())
    await drawer.getByTestId('corp-cert-issue').fill('2020-01-01')
    await drawer.getByTestId('corp-cert-expire-date').fill(ymd(30))
    await drawer.getByTestId('corp-cert-save').click()
    await expect(drawer).toBeHidden()

    await page.locator('input[placeholder="持有人"]').fill(holder)
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    const archiveRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
    await expect(archiveRow).toBeVisible()
    await archiveRow.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    await review.getByTestId('corp-cert-review-approve').click()
    await expect(review).toBeHidden()

    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
    await scanDrawer.getByTestId('corp-cert-scan-confirm').click()
    await expect(page.getByTestId('corp-cert-scan-message')).toContainText('工作台')

    await page.getByTestId('corp-cert-expire-holder').fill(holder)
    await page.getByTestId('corp-cert-expire-level').selectOption('YELLOW')
    await page.getByTestId('corp-cert-expire-status').selectOption('WARNING')
    await page.getByTestId('corp-cert-expire-search').click()
    const alertRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: holder })
    await expect(alertRow).toBeVisible()
    await expect(alertRow.getByTestId('corp-cert-level')).toHaveText('黄色')
    await expect(alertRow.getByTestId('corp-cert-notify')).toContainText('已通知：')
    await expect(page.getByTestId('corp-cert-expire-stats')).toContainText('本月换证')

    await alertRow.getByTestId('corp-cert-remind-btn').click()
    const remind = page.locator('.drawer.on').filter({ hasText: '催办' })
    await remind.getByTestId('corp-cert-remind-channel').selectOption('APP')
    await remind.getByTestId('corp-cert-remind-confirm').click()
    await expect(page.getByTestId('corp-cert-remind-message')).toContainText('已催办')
    await expect(alertRow.getByTestId('corp-cert-notify')).toContainText('催办')
    await page.screenshot({ path: `${shotDir}/acct-cert-155-expire-remind.png`, fullPage: true })

    await page.getByTestId('corp-cert-expire-level').selectOption('LOCKED')
    await page.getByTestId('corp-cert-expire-search').click()
    await expect(page.getByTestId('corp-cert-expire-empty')).toContainText('没有符合筛选的到期预警')
    await page.screenshot({ path: `${shotDir}/acct-cert-155-expire-empty.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})