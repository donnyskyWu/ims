import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-127-screenshots'

function ymd(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** #127 · 数字化率横幅、待审 1033、默认 L1 的 1034、L2 水印链接、L3 明文仍禁止下载 */
test.describe('corp certificate digital metrics and file url closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('banner, pending block, level config, then watermark and plaintext preview', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    const banner = page.getByTestId('corp-cert-digital-banner')
    await expect(banner).toContainText('数字化率')
    await expect(banner).toContainText('95%')
    const bannerText = await banner.innerText()
    const mark = bannerText.includes('未达标') ? '未达标' : '达标'
    await page.getByTestId('corp-cert-digital-open').click()
    const modal = page.getByTestId('corp-cert-digital-modal')
    await expect(modal).toContainText('目标线 95%')
    await expect(modal).toContainText(mark)
    const expected = (await page.getByTestId('corp-cert-digital-expected').innerText()).trim()
    const digitized = (await page.getByTestId('corp-cert-digital-count').innerText()).trim()
    expect(bannerText).toContain(expected)
    expect(bannerText).toContain(digitized)
    await page.screenshot({ path: `${shotDir}/01-digital-banner.png`, fullPage: true })
    await page.locator('.drawer.on').filter({ hasText: '数字化率统计' }).getByRole('button', { name: '关闭' }).click()

    await expect(page.getByTestId('corp-cert-level-panel')).toBeVisible()
    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')

    const stamp = Date.now()
    const holder = `E2E-Cert-URL-${stamp}`
    const number = `URL${stamp}`
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
    const uploaded = (await (await uploadResp).json()) as { code: number }
    expect(uploaded.code).toBe(0)
    await expect(create).toBeHidden()

    await page.locator('input[placeholder="持有人"]').fill(holder)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
    await expect(row).toContainText('待审')

    const pendingResp = page.waitForResponse((r) => r.url().includes('/file-url') && r.status() === 200)
    await row.getByTestId('corp-cert-file-btn').click()
    const pending = (await (await pendingResp).json()) as { code: number }
    expect(pending.code).toBe(1033)
    const fileDrawer = page.locator('.drawer.on').filter({ hasText: '原图链接' })
    await expect(fileDrawer.getByTestId('corp-cert-file-error')).toContainText('1033')
    await expect(fileDrawer).not.toContainText(number)
    await page.screenshot({ path: `${shotDir}/02-pending-1033.png`, fullPage: true })
    await fileDrawer.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await review.getByTestId('corp-cert-review-approve').click()
    expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
    await expect(review).toBeHidden()
    await expect(row).toContainText('生效')

    const deniedResp = page.waitForResponse((r) => r.url().includes('/file-url') && r.status() === 200)
    await row.getByTestId('corp-cert-file-btn').click()
    expect(((await (await deniedResp).json()) as { code: number }).code).toBe(1034)
    await expect(fileDrawer.getByTestId('corp-cert-file-error')).toContainText('1034')
    await page.screenshot({ path: `${shotDir}/03-level-1034.png`, fullPage: true })
    await fileDrawer.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('corp-cert-level-role').fill('sys:admin')
    await page.getByTestId('corp-cert-level-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('下次查看即按新级别')
    await expect(page.getByTestId('corp-cert-level-current')).toContainText('sys:admin')

    const watermarkResp = page.waitForResponse((r) => r.url().includes('/file-url') && r.status() === 200)
    await row.getByTestId('corp-cert-file-btn').click()
    const watermark = (await (await watermarkResp).json()) as {
      code: number
      data?: { expiresInSeconds?: number; signedUrl?: string; watermark?: { text?: string } }
    }
    expect(watermark.code).toBe(0)
    expect(watermark.data?.expiresInSeconds).toBe(60)
    expect(watermark.data?.signedUrl || '').toContain('/cert/archive/file?token=')
    expect(watermark.data?.watermark?.text || '').toContain('管理员')
    expect(JSON.stringify(watermark)).not.toContain(number)
    await expect(fileDrawer.getByTestId('corp-cert-file-watermark')).toContainText('管理员')
    await expect(fileDrawer.getByTestId('corp-cert-file-ttl')).toContainText('禁止下载')
    await expect(fileDrawer.getByTestId('corp-cert-file-preview')).toContainText('禁止下载')
    await page.screenshot({ path: `${shotDir}/04-l2-watermark.png`, fullPage: true })
    await fileDrawer.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('corp-cert-l3-user').selectOption({ label: '管理员' })
    await page.getByTestId('corp-cert-l3-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('下次查看即按新级别')
    const plainResp = page.waitForResponse((r) => r.url().includes('/file-url') && r.status() === 200)
    await row.getByTestId('corp-cert-file-btn').click()
    const plain = (await (await plainResp).json()) as { code: number; data?: { watermark?: { text?: string } } }
    expect(plain.code).toBe(0)
    expect(plain.data?.watermark).toBeUndefined()
    expect(JSON.stringify(plain)).not.toContain(number)
    await expect(fileDrawer.getByTestId('corp-cert-file-plain')).toContainText('明文预览，禁止下载')
    await expect(fileDrawer.getByTestId('corp-cert-file-watermark')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/05-l3-plain.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
