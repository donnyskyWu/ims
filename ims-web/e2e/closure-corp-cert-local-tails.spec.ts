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

async function openCertificate(page: Page) {
  const ready = page.waitForResponse(
    (r) => r.url().includes('/cert/archive/digital-metrics') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/resource/certificate')
  await ready
  await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
}

/** #199 · 证件列表筛选空态、白名单追加/移除、详情最近查看、审计日期倒置、异常报告本地导出桩 */
test.describe('corp certificate local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty filter, whitelist edges, recent audit, inverted dates, and local risk export', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await openCertificate(page)

    const banner = page.getByTestId('corp-cert-digital-banner')
    await expect(banner).toContainText('数字化率')
    await expect(banner).toContainText('95%')
    await page.getByTestId('corp-cert-digital-open').click()
    const stats = page.getByTestId('corp-cert-digital-modal')
    await expect(stats.getByTestId('corp-cert-digital-type-empty')).toContainText('按证件类型的缺口暂无分项')
    await page.screenshot({ path: `${shotDir}/cert-199-digital-type-empty.png`, fullPage: true })
    await page.locator('.drawer.on').filter({ hasText: '数字化率统计' }).getByRole('button', { name: '关闭' }).click()

    const missing = `E2E-Cert-NONE-${Date.now()}`
    await page.locator('input[placeholder="持有人"]').fill(missing)
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await emptyResp
    const listEmpty = page.getByTestId('corp-cert-list-empty')
    await expect(listEmpty).toContainText('当前筛选下没有证件')
    await expect(listEmpty).toContainText('换一个持有人或状态')
    await page.screenshot({ path: `${shotDir}/cert-199-list-empty.png`, fullPage: true })
    await page.locator('form.qbar').first().getByRole('button', { name: '重置' }).click()

    await expect(page.getByTestId('corp-cert-level-panel')).toBeVisible()
    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')
    await expect(page.getByTestId('corp-cert-l3-empty')).toContainText('白名单为空')

    await page.getByTestId('corp-cert-l3-user').selectOption({ label: '管理员' })
    const addResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/level-config') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-l3-save').click()
    const added = (await (await addResp).json()) as { code: number }
    expect(added.code).toBe(0)
    await expect(page.getByTestId('corp-cert-l3-item')).toContainText('管理员')
    await page.getByTestId('corp-cert-l3-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('该用户已在白名单')
    await page.screenshot({ path: `${shotDir}/cert-199-l3-whitelist.png`, fullPage: true })

    const removeResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/level-config') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-l3-remove').click()
    expect(((await (await removeResp).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已移出白名单')
    await expect(page.getByTestId('corp-cert-l3-empty')).toBeVisible()

    await page.locator('input[placeholder="持有人"]').fill('E2E-Cert-Watermark')
    const listResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/resource/certificate/page') &&
        r.url().includes('holderName=E2E-Cert-Watermark') &&
        r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('tbody tr', { hasText: 'E2E-Cert-Watermark' }).first()
    await expect(row).toBeVisible()
    const viewResp = page.waitForResponse(
      (r) => r.url().includes('/certificate/') && r.url().includes('/view') && r.status() === 200,
    )
    await row.getByTestId('corp-cert-view-btn').click()
    expect(((await (await viewResp).json()) as { code: number }).code).toBe(0)
    const drawer = page.locator('.drawer.on').filter({ hasText: '证件查看' })
    const recent = drawer.getByTestId('corp-cert-detail-audit')
    await expect(recent).toContainText('最近查看')
    await expect(recent.getByTestId('corp-cert-detail-audit-row').first()).toContainText('管理员')
    await expect(recent.getByTestId('corp-cert-detail-audit-empty')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/cert-199-detail-audit.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('corp-cert-audit-from').fill(ymd(1))
    await page.getByTestId('corp-cert-audit-to').fill(ymd(-1))
    await page.getByTestId('corp-cert-audit-search').click()
    await expect(page.getByTestId('corp-cert-audit-error')).toContainText('开始日期不能晚于结束日期')
    await page.screenshot({ path: `${shotDir}/cert-199-audit-range.png`, fullPage: true })

    await page.getByTestId('corp-cert-risk-export').click()
    const exportDrawer = page.locator('.drawer.on').filter({ hasText: '导出异常访问报告' })
    await expect(exportDrawer.getByTestId('corp-cert-risk-export-modal')).toBeVisible()
    await exportDrawer.getByTestId('corp-cert-risk-export-confirm').click()
    await expect(page.getByTestId('corp-cert-risk-export-result')).toContainText('已生成异常访问报告（本地桩，未外发）')
    await page.screenshot({ path: `${shotDir}/cert-199-risk-export.png`, fullPage: true })

    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')
    expect(pageErrors).toEqual([])
  })
})
