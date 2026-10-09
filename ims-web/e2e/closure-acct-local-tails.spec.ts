import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'

function shanghaiDay() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Shanghai', day: 'numeric' }).formatToParts(new Date())
  return Number(parts.find((part) => part.type === 'day')?.value || '0')
}

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

/** #204 账号状态色标、时间线中文类型、核对窗口文案、归还筛选空态、证件状态色标。 */
test.describe('account local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('ledger status badge, timeline label, asset empty, and reconcile window', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/account/douyin')
    await expect(page.locator('h1')).toContainText('抖音')

    const windowText =
      shanghaiDay() <= 5
        ? '请于 5 日前完成上月核对'
        : '账实核对窗口为每月 1–5 日。当前不在窗口内，仍可按月触发核对。'
    await expect(page.getByTestId('acct-reconcile-window')).toContainText(windowText)

    await page.getByTestId('acct-filter-keyword').fill('AC-E2E-POOL')
    const listed = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.url().includes('keyword=') && r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await listed
    const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: 'AC-E2E-POOL' })
    await expect(row).toBeVisible()
    const status = row.getByTestId('acct-status-tag')
    await expect(status).toBeVisible()
    await expect(status).toHaveText(/在用|池可领用|冻结|已归还|已注销/)
    await page.screenshot({ path: `${shotDir}/acct-204-status-badge.png`, fullPage: true })

    await row.getByRole('button', { name: '详情' }).click()
    const detail = page.locator('.drawer.on').filter({ hasText: '详情' })
    await expect(detail.getByTestId('acct-detail-status')).toBeVisible()
    await detail.getByRole('button', { name: '领用时间线' }).click()
    const timeline = detail.locator('.timeline-list')
    const empty = detail.getByText('暂无领用/归还事件')
    if (await timeline.count()) {
      const event = detail.getByTestId('acct-timeline-event').first()
      await expect(event.getByTestId('acct-timeline-label')).toHaveText(/登记|领用|流转|归还|冲话费|冻结|解冻|注销|回收回池/)
      await expect(event).toContainText(/APPLY|RETURN|TRANSFER|FREEZE|UNFREEZE|RECHARGE|REGISTER|RECYCLE|CANCEL/)
    } else {
      await expect(empty).toBeVisible()
    }
    await detail.getByRole('button', { name: '关联资产' }).click()
    const assetEmpty = detail.getByTestId('acct-asset-empty')
    const assetRow = detail.getByTestId('acct-asset-row')
    await expect(assetEmpty.or(assetRow.first())).toBeVisible()
    if (await assetEmpty.count()) {
      await expect(assetEmpty).toContainText('该账号暂无关联资产')
    }
    await page.screenshot({ path: `${shotDir}/acct-204-timeline-asset.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('return list filter empty and cert expiry status badge', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/account/return')
    await expect(page.locator('h1')).toHaveText('离职归还')
    await page.getByTestId('return-filter-no').fill('ZZ-NO-RETURN-204')
    await page.getByTestId('return-filter-status').selectOption('CLOSED')
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/account/return/list') && r.url().includes('returnNo=') && r.status() === 200,
    )
    await page.getByTestId('return-filter-search').click()
    await filtered
    const empty = page.getByTestId('return-list-empty')
    await expect(empty).toContainText('没有符合筛选的离职归还单')
    await expect(empty).toContainText('换一个单号或状态')
    await page.screenshot({ path: `${shotDir}/acct-204-return-empty.png`, fullPage: true })

    const holder = `E2E-Cert-204-${Date.now()}`
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
    await page.getByTestId('corp-cert-expire-status').selectOption('WARNING')
    await page.getByTestId('corp-cert-expire-search').click()
    const certRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: holder })
    await expect(certRow.getByTestId('corp-cert-status')).toContainText('预警中')
    await page.screenshot({ path: `${shotDir}/acct-204-cert-status.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
