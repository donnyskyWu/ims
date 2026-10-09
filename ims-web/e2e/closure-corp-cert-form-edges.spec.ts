import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts'
const VALID_ID = '110101199003078515'
const BAD_ID = '110101199003078516'

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

async function fillAndSave(page: Page, fields: { holder: string; type?: string; no: string; issue: string; expire: string; fileKey?: string }) {
  await page.getByTestId('corp-cert-create-btn').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
  await drawer.getByTestId('corp-cert-holder').fill(fields.holder)
  if (fields.type) await drawer.getByTestId('corp-cert-type').selectOption(fields.type)
  await drawer.getByTestId('corp-cert-no').fill(fields.no)
  await drawer.getByTestId('corp-cert-issue').fill(fields.issue)
  await drawer.getByTestId('corp-cert-expire-date').fill(fields.expire)
  if (fields.fileKey !== undefined) await drawer.getByTestId('corp-cert-file-key').fill(fields.fileKey)
  await drawer.getByTestId('corp-cert-save').click()
  return drawer
}

/** #238 · 录入/换证/驳回校验，级别边界文案，原图空态。不重做筛选空态、白名单追加或类型有效期筛选。 */
test.describe('corp certificate form and level edge closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('form validation, reject remark, opacity edges, renew window, and file empty', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const puts: string[] = []
    const uploads: string[] = []
    const reviews: string[] = []
    page.on('request', (request) => {
      const url = request.url()
      if (request.method() !== 'PUT' && request.method() !== 'POST') return
      if (url.includes('/cert/security/level-config')) puts.push(request.method())
      if (url.includes('/cert/archive/upload')) uploads.push(request.method())
      if (url.includes('/review')) reviews.push(request.method())
    })
    await page.route('**/system/user/page**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, msg: 'ok', data: { list: [], total: 0 } }),
      })
    })
    await loginAdmin(page)
    await openCertificate(page)

    await expect(page.getByTestId('corp-cert-level-edge')).toContainText('L1 范围不可改')
    await expect(page.getByTestId('corp-cert-level-table')).toContainText('范围不可改')
    await expect(page.getByTestId('corp-cert-l3-users-empty')).toContainText('没有可选的本地用户')
    await page.screenshot({ path: `${shotDir}/cert-238-level-edge.png`, fullPage: true })

    await page.getByTestId('corp-cert-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await create.getByTestId('corp-cert-holder').fill('')
    await create.getByTestId('corp-cert-save').click()
    await expect(create.getByTestId('corp-cert-form-error')).toContainText('持有人必填')
    const holder = `E2E-Cert-238-${Date.now()}`
    await create.getByTestId('corp-cert-holder').fill(holder)
    await create.getByTestId('corp-cert-no').fill('1234567')
    await create.getByTestId('corp-cert-save').click()
    await expect(create.getByTestId('corp-cert-form-error')).toContainText('证件号至少 8 位')
    await create.getByTestId('corp-cert-no').fill('12345678')
    await expect(create.getByTestId('corp-cert-no-hint')).toContainText('不足 18 位')
    await create.getByTestId('corp-cert-no').fill(BAD_ID)
    await expect(create.getByTestId('corp-cert-no-hint')).toContainText('身份证校验位不正确')
    await expect(create.getByTestId('corp-cert-no-hint')).toContainText('仍可提交')
    await create.getByTestId('corp-cert-no').fill(VALID_ID)
    await expect(create.getByTestId('corp-cert-no-hint')).toContainText('身份证校验位正确')
    await create.getByTestId('corp-cert-issue').fill('2020-01-01')
    await create.getByTestId('corp-cert-expire-date').fill('2020-01-01')
    await create.getByTestId('corp-cert-save').click()
    await expect(create.getByTestId('corp-cert-form-error')).toContainText('有效期须晚于签发日期')
    await create.getByTestId('corp-cert-expire-date').fill(ymd(400))
    await create.getByTestId('corp-cert-file-key').fill('   ')
    await create.getByTestId('corp-cert-save').click()
    await expect(create.getByTestId('corp-cert-form-error')).toContainText('扫描件标识必填')
    expect(uploads).toEqual([])
    await page.screenshot({ path: `${shotDir}/cert-238-form-error.png`, fullPage: true })
    await create.getByRole('button', { name: '取消' }).click()

    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    const saved = await fillAndSave(page, {
      holder,
      no: VALID_ID,
      issue: '2020-01-01',
      expire: ymd(400),
      fileKey: 'local/cert/upload',
    })
    expect(((await (await uploadResp).json()) as { code: number }).code).toBe(0)
    await expect(saved).toBeHidden()

    await page.locator('input[placeholder="持有人"]').fill(holder)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: holder })
    await row.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewBefore = reviews.length
    await review.getByTestId('corp-cert-review-reject').click()
    await expect(review.getByTestId('corp-cert-review-error')).toContainText('驳回须填写原因')
    await review.getByTestId('corp-cert-review-remark').fill('   ')
    await review.getByTestId('corp-cert-review-reject').click()
    await expect(review.getByTestId('corp-cert-review-error')).toContainText('驳回须填写原因')
    await review.getByTestId('corp-cert-review-remark').fill('原因'.repeat(101))
    await review.getByTestId('corp-cert-review-reject').click()
    await expect(review.getByTestId('corp-cert-review-error')).toContainText('不超过 200 字')
    expect(reviews.length).toBe(reviewBefore)
    await page.screenshot({ path: `${shotDir}/cert-238-review-remark.png`, fullPage: true })
    await review.getByTestId('corp-cert-review-remark').fill('影像模糊')
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await review.getByTestId('corp-cert-review-reject').click()
    expect(((await (await rejectResp).json()) as { code: number }).code).toBe(0)
    await expect(review).toBeHidden()
    await expect(page.locator('.tbl-wrap').first()).toContainText('没有符合筛选的记录')

    await page.getByTestId('corp-cert-level-opacity').fill('0.05')
    await expect(page.getByTestId('corp-cert-level-opacity-edge')).toContainText('已到透明度下限 0.05')
    await page.getByTestId('corp-cert-level-opacity').fill('0.3')
    await expect(page.getByTestId('corp-cert-level-opacity-edge')).toContainText('已到透明度上限 0.30')
    await page.screenshot({ path: `${shotDir}/cert-238-opacity-edge.png`, fullPage: true })
    await page.getByTestId('corp-cert-level-role').fill('sys:admin')
    await page.getByTestId('corp-cert-level-opacity').fill('0.04')
    const putsBefore = puts.length
    await page.getByTestId('corp-cert-level-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('水印透明度须在 0.05 到 0.3')
    expect(puts.length).toBe(putsBefore)
    await page.getByTestId('corp-cert-level-opacity').fill('0.12')
    await page.getByTestId('corp-cert-level-role').fill('sys admin')
    await page.getByTestId('corp-cert-level-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('角色编码不能含空格')
    await page.getByTestId('corp-cert-level-role').fill('r'.repeat(65))
    await page.getByTestId('corp-cert-level-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('角色编码不超过 64 字')
    await page.getByTestId('corp-cert-level-role').fill('   ')
    await page.getByTestId('corp-cert-level-save').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('角色编码必填')
    expect(puts.length).toBe(putsBefore)

    const nearHolder = `E2E-Cert-238N-${Date.now()}`
    const nearResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    const nearDrawer = await fillAndSave(page, {
      holder: nearHolder,
      type: 'PASSPORT',
      no: `P${Date.now()}`,
      issue: '2020-01-01',
      expire: ymd(10),
      fileKey: 'local/cert/renew',
    })
    expect(((await (await nearResp).json()) as { code: number }).code).toBe(0)
    await expect(nearDrawer).toBeHidden()
    await page.locator('input[placeholder="持有人"]').fill(nearHolder)
    const nearList = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await nearList
    const nearRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: nearHolder })
    await nearRow.getByTestId('corp-cert-review-btn').click()
    const nearReview = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await nearReview.getByTestId('corp-cert-review-approve').click()
    expect(((await (await approveResp).json()) as { code: number }).code).toBe(0)
    await page.getByTestId('corp-cert-scan-btn').click()
    const scanResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/scan') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.locator('.drawer.on').filter({ hasText: '扫描到期' }).getByTestId('corp-cert-scan-confirm').click()
    expect(((await (await scanResp).json()) as { code: number }).code).toBe(0)
    await page.getByTestId('corp-cert-expire-holder').fill(nearHolder)
    const expireResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-cert-expire-search').click()
    await expireResp
    const expireRow = page.getByTestId('corp-cert-expire-table').locator('tbody tr', { hasText: nearHolder })
    await expireRow.getByTestId('corp-cert-renew-btn').click()
    const renew = page.locator('.drawer.on').filter({ hasText: '换证' })
    const uploadsBeforeRenew = uploads.length
    await renew.getByTestId('corp-cert-renew-save').click()
    await expect(renew.getByTestId('corp-cert-renew-error')).toContainText('证件号至少 8 位')
    await renew.getByTestId('corp-cert-renew-no').fill(`N${Date.now()}`)
    await renew.getByTestId('corp-cert-renew-issue').fill('2024-01-01')
    await renew.getByTestId('corp-cert-renew-expire').fill(ymd(10))
    await renew.getByTestId('corp-cert-renew-save').click()
    await expect(renew.getByTestId('corp-cert-renew-error')).toContainText('新证有效期须晚于旧证，且超出 30 天预警')
    expect(uploads.length).toBe(uploadsBeforeRenew)
    await page.screenshot({ path: `${shotDir}/cert-238-renew-window.png`, fullPage: true })
    await renew.getByRole('button', { name: '取消' }).click()

    await page.getByTestId('corp-cert-level-reset').click()
    await expect(page.getByTestId('corp-cert-level-message')).toContainText('已恢复默认')
    const fileHolder = `E2E-Cert-238F-${Date.now()}`
    const fileResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    const fileDrawerCreate = await fillAndSave(page, {
      holder: fileHolder,
      type: 'PASSPORT',
      no: `F${Date.now()}`,
      issue: '2020-01-01',
      expire: ymd(500),
      fileKey: 'local/cert/file',
    })
    expect(((await (await fileResp).json()) as { code: number }).code).toBe(0)
    await expect(fileDrawerCreate).toBeHidden()
    await page.locator('input[placeholder="持有人"]').fill(fileHolder)
    const fileList = page.waitForResponse(
      (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
    await fileList
    const fileRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: fileHolder })
    await fileRow.getByTestId('corp-cert-review-btn').click()
    const fileReview = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    await fileReview.getByTestId('corp-cert-review-approve').click()
    await expect(fileReview).toBeHidden()

    let releaseFile = () => {}
    const fileGate = new Promise<void>((resolve) => {
      releaseFile = resolve
    })
    await page.route('**/cert/archive/**/file-url**', async (route) => {
      await fileGate
      await route.continue()
    })
    await fileRow.getByTestId('corp-cert-file-btn').click()
    const fileDrawer = page.locator('.drawer.on').filter({ hasText: '原图链接' })
    await expect(fileDrawer.getByTestId('corp-cert-file-loading')).toContainText('正在获取原图链接')
    await page.screenshot({ path: `${shotDir}/cert-238-file-loading.png`, fullPage: true })
    releaseFile()
    await expect(fileDrawer.getByTestId('corp-cert-file-error')).toContainText('1034')
    await expect(fileDrawer.getByTestId('corp-cert-file-level')).toContainText('无原图查看权限，仅索引可见')
    await page.screenshot({ path: `${shotDir}/cert-238-file-level.png`, fullPage: true })
    await fileDrawer.getByRole('button', { name: '关闭' }).click()
    await page.unroute('**/cert/archive/**/file-url**')
    await page.route('**/cert/archive/**/file-url**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, msg: 'ok', data: { expiresInSeconds: 60 } }),
      })
    })
    await fileRow.getByTestId('corp-cert-file-btn').click()
    await expect(fileDrawer.getByTestId('corp-cert-file-empty')).toContainText('没有可预览的原图链接')
    await page.screenshot({ path: `${shotDir}/cert-238-file-empty.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
