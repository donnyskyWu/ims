import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-78-screenshots'

const YELLOW_ACCOUNT = 'AC-E2E-LIVE1044'
const YELLOW_PHONE = 'E2E-LIVE1044-PHONE'
const RED_ACCOUNT = 'AC-E2E-LIVE1043'
const RED_PHONE = 'E2E-LIVE1043-PHONE'

fs.mkdirSync(shotDir, { recursive: true })

async function resolveAccount(page: Page, accountNo: string, phoneCode: string) {
  await page.goto('/ims/corp/account/douyin')
  await page.locator('input[placeholder="账号编号/昵称"]').fill(accountNo)
  const accListResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await accListResp
  const accRow = page.locator('tbody tr', { hasText: accountNo }).first()
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
  await page.locator('input[placeholder="设备编号 / 型号"]').fill(phoneCode)
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
    (row) => row.phoneCode === phoneCode || row.deviceNumber === phoneCode,
  )
  expect(phoneHit?.id).toBeTruthy()
  return { accountId: accountId!, realnamePersonId: realnamePersonId!, deviceId: phoneHit!.id! }
}

async function openLiveRegister(page: Page, ids: { accountId: number; realnamePersonId: number; deviceId: number }, topic: string) {
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  await page.getByRole('button', { name: '新建场次登记' }).click()
  const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
  await expect(drawer).toBeVisible()
  await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
  await drawer.locator('label', { hasText: '实名人 id' }).locator('..').locator('input').fill(String(ids.realnamePersonId))
  await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
  await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(topic)
  const regResp = page.waitForResponse(
    (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const body = (await (await regResp).json()) as {
    code: number
    data?: { sessionCode?: string; riskLevel?: string; riskScore?: number; sessionStatus?: string }
  }
  expect(body.code).toBe(0)
  const detail = page.locator('.drawer').filter({ hasText: '场次' })
  await expect(detail).toBeVisible({ timeout: 15_000 })
  await detail.locator('.tab', { hasText: '风控登记' }).click()
  return { body, detail, sessionCode: body.data?.sessionCode || '' }
}

/** Checklist E2E-S2-03 / E2E-S2-04 评分红级 / E2E-S2-09（#78 · 纯 UI） */
test.describe('live risk pack closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('yellow risk requires approval before going live', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveAccount(page, YELLOW_ACCOUNT, YELLOW_PHONE)
    const { detail, sessionCode } = await openLiveRegister(page, ids, `E2E 黄级违禁 ${Date.now()}`)
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    await expect(detail.getByTestId('live-session-status')).toContainText('YELLOW')
    await expect(detail.getByTestId('live-session-status')).toContainText('45')
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
    await expect(detail.getByTestId('live-session-status')).toContainText('PENDING_RISK_CHECK')
    await page.screenshot({ path: `${shotDir}/01-yellow-1044.png`, fullPage: true })

    await detail.getByTestId('live-approve-comment').fill('同意黄级放行')
    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-approve-pass').click()
    expect(((await (await approveResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('APPROVED')
    await expect(detail.getByTestId('live-approver')).toContainText('管理员')

    const liveResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await liveResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('LIVE')
    await page.screenshot({ path: `${shotDir}/02-yellow-approved-live.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('red risk score blocks going live', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveAccount(page, RED_ACCOUNT, RED_PHONE)
    const { detail, sessionCode } = await openLiveRegister(page, ids, `E2E 红级违禁 ${Date.now()}`)
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    await expect(detail.getByTestId('live-session-status')).toContainText('RED')
    await expect(detail.getByTestId('live-session-status')).toContainText('75')
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('红色禁止开播')
    await expect(detail.getByTestId('live-approve-pass')).toHaveCount(0)

    const riskResp = page.waitForResponse(
      (r) => r.url().includes('/risk-check') && r.request().method() === 'POST' && r.status() === 200,
    )
    await detail.getByRole('button', { name: '执行风控' }).click()
    expect(((await (await riskResp).json()) as { code: number }).code).toBe(1043)
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1043)
    await expect(detail.getByTestId('live-action-error')).toContainText('1043')
    await expect(detail.getByTestId('live-session-status')).toContainText('PENDING_RISK_CHECK')
    await page.screenshot({ path: `${shotDir}/03-red-1043.png`, fullPage: true })
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

    await drawer.getByTestId('live-supplement-account').fill(String(ids.accountId))
    await drawer.getByTestId('live-supplement-person').fill(String(ids.realnamePersonId))
    await drawer.getByTestId('live-supplement-device').fill(String(ids.deviceId))
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
    await expect(detail.getByTestId('live-session-status')).toContainText('ENDED')
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
    await expect(row).toContainText('ENDED')
    await page.screenshot({ path: `${shotDir}/05-supplement-approved.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
