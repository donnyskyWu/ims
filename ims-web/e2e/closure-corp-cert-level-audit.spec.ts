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
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/resource/certificate')
  await ready
  await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
  await expect(page.getByTestId('corp-cert-level-panel')).toBeVisible()
}

/** #169 · 等级配置保存水印样式；审计日志按级别筛选并展示 IP/设备 */
test.describe('corp certificate level style and audit filter closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('save watermark style, show it on the file link, then filter audit by level', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await openCertificate(page)

    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')
    await expect(page.getByTestId('corp-cert-level-table')).toContainText('未配置')
    await expect(page.getByTestId('corp-cert-level-current')).toContainText('0.12')
    await expect(page.getByTestId('corp-cert-level-current')).toContainText('右下')

    await page.getByTestId('corp-cert-level-role').fill('sys:admin')
    await page.getByTestId('corp-cert-level-opacity').fill('0.2')
    await page.getByTestId('corp-cert-level-position').selectOption('top-left')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/level-config') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-level-save').click()
    const savedResponse = await saveResp
    const saved = (await savedResponse.json()) as { code: number }
    const payload = savedResponse.request().postDataJSON() as { opacity?: number; position?: string; rules?: unknown[] }
    expect(saved.code).toBe(0)
    expect(payload.opacity).toBeCloseTo(0.2, 2)
    expect(payload.position).toBe('top-left')
    expect(JSON.stringify(payload.rules || [])).toContain('sys:admin')
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('下次查看即按新级别')
    const current = page.getByTestId('corp-cert-level-current')
    await expect(current).toContainText('sys:admin')
    await expect(current).toContainText('0.20')
    await expect(current).toContainText('左上')
    const table = page.getByTestId('corp-cert-level-table')
    await expect(table).toContainText('默认全员')
    await expect(table).toContainText('sys:admin')
    await expect(table).toContainText('0.20')
    await expect(table).toContainText('左上')
    await page.screenshot({ path: `${shotDir}/cert-169-level-style.png`, fullPage: true })

    const stamp = Date.now()
    const holder = `E2E-Cert-LV-${stamp}`
    const number = `LV${stamp}`
    await page.getByTestId('corp-cert-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await create.getByTestId('corp-cert-holder').fill(holder)
    await create.getByTestId('corp-cert-no').fill(number)
    await create.getByTestId('corp-cert-issue').fill('2020-01-01')
    await create.getByTestId('corp-cert-expire-date').fill(ymd(400))
    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await create.getByTestId('corp-cert-save').click()
    expect(((await (await uploadResp).json()) as { code: number }).code).toBe(0)
    await expect(create).toBeHidden()

    await page.locator('input[placeholder="持有人"]').fill(holder)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
    await row.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await review.getByTestId('corp-cert-review-approve').click()
    expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
    await expect(review).toBeHidden()

    const fileResp = page.waitForResponse((r) => r.url().includes('/file-url') && r.status() === 200)
    await row.getByTestId('corp-cert-file-btn').click()
    const file = (await (await fileResp).json()) as {
      code: number
      data?: { watermark?: { text?: string; opacity?: number; position?: string }; signedUrl?: string }
    }
    expect(file.code).toBe(0)
    expect(file.data?.watermark?.opacity).toBeCloseTo(0.2, 2)
    expect(file.data?.watermark?.position).toBe('top-left')
    expect(JSON.stringify(file)).not.toContain(number)
    const fileDrawer = page.locator('.drawer.on').filter({ hasText: '原图链接' })
    await expect(fileDrawer.getByTestId('corp-cert-file-style')).toContainText('0.20')
    await expect(fileDrawer.getByTestId('corp-cert-file-style')).toContainText('左上')
    await expect(fileDrawer.getByTestId('corp-cert-file-ttl')).toContainText('禁止下载')
    await page.screenshot({ path: `${shotDir}/cert-169-file-watermark.png`, fullPage: true })
    await fileDrawer.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('corp-cert-audit-holder').fill(holder)
    await page.getByTestId('corp-cert-audit-level').selectOption('2')
    await page.getByTestId('corp-cert-audit-from').fill(ymd(0))
    await page.getByTestId('corp-cert-audit-to').fill('')
    await page.getByTestId('corp-cert-audit-search').click()
    await expect(page.getByTestId('corp-cert-audit-panel')).toContainText('请同时填写开始和结束日期')

    await page.getByTestId('corp-cert-audit-from').fill('')
    const auditResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/view-logs') && r.url().includes('viewLevel=2') && r.status() === 200,
    )
    await page.getByTestId('corp-cert-audit-search').click()
    const audited = (await (await auditResp).json()) as { code: number; data?: { total?: number } }
    expect(audited.code).toBe(0)
    expect(audited.data?.total).toBe(1)
    const auditTable = page.getByTestId('corp-cert-audit-table')
    await expect(auditTable).toContainText('IP/设备')
    const hit = auditTable.locator('tbody tr', { hasText: holder })
    await expect(hit).toContainText('L2')
    await expect(hit.getByTestId('corp-cert-audit-ip')).not.toHaveText('—')
    await expect(page.getByTestId('corp-cert-audit-pager')).toContainText('第 1 / 1 页')
    await page.screenshot({ path: `${shotDir}/cert-169-audit-level.png`, fullPage: true })

    await page.getByTestId('corp-cert-audit-level').selectOption('1')
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/cert/security/view-logs') && r.url().includes('viewLevel=1') && r.status() === 200,
    )
    await page.getByTestId('corp-cert-audit-search').click()
    const emptied = (await (await emptyResp).json()) as { code: number; data?: { total?: number } }
    expect(emptied.code).toBe(0)
    expect(emptied.data?.total).toBe(0)
    await expect(auditTable).toContainText('没有查看记录')
    await expect(page.getByTestId('corp-cert-audit-empty')).toContainText('当前筛选下没有匹配的查看记录')
    await page.screenshot({ path: `${shotDir}/cert-169-audit-empty.png`, fullPage: true })

    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')
    expect(pageErrors).toEqual([])
  })
})
