import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-71-screenshots'
const ACCOUNT_NO = 'AC-E2E-LIVE1045'
const PHONE_CODE = 'E2E-LIVE1045-PHONE'
const HOLDER = 'E2E-Live-1045'

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

async function resolveIds(page: Page) {
  await page.goto('/ims/corp/account/douyin')
  await page.locator('input[placeholder="账号编号/昵称"]').fill(ACCOUNT_NO)
  const accListResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await accListResp
  const accRow = page.locator('tbody tr', { hasText: ACCOUNT_NO }).first()
  await expect(accRow).toBeVisible({ timeout: 15_000 })
  const accDetailResp = page.waitForResponse(
    (r) => /\/corp\/account\/\d+/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
  )
  await accRow.getByRole('button', { name: '详情' }).click()
  const accDetailBody = (await (await accDetailResp).json()) as {
    code: number
    data?: { id?: number; realnameId?: number }
  }
  expect(accDetailBody.code).toBe(0)
  const accountId = accDetailBody.data?.id
  const realnamePersonId = accDetailBody.data?.realnameId
  expect(accountId).toBeTruthy()
  expect(realnamePersonId).toBeTruthy()

  await page.goto('/ims/corp/device/phone')
  await page.locator('input[placeholder="设备编号 / 型号"]').fill(PHONE_CODE)
  const phoneListResp = page.waitForResponse(
    (r) => r.url().includes('/corp/device/phone/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  const phoneListBody = (await (await phoneListResp).json()) as {
    code: number
    data?: { list?: Array<{ id?: number; phoneCode?: string; deviceNumber?: string }> }
  }
  expect(phoneListBody.code).toBe(0)
  const phoneHit = phoneListBody.data?.list?.find(
    (row) => row.phoneCode === PHONE_CODE || row.deviceNumber === PHONE_CODE,
  )
  expect(phoneHit?.id).toBeTruthy()
  return { accountId: accountId!, realnamePersonId: realnamePersonId!, deviceId: phoneHit!.id! }
}

/** Checklist **E2E-S2-04**（#71 · 纯 UI）· 锁定证件拦截开播 **1045**，换证后可确认开播 */
test.describe('live locked certificate closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('expired certificate blocks going live until renewed', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    const ids = await resolveIds(page)

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
    await page.getByTestId('corp-cert-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-cert-holder').fill(HOLDER)
    await create.getByTestId('corp-cert-no').fill(certNo(1))
    await create.getByTestId('corp-cert-issue').fill('2020-01-01')
    await create.getByTestId('corp-cert-expire-date').fill(ymd(0))
    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await create.getByTestId('corp-cert-save').click()
    expect(((await (await uploadResp).json()) as { code: number }).code).toBe(0)
    await expect(create).toBeHidden()

    await searchHolder(page, HOLDER)
    const pending = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: HOLDER })
    await expect(pending).toContainText('待审')
    await pending.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
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
    const scanned = (await (await scanResp).json()) as { code: number; data?: { created?: number } }
    expect(scanned.code).toBe(0)
    expect(scanned.data?.created).toBeGreaterThanOrEqual(1)
    const alertRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: HOLDER })
    await expect(alertRow).toBeVisible()
    await expect(alertRow).toContainText('锁定')
    await page.screenshot({ path: `${shotDir}/01-locked-cert.png`, fullPage: true })

    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建场次登记' }).click()
    const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
    await expect(drawer).toBeVisible()
    await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
    await drawer.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
    await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
    await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(`E2E 1045 ${Date.now()}`)
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const blocked = (await (await blockedResp).json()) as { code: number; msg?: string }
    expect(blocked.code).toBe(1045)
    await expect(drawer.getByTestId('live-register-error')).toContainText('1045')
    await expect(drawer).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-register-blocked-1045.png`, fullPage: true })

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
    const expireTable = page.getByTestId('corp-cert-expire-table')
    await expireTable.locator('tbody tr', { hasText: HOLDER }).getByTestId('corp-cert-renew-btn').click()
    const renew = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-save') })
    await expect(renew.getByTestId('corp-cert-renew-holder')).toHaveText(HOLDER)
    const newExpire = ymd(400)
    await renew.getByTestId('corp-cert-renew-no').fill(certNo(2))
    await renew.getByTestId('corp-cert-renew-issue').fill('2024-01-01')
    await renew.getByTestId('corp-cert-renew-expire').fill(newExpire)
    await renew.getByTestId('corp-cert-renew-remark').fill('换证后开播')
    await page.screenshot({ path: `${shotDir}/03-renew-form.png`, fullPage: true })
    const renewUpload = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await renew.getByTestId('corp-cert-renew-save').click()
    expect(((await (await renewUpload).json()) as { code: number }).code).toBe(0)
    await expect(renew).toBeHidden()

    await searchHolder(page, HOLDER)
    const newPending = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: '待审' })
    await expect(newPending).toBeVisible()
    await newPending.getByTestId('corp-cert-review-btn').click()
    const reviewNew = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewNewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewNew.getByTestId('corp-cert-review-approve').click()
    expect(((await (await reviewNewResp).json()) as { code: number }).code).toBe(0)
    await expect(reviewNew).toBeHidden()

    await expireTable.locator('tbody tr', { hasText: HOLDER }).getByTestId('corp-cert-renew-finish').click()
    const finish = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-confirm') })
    await expect(finish.getByTestId('corp-cert-renew-new-expire')).toHaveText(newExpire)
    const renewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/') && r.url().includes('/renew') && r.request().method() === 'PUT',
    )
    await finish.getByTestId('corp-cert-renew-confirm').click()
    expect(((await (await renewResp).json()) as { code: number }).code).toBe(0)
    await expect(finish).toBeHidden()
    await expect(page.getByTestId('corp-cert-renew-message')).toContainText('旧证已归档')
    await expect(expireTable.locator('tbody tr', { hasText: HOLDER })).toContainText('已换证')
    await searchHolder(page, HOLDER)
    const archive = page.locator('.tbl-wrap').first()
    await expect(archive.locator('tbody tr', { hasText: '已回收' })).toBeVisible()
    await expect(archive.locator('tbody tr', { hasText: '生效' })).toContainText(newExpire)
    await page.screenshot({ path: `${shotDir}/04-renewed-archive.png`, fullPage: true })

    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建场次登记' }).click()
    const again = page.locator('.drawer').filter({ hasText: '开播登记' })
    await again.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
    await again.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
    await again.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
    await again.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(`E2E 1045 renewed ${Date.now()}`)
    const okResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
    )
    await again.getByRole('button', { name: '提交登记' }).click()
    const allowed = (await (await okResp).json()) as { code: number; data?: { sessionCode?: string; sessionStatus?: string } }
    expect(allowed.code).toBe(0)
    const sessionCode = allowed.data?.sessionCode
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    const detail = page.locator('.drawer').filter({ hasText: '场次' })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    if (allowed.data?.sessionStatus === 'PENDING_RISK_CHECK') {
      await detail.locator('.tab', { hasText: '风控登记' }).click()
      const riskResp = page.waitForResponse(
        (r) => r.url().includes('/risk-check') && r.request().method() === 'POST' && r.status() === 200,
      )
      await detail.getByRole('button', { name: '执行风控' }).click()
      const riskBody = (await (await riskResp).json()) as { code: number }
      expect(riskBody.code).toBe(0)
    }
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/live/register/') && r.url().includes('/start') && r.request().method() === 'PUT',
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('LIVE')
    await page.screenshot({ path: `${shotDir}/05-live-started.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
