import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-168-screenshots'

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

async function openLiveRegister(
  page: Page,
  ids: { accountId: number; realnamePersonId: number; deviceId: number },
  topic: string,
) {
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
  const body = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
  expect(body.code).toBe(0)
  const detail = page.locator('.drawer.on').filter({ hasText: '场次' })
  await expect(detail).toBeVisible({ timeout: 15_000 })
  await detail.locator('.tab', { hasText: '风控登记' }).click()
  return { detail, sessionCode: body.data?.sessionCode || '' }
}

/** #168 · 开播取消 / 红级同场次整改 / 黄级本地待办 */
test.describe('live start yellow red edges', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('approved session can be cancelled before start', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { detail } = await openLiveRegister(page, ids, `E2E 取消开播 ${Date.now()}`)
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('可直接确认开播')
    await expect(detail.locator('[data-testid="live-risk-check"][data-result="PASS"]').first()).toBeVisible()

    await detail.getByTestId('live-cancel-open').click()
    await detail.getByTestId('live-cancel-confirm').click()
    await expect(detail.getByTestId('live-action-error')).toContainText('取消原因必填')
    await expect(detail.getByTestId('live-session-status')).toContainText('APPROVED')
    await page.screenshot({ path: `${shotDir}/01-cancel-reason-required.png`, fullPage: true })

    await detail.getByTestId('live-cancel-reason').fill('计划有变')
    const cancelResp = page.waitForResponse(
      (r) => r.url().includes('/cancel') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-cancel-confirm').click()
    expect(((await (await cancelResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('CANCELLED')
    await expect(detail.getByTestId('live-cancel-reason-text')).toContainText('计划有变')
    await expect(detail.getByTestId('live-start-blocked')).toContainText('已取消不可开播')

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1042)
    await expect(detail.getByTestId('live-action-error')).toContainText('1042')
    await page.screenshot({ path: `${shotDir}/02-cancelled-cannot-start.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('red risk reuses the same session and yellow notice stays local', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveAccount(page, RED_ACCOUNT, RED_PHONE)
    const { detail, sessionCode } = await openLiveRegister(page, ids, `E2E 红级整改违禁 ${Date.now()}`)
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('红色禁止开播')
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('请整改后重新登记')
    await expect(detail.getByTestId('live-start-blocked')).toContainText('未放行不可开播')
    await expect(detail.locator('[data-testid="live-risk-check"][data-result="FAIL"]').first()).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-red-reregister-prompt.png`, fullPage: true })

    await detail.getByTestId('live-reregister-open').click()
    const edit = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-code-lock') })
    await expect(edit).toBeVisible()
    await expect(edit.getByTestId('live-session-code-lock')).toHaveValue(sessionCode)
    await edit.locator('label', { hasText: '主题' }).locator('..').locator('input').fill('整改后专场')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes(`/live/register/${sessionCode}`) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await edit.getByTestId('live-reregister-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)

    const next = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-status') })
    await expect(next).toBeVisible({ timeout: 15_000 })
    await expect(next).toContainText(sessionCode)
    await expect(next.getByTestId('live-session-status')).toContainText('50', { timeout: 15_000 })
    await expect(next.getByTestId('live-session-status')).toContainText('YELLOW')
    await expect(next.getByTestId('live-risk-conclusion')).toContainText('黄色待审批')
    await expect(next.getByTestId('live-yellow-notice')).toContainText('钉钉未外发', { timeout: 15_000 })
    await expect(next.getByTestId('live-yellow-notice')).toContainText('短信未外发')
    await page.screenshot({ path: `${shotDir}/04-same-session-yellow.png`, fullPage: true })

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await next.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1044)

    await next.getByTestId('live-approve-comment').fill('请去掉违禁词')
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await next.getByTestId('live-approve-reject').click()
    expect(((await (await rejectResp).json()) as { code: number }).code).toBe(0)
    await expect(next.getByTestId('live-approve-comment-text')).toContainText('请去掉违禁词')
    await expect(next.getByTestId('live-session-status')).toContainText('PENDING_RISK_CHECK')
    await page.screenshot({ path: `${shotDir}/05-yellow-reject.png`, fullPage: true })

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心', { timeout: 15_000 })
    const msgRow = page.locator('tbody tr').filter({ hasText: `黄级整改 ${sessionCode}` })
    await expect(msgRow.first()).toBeVisible({ timeout: 15_000 })
    await expect(msgRow.first()).toContainText('钉钉未外发')
    await page.screenshot({ path: `${shotDir}/06-local-rectify-message.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
