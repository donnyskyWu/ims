import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, fillLiveRegisterDrawer, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-168-screenshots'
const DISABLED_PERSON = 'E2E-Live-1043'

fs.mkdirSync(shotDir, { recursive: true })

async function yellowIds(page: Page) {
  const fin = await resolveLiveFinRegisterIdsViaUi(page)
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  const optionsResp = page.waitForResponse(
    (r) => r.url().includes('/live/register/options') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '新建场次登记' }).click()
  await optionsResp
  const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
  await expect(drawer).toBeVisible()
  const option = drawer.getByTestId('live-reg-person').locator('option', { hasText: DISABLED_PERSON })
  await expect(option).toHaveCount(1)
  const value = await option.getAttribute('value')
  expect(value).toBeTruthy()
  return { drawer, ids: { ...fin, realnamePersonId: Number(value) } }
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
  await fillLiveRegisterDrawer(drawer, ids, topic)
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

  test('yellow reject stays local and the same session turns green after the word is removed', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const { drawer, ids } = await yellowIds(page)
    await fillLiveRegisterDrawer(drawer, ids, `E2E 黄级整改违禁 ${Date.now()}`)
    const regResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const created = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(created.code).toBe(0)
    const sessionCode = created.data?.sessionCode || ''
    expect(sessionCode).toMatch(/^IMS\d{8}DYS\d{4}$/)
    const detail = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-status') })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await expect(detail.getByTestId('live-session-status')).toContainText('55')
    await expect(detail.getByTestId('live-session-status')).toContainText('YELLOW')
    await expect(detail.getByTestId('live-risk-conclusion')).toContainText('黄色待审批')
    await expect(detail.getByTestId('live-start-blocked')).toContainText('未放行不可开播')
    await expect(detail.getByTestId('live-yellow-notice')).toContainText('钉钉未外发', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/03-yellow-before-reject.png`, fullPage: true })

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(1044)

    await detail.getByTestId('live-approve-comment').fill('请去掉违禁词')
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-approve-reject').click()
    expect(((await (await rejectResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-approve-comment-text')).toContainText('请去掉违禁词')
    await expect(detail.getByTestId('live-session-status')).toContainText('PENDING_RISK_CHECK')
    await page.screenshot({ path: `${shotDir}/05-yellow-reject.png`, fullPage: true })

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心', { timeout: 15_000 })
    const msgRow = page.locator('tbody tr').filter({ hasText: `黄级整改 ${sessionCode}` })
    await expect(msgRow.first()).toBeVisible({ timeout: 15_000 })
    await expect(msgRow.first()).toContainText('钉钉未外发')
    await page.screenshot({ path: `${shotDir}/06-local-rectify-message.png`, fullPage: true })

    await page.goto('/ims/live/sessions')
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    await page.locator('tbody tr', { hasText: sessionCode }).first().getByRole('button', { name: '详情' }).click()
    const again = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-status') })
    await expect(again).toBeVisible({ timeout: 15_000 })
    await again.locator('.tab', { hasText: '风控登记' }).click()
    await again.getByTestId('live-edit-open').click()
    const edit = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-code-lock') })
    await expect(edit.getByTestId('live-session-code-lock')).toHaveValue(sessionCode)
    await edit.getByTestId('live-reg-topic').fill('整改后专场')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes(`/live/register/${sessionCode}`) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await edit.getByTestId('live-reregister-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    const next = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-status') })
    await expect(next).toBeVisible({ timeout: 15_000 })
    await expect(next).toContainText(sessionCode)
    await expect(next.getByTestId('live-session-status')).toContainText('30', { timeout: 15_000 })
    await expect(next.getByTestId('live-session-status')).toContainText('GREEN')
    await expect(next.getByTestId('live-risk-conclusion')).toContainText('可直接确认开播')
    await page.screenshot({ path: `${shotDir}/04-same-session-green.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
