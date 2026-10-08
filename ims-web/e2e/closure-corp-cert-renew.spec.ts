import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-69-screenshots'

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

async function searchHolder(page: Page, holder: string) {
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('input[placeholder="持有人"]').fill(holder)
  await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
  await listResp
}

/** Checklist **E2E-S6-05**（#69 · 纯 UI）· 换证：新有效期、旧证历史、预警解除、待办完成 */
test.describe('corp certificate renewal closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('renew expiring certificates keeps history and clears warnings', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    const stamp = Date.now()
    const samples = [
      { holder: `E2E-Cert-RN-Y-${stamp}`, days: 30, level: '黄色', oldStatus: '即将到期' },
      { holder: `E2E-Cert-RN-R-${stamp}`, days: 7, level: '红色', oldStatus: '即将到期' },
      { holder: `E2E-Cert-RN-L-${stamp}`, days: 0, level: '锁定', oldStatus: '已过期' },
    ]
    const newExpire = ymd(400)

    for (const [index, sample] of samples.entries()) {
      await page.getByTestId('corp-cert-create-btn').click()
      const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
      await expect(drawer).toBeVisible()
      await drawer.getByTestId('corp-cert-holder').fill(sample.holder)
      await drawer.getByTestId('corp-cert-no').fill(certNo(index + 1))
      await drawer.getByTestId('corp-cert-issue').fill('2020-01-01')
      await drawer.getByTestId('corp-cert-expire-date').fill(ymd(sample.days))
      const uploadResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
      )
      await drawer.getByTestId('corp-cert-save').click()
      const uploaded = (await (await uploadResp).json()) as { code: number }
      expect(uploaded.code).toBe(0)
      await expect(drawer).toBeHidden()

      await searchHolder(page, sample.holder)
      const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: sample.holder })
      await expect(row).toContainText('待审')
      await row.getByTestId('corp-cert-review-btn').click()
      const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
      const reviewResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
      )
      await review.getByTestId('corp-cert-review-approve').click()
      expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
      await expect(review).toBeHidden()
    }

    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
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
    await page.screenshot({ path: `${shotDir}/02-three-level-alerts.png`, fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    const todoTable = page.locator('.tbl-wrap table').nth(1)
    const lockedTitle = `证件锁定预警：${samples[2].holder}`
    await expect(todoTable.locator('tbody tr', { hasText: lockedTitle })).toBeVisible()

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })

    for (const [index, sample] of samples.entries()) {
      const alertRow = expireTable.locator('tbody tr', { hasText: sample.holder })
      await alertRow.getByTestId('corp-cert-renew-btn').click()
      const renew = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-save') })
      await expect(renew.getByTestId('corp-cert-renew-holder')).toHaveText(sample.holder)
      await renew.getByTestId('corp-cert-renew-no').fill(certNo(index + 4))
      await renew.getByTestId('corp-cert-renew-issue').fill('2024-01-01')
      await renew.getByTestId('corp-cert-renew-expire').fill(newExpire)
      await renew.getByTestId('corp-cert-renew-remark').fill('换证')
      if (index === 2) {
        await page.screenshot({ path: `${shotDir}/01-renew-form.png`, fullPage: true })
      }
      const uploadResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
      )
      await renew.getByTestId('corp-cert-renew-save').click()
      expect(((await (await uploadResp).json()) as { code: number }).code).toBe(0)
      await expect(renew).toBeHidden()

      await searchHolder(page, sample.holder)
      const pending = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: '待审' })
      await expect(pending).toBeVisible()
      await pending.getByTestId('corp-cert-review-btn').click()
      const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
      const reviewResp = page.waitForResponse(
        (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
      )
      await review.getByTestId('corp-cert-review-approve').click()
      expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
      await expect(review).toBeHidden()

      await expireTable.locator('tbody tr', { hasText: sample.holder }).getByTestId('corp-cert-renew-finish').click()
      const finish = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-confirm') })
      await expect(finish.getByTestId('corp-cert-renew-new-expire')).toHaveText(newExpire)
      if (index === 2) {
        await page.screenshot({ path: `${shotDir}/03-confirm-renew.png`, fullPage: true })
      }
      const renewResp = page.waitForResponse(
        (r) => r.url().includes('/cert/expire/') && r.url().includes('/renew') && r.request().method() === 'PUT',
      )
      await finish.getByTestId('corp-cert-renew-confirm').click()
      expect(((await (await renewResp).json()) as { code: number }).code).toBe(0)
      await expect(finish).toBeHidden()
      await expect(page.getByTestId('corp-cert-renew-message')).toContainText('旧证已归档')

      const resolved = expireTable.locator('tbody tr', { hasText: sample.holder })
      await expect(resolved).toContainText('已换证')
      await expect(resolved).toContainText(sample.level)
      await expect(resolved.getByTestId('corp-cert-renew-btn')).toHaveCount(0)

      await searchHolder(page, sample.holder)
      const archive = page.locator('.tbl-wrap').first()
      const history = archive.locator('tbody tr', { hasText: sample.oldStatus === '已过期' ? ymd(sample.days) : ymd(sample.days) })
      await expect(archive.locator('tbody tr', { hasText: '已回收' })).toContainText(ymd(sample.days))
      await expect(archive.locator('tbody tr', { hasText: '生效' })).toContainText(newExpire)
      await expect(history).toBeVisible()
    }

    await page.screenshot({ path: `${shotDir}/04-recycled-history.png`, fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    await expect(page.locator('.tbl-wrap table').nth(1).locator('tbody tr', { hasText: lockedTitle })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/05-workbench-todo-cleared.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
