import fs from 'fs'
import { test, expect, type Locator, type Page } from '@playwright/test'
import { attachClosurePageHooks, fillLiveRegisterDrawer, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-78-screenshots'

const FROZEN_ACCOUNTS = ['AC-E2E-LIVE1044', 'AC-E2E-LIVE1043']
const DISABLED_PERSON = 'E2E-Live-1043'

fs.mkdirSync(shotDir, { recursive: true })

async function openRegisterDrawer(page: Page) {
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  const optionsResp = page.waitForResponse(
    (r) => r.url().includes('/live/register/options') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '新建场次登记' }).click()
  await optionsResp
  const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
  await expect(drawer).toBeVisible()
  await expect(drawer.getByTestId('live-reg-account')).toContainText('AC-E2E-FIN')
  return drawer
}

async function disabledPersonId(drawer: Locator) {
  const option = drawer.getByTestId('live-reg-person').locator('option', { hasText: DISABLED_PERSON })
  await expect(option).toHaveCount(1, { timeout: 15_000 })
  const value = await option.getAttribute('value')
  expect(value).toBeTruthy()
  return Number(value)
}

/** Checklist E2E-S2-03 / E2E-S2-04 / E2E-S2-09（#78 · 纯 UI）。冻结账号不进下拉，黄级改走停用实名人。 */
test.describe('live risk pack closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('yellow risk requires approval before going live', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const fin = await resolveLiveFinRegisterIdsViaUi(page)
    const drawer = await openRegisterDrawer(page)
    const ids = { ...fin, realnamePersonId: await disabledPersonId(drawer) }
    await fillLiveRegisterDrawer(drawer, ids, `E2E 黄级违禁 ${Date.now()}`)
    const regResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const body = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(body.code).toBe(0)
    const sessionCode = body.data?.sessionCode || ''
    const detail = page.locator('.drawer').filter({ hasText: '场次' })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    await expect(detail.getByTestId('live-session-status')).toContainText('黄')
    await expect(detail.getByTestId('live-session-status')).toContainText('55')
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('黄色待审批')

    const riskResp = page.waitForResponse(
      (r) => r.url().includes('/risk-check') && r.request().method() === 'POST' && r.status() === 200,
    )
    await detail.getByRole('button', { name: '执行风控' }).click()
    expect(((await (await riskResp).json()) as { code: number }).code).toBe(1044)
    await expect(detail.getByTestId('live-action-error')).toContainText('1044')

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1044)
    await expect(detail.getByTestId('live-session-status')).toContainText('待风控')
    await page.screenshot({ path: `${shotDir}/01-yellow-1044.png`, fullPage: true })

    await detail.getByTestId('live-approve-comment').fill('同意黄级放行')
    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-approve-pass').click()
    expect(((await (await approveResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('已放行')
    await expect(detail.getByTestId('live-approver')).toContainText('管理员')

    const liveResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await liveResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('直播中')
    await page.screenshot({ path: `${shotDir}/02-yellow-approved-live.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('empty register stays local and frozen accounts stay out of the dropdown', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const drawer = await openRegisterDrawer(page)
    let posted = false
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/live/register') && !request.url().includes('/options')) {
        posted = true
      }
    })
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('live-reg-gap-account')).toContainText('必填项，请填写')
    await expect(drawer.getByTestId('live-reg-gap-topic')).toContainText('必填项，请填写')
    const accountText = await drawer.getByTestId('live-reg-account').innerText()
    for (const accountNo of FROZEN_ACCOUNTS) {
      expect(accountText).not.toContain(accountNo)
    }
    await drawer.getByTestId('live-reg-plan').fill('2020-01-15T20:00')
    await drawer.getByRole('button', { name: '提交登记' }).click()
    await expect(drawer.getByTestId('live-reg-gap-plan')).toContainText('计划开播须晚于当前时间')
    expect(posted).toBe(false)
    await page.screenshot({ path: `${shotDir}/03-register-required.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('supplement without reason is blocked and approval lands it', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)

    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.getByTestId('live-supplement-open').click()
    const drawer = page.locator('.drawer').filter({ hasText: '历史补录' })
    await expect(drawer).toBeVisible()
    const missingResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/supplement') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('live-supplement-submit').click()
    expect(((await (await missingResp).json()) as { code: number }).code).toBe(1049)
    await expect(drawer.getByTestId('live-supplement-error')).toContainText('1049')
    await page.screenshot({ path: `${shotDir}/04-supplement-1049.png`, fullPage: true })

    await expect(drawer.getByTestId('live-supplement-account').locator(`option[value="${ids.accountId}"]`)).toHaveCount(1)
    await drawer.getByTestId('live-supplement-account').selectOption(String(ids.accountId))
    await drawer.getByTestId('live-supplement-person').selectOption(String(ids.realnamePersonId))
    await drawer.getByTestId('live-supplement-device').selectOption(String(ids.deviceId))
    await drawer.getByTestId('live-supplement-topic').fill(`E2E 补录 ${Date.now()}`)
    await drawer.getByTestId('live-supplement-plan').fill('2020-01-15T20:00:00+08:00')
    await drawer.getByTestId('live-supplement-reason').fill('历史漏登，补台账')
    const createdResp = page.waitForResponse(
      (r) => r.url().includes('/live/ledger/supplement') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('live-supplement-submit').click()
    const created = (await (await createdResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(created.code).toBe(0)
    const sessionCode = created.data?.sessionCode || ''
    expect(sessionCode).toMatch(/^IMS20200115DYS\d{4}$/)

    const detail = page.locator('.drawer').filter({ hasText: '场次' })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1049)
    await expect(detail.getByTestId('live-action-error')).toContainText('1049')

    await detail.getByTestId('live-supplement-comment').fill('补录通过')
    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/ledger/supplement/') && r.url().includes('/approve') && r.request().method() === 'PUT',
    )
    await detail.getByTestId('live-supplement-pass').click()
    expect(((await (await approveResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('已下播')
    await expect(detail.getByTestId('live-supplement-reason-text')).toContainText('历史漏登，补台账')
    await detail.locator('.dr-x').click()
    await expect(page.locator('.drawer.on').filter({ hasText: '场次' })).toHaveCount(0)

    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.getByTestId('live-supplement-tag')).toHaveText('补录')
    await expect(row).toContainText('已下播')
    await page.screenshot({ path: `${shotDir}/05-supplement-approved.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
