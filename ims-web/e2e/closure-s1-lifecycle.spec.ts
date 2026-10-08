import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { execFileSync } from 'child_process'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-73-screenshots'
const NICK = 'E2E主播小周'
const ACCOUNT = 'AC-E2E-S1'
const USER = 'e2e_s1_anchor'
const PASS = 'Admin@123'

function ymd(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

function certNo() {
  return `110101${String(Date.now()).slice(-10)}01`.padEnd(18, '0').slice(0, 18)
}

/** 外部系统事件模拟。随后断言与领用/归还/换证只走页面。 */
function deliver(phase: string) {
  const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../ims-backend')
  const env = { ...process.env }
  delete env.IMS_USE_CLOUD_DB
  env.IMS_MYSQL_HOST = '127.0.0.1'
  const bin = process.env.PYTHON || 'python3'
  const out = execFileSync(bin, ['-m', 'app.s1_lifecycle_seed', phase], {
    cwd: backend,
    env,
    encoding: 'utf8',
  })
  const line = out.trim().split('\n').filter(Boolean).pop() || '{}'
  return JSON.parse(line) as { phase?: string; username?: string; status?: string }
}

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

async function searchOrg(page: Page, keyword: string) {
  await page.goto('/ims/auth/org')
  await expect(page.locator('h1')).toHaveText('组织架构同步', { timeout: 15_000 })
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/auth/org/users') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('org-user-keyword').fill(keyword)
  await page.getByTestId('org-user-search').click()
  await listResp
  const row = page.getByTestId('org-user-row').filter({ hasText: keyword })
  await expect(row).toBeVisible({ timeout: 15_000 })
  return row
}

async function searchAccount(page: Page) {
  await page.goto('/ims/corp/account/douyin')
  await expect(page.locator('h1')).toContainText('抖音', { timeout: 15_000 })
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('input[placeholder="账号编号/昵称"]').fill(ACCOUNT)
  await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
  await listResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: ACCOUNT })
  await expect(row).toBeVisible({ timeout: 15_000 })
  return row
}

async function searchHolder(page: Page, holder: string) {
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/corp/resource/certificate/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('input[placeholder="持有人"]').fill(holder)
  await page.locator('form.qbar').first().getByRole('button', { name: '查询' }).click()
  await listResp
}

/** Checklist **E2E-S1-01/03/04** 与 **S1-05～09/11** 现有能力子集（#73 · 事件在浏览器外模拟 · 之后纯 UI） */
test.describe('S1 simulated employee lifecycle closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('hire transfer and resign stay visible through existing checkout return and renew', async ({ page }) => {
    test.setTimeout(240_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })

    const hired = deliver('hire')
    expect(hired.username).toBe(USER)
    expect(hired.status).toBe('ENABLED')

    await loginAdmin(page)
    const hiredRow = await searchOrg(page, NICK)
    await expect(hiredRow.getByTestId('org-user-position')).toHaveText('主播运营')
    await expect(hiredRow.getByTestId('org-user-dept')).toContainText('内容部')
    await expect(hiredRow.getByTestId('org-user-roles')).toContainText('主播运营')
    await expect(hiredRow.getByTestId('org-user-status')).toHaveText('在职')
    await hiredRow.getByTestId('org-user-open').click()
    const drawer = page.getByTestId('org-user-drawer')
    await expect(drawer.getByTestId('org-detail-position')).toHaveText('主播运营')
    await expect(drawer.getByTestId('org-diff-summary')).toContainText('入职按岗位供给角色')
    await page.screenshot({ path: `${shotDir}/01-hire-visible.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    await logout(page)
    await loginAs(page, USER, PASS)
    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(NICK, { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/01b-workbench.png`, fullPage: true })

    const poolRow = await searchAccount(page)
    await expect(poolRow).toContainText('池可领用')
    await poolRow.getByRole('button', { name: '领用' }).click()
    await expect(page.locator('.drawer.on').getByText('发起账号领用')).toBeVisible()
    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交申请' }).click()
    await applyResp
    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '审批通过' }).click()
    await approveResp
    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/confirm') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '确认领用生效' }).click()
    await confirmResp
    await expect(poolRow).toContainText('在用')
    await expect(poolRow).toContainText(NICK)

    await logout(page)
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    const code = `AS-S1-${Date.now()}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`S1显示器-${code}`)
    await expect(create.getByTestId('corp-asset-bind-account')).toHaveValue('')
    await expect(create.getByTestId('corp-asset-bind-session')).toHaveValue('')
    const saveResp = page.waitForResponse(
      (r) =>
        r.url().includes('/asset/ledger') &&
        r.request().method() === 'POST' &&
        !r.url().includes('/checkout') &&
        r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    const assetRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(assetRow).toBeVisible()
    await assetRow.getByTestId('corp-asset-checkout-btn').click()
    const checkout = page.locator('.drawer.on').filter({ hasText: '领用' })
    await expect(checkout.getByTestId('corp-asset-owner').locator('option', { hasText: NICK })).toBeAttached({
      timeout: 15_000,
    })
    await checkout.getByTestId('corp-asset-owner').selectOption({ label: NICK })
    await checkout.getByTestId('corp-asset-purpose').fill('主播办公')
    const checkoutResp = page.waitForResponse(
      (r) => r.url().includes('/checkout') && r.request().method() === 'POST' && r.status() === 200,
    )
    await checkout.getByTestId('corp-asset-checkout-save').click()
    expect(((await (await checkoutResp).json()) as { code: number }).code).toBe(0)
    await expect(assetRow).toContainText(NICK)
    await expect(assetRow.getByTestId('corp-asset-status')).toHaveText('在用')
    await assetRow.getByTestId('corp-asset-use-btn').click()
    const useDrawer = page.locator('.drawer.on').filter({ hasText: '使用' })
    await useDrawer.getByTestId('corp-asset-use-remark').fill('在岗使用')
    const useResp = page.waitForResponse(
      (r) => r.url().includes('/use') && r.request().method() === 'POST' && r.status() === 200,
    )
    await useDrawer.getByTestId('corp-asset-use-save').click()
    expect(((await (await useResp).json()) as { code: number }).code).toBe(0)

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
    await page.getByTestId('corp-cert-create-btn').click()
    const certDrawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await certDrawer.getByTestId('corp-cert-holder').fill(NICK)
    await certDrawer.getByTestId('corp-cert-no').fill(certNo())
    await certDrawer.getByTestId('corp-cert-issue').fill('2020-01-01')
    await certDrawer.getByTestId('corp-cert-expire-date').fill(ymd(0))
    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await certDrawer.getByTestId('corp-cert-save').click()
    expect(((await (await uploadResp).json()) as { code: number }).code).toBe(0)
    await searchHolder(page, NICK)
    const certRow = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: NICK }).first()
    await expect(certRow).toContainText('待审')
    await certRow.getByTestId('corp-cert-review-btn').click()
    const review = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await review.getByTestId('corp-cert-review-approve').click()
    expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
    await page.screenshot({ path: `${shotDir}/02-onjob-issued.png`, fullPage: true })

    deliver('transfer')
    const moved = await searchOrg(page, NICK)
    await expect(moved.getByTestId('org-user-dept')).toContainText('直播部')
    await expect(moved.getByTestId('org-user-roles')).toContainText('主播运营')
    await expect(moved.getByTestId('org-user-roles')).toContainText('编导')
    await moved.getByTestId('org-user-open').click()
    const diff = page.getByTestId('org-user-diff')
    await expect(diff.getByTestId('org-diff-dept')).toContainText('内容部')
    await expect(diff.getByTestId('org-diff-dept')).toContainText('直播部')
    await expect(diff.getByTestId('org-diff-retained')).toContainText('主播运营')
    await expect(diff.getByTestId('org-diff-added')).toContainText('编导')
    await expect(page.getByTestId('org-detail-buffer')).not.toHaveText('—')
    await page.screenshot({ path: `${shotDir}/03-transfer-dept.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    const resigned = deliver('resign')
    expect(resigned.status).toBe('FROZEN')
    const frozenRow = await searchOrg(page, NICK)
    await expect(frozenRow.getByTestId('org-user-status')).toHaveText('冻结')
    await frozenRow.getByTestId('org-user-open').click()
    await expect(page.getByTestId('org-user-frozen')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-resign-frozen.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    await logout(page)
    await page.locator('input[autocomplete="username"]').fill(USER)
    await page.locator('input[type="password"]').fill(PASS)
    await page.locator('button[type="submit"]').click()
    await expect(page.locator('.login-err')).toContainText('用户名或密码错误')

    await loginAdmin(page)
    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    const todoTable = page.locator('.tbl-wrap table').nth(1)
    await expect(todoTable.locator('tbody tr', { hasText: `离职待归还：${NICK}` })).toBeVisible({ timeout: 15_000 })

    const inUse = await searchAccount(page)
    await expect(inUse).toContainText('在用')
    await inUse.getByRole('button', { name: '归还' }).click()
    await expect(page.locator('.drawer.on').getByText('账号归还')).toBeVisible()
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/account/return/submit') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '确认归还' }).click()
    await returnResp
    await expect(inUse).toContainText('已归还')

    await page.goto('/ims/corp/device/office')
    const usedAsset = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(usedAsset).toBeVisible()
    await usedAsset.getByTestId('corp-asset-return-btn').click()
    const returnDrawer = page.locator('.drawer.on').filter({ hasText: '归还' })
    const assetReturnResp = page.waitForResponse(
      (r) => r.url().includes('/return') && r.request().method() === 'POST' && r.status() === 200,
    )
    await returnDrawer.getByTestId('corp-asset-return-save').click()
    expect(((await (await assetReturnResp).json()) as { code: number }).code).toBe(0)
    await expect(usedAsset.getByTestId('corp-asset-status')).toHaveText('已归还')

    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toHaveText('证件管理', { timeout: 15_000 })
    await page.getByTestId('corp-cert-scan-btn').click()
    const scanDrawer = page.locator('.drawer.on').filter({ hasText: '扫描到期' })
    const scanResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/scan') && r.request().method() === 'POST' && r.status() === 200,
    )
    await scanDrawer.getByTestId('corp-cert-scan-confirm').click()
    expect(((await (await scanResp).json()) as { code: number }).code).toBe(0)
    const expireTable = page.getByTestId('corp-cert-expire-table')
    const alertRow = expireTable.locator('tbody tr', { hasText: NICK }).first()
    await expect(alertRow).toBeVisible({ timeout: 15_000 })
    await alertRow.getByTestId('corp-cert-renew-btn').click()
    const renew = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-save') })
    const newExpire = ymd(400)
    await renew.getByTestId('corp-cert-renew-no').fill(certNo())
    await renew.getByTestId('corp-cert-renew-issue').fill('2024-01-01')
    await renew.getByTestId('corp-cert-renew-expire').fill(newExpire)
    await renew.getByTestId('corp-cert-renew-remark').fill('离职换证回收')
    const renewUpload = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await renew.getByTestId('corp-cert-renew-save').click()
    expect(((await (await renewUpload).json()) as { code: number }).code).toBe(0)
    await searchHolder(page, NICK)
    const pending = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: '待审' }).first()
    await pending.getByTestId('corp-cert-review-btn').click()
    const renewReview = page.locator('.drawer.on').filter({ hasText: '审核证件' })
    const renewReviewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await renewReview.getByTestId('corp-cert-review-approve').click()
    expect(((await (await renewReviewResp).json()) as { code: number }).code).toBe(0)
    await expireTable.locator('tbody tr', { hasText: NICK }).first().getByTestId('corp-cert-renew-finish').click()
    const finish = page.locator('.drawer.on').filter({ has: page.getByTestId('corp-cert-renew-confirm') })
    const renewResp = page.waitForResponse(
      (r) => r.url().includes('/cert/expire/') && r.url().includes('/renew') && r.request().method() === 'PUT',
    )
    await finish.getByTestId('corp-cert-renew-confirm').click()
    expect(((await (await renewResp).json()) as { code: number }).code).toBe(0)
    await searchHolder(page, NICK)
    await expect(page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: '已回收' })).toBeVisible()

    const done = await searchOrg(page, NICK)
    await done.getByTestId('org-user-open').click()
    const holdings = page.getByTestId('org-user-holdings')
    await expect(holdings).toContainText('账号在用 0')
    await expect(holdings).toContainText('资产在用 0')
    await expect(holdings).toContainText(/证件已回收 [1-9]/)
    await page.screenshot({ path: `${shotDir}/05-returned.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
