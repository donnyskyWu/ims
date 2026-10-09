import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

/**
 * Checklist E2E-S2-06/07/08（#80 · 纯 UI）
 * 1046 缺字段拦截 → 补齐提交；1047 只读后走更正单；1048 超 24h 督办（种子场次 + 工作台 + 预警）
 */
const shotDir = '/opt/cursor/artifacts/e2e-80-screenshots'
const OVERDUE_SESSION = 'IMS20261006DYS1048'

fs.mkdirSync(shotDir, { recursive: true })

async function openReportTab(
  page: Page,
  ids: { accountId: number; realnamePersonId: number; deviceId: number },
) {
  const topic = `E2E 下播收尾 ${Date.now()}`
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
    (r) => r.url().includes('/live/register') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const regBody = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
  expect(regBody.code).toBe(0)
  const sessionCode = regBody.data?.sessionCode
  expect(sessionCode).toBeTruthy()

  const detail = page.locator('.drawer').filter({ hasText: '场次' })
  await expect(detail).toBeVisible({ timeout: 15_000 })
  const reportLoad = page.waitForResponse(
    (r) => r.url().includes('/live/report/') && r.request().method() === 'GET' && r.status() === 200,
    { timeout: 15_000 },
  )
  await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
  await reportLoad.catch(() => null)
  const gmv = detail.getByTestId('live-report-gmv')
  await expect(gmv).toBeVisible()
  await expect(gmv).toHaveValue('1000', { timeout: 5_000 })
  return { detail, sessionCode: sessionCode! }
}

test.describe('live report end ledger closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('missing fields 1046 then readonly 1047 and correction', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { detail } = await openReportTab(page, ids)

    await detail.getByTestId('live-report-gmv').fill('')
    const missingResp = page.waitForResponse(
      (r) =>
        /\/live\/report\/IMS/.test(r.url()) &&
        !r.url().includes('/correction') &&
        r.request().method() === 'POST',
    )
    await detail.getByTestId('live-report-submit').click()
    const missingBody = (await (await missingResp).json()) as { code: number; data?: { missing?: string[] } }
    expect(missingBody.code).toBe(1046)
    expect(missingBody.data?.missing).toContain('gmv')
    await expect(detail.getByTestId('live-report-error')).toContainText('1046')
    await page.screenshot({ path: `${shotDir}/01-missing-1046.png`, fullPage: true })

    await detail.getByTestId('live-report-gmv').fill('88000')
    const submitResp = page.waitForResponse(
      (r) =>
        /\/live\/report\/IMS/.test(r.url()) &&
        !r.url().includes('/correction') &&
        r.request().method() === 'POST',
    )
    await detail.getByTestId('live-report-submit').click()
    const submitBody = (await (await submitResp).json()) as { code: number; data?: { entryStatus?: string; gmv?: number } }
    expect(submitBody.code).toBe(0)
    expect(submitBody.data?.entryStatus).toBe('SUBMITTED')
    expect(submitBody.data?.gmv).toBe(88000)
    await expect(detail.getByTestId('live-report-confirm')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-report-submitted.png`, fullPage: true })

    const blockedResp = page.waitForResponse(
      (r) =>
        /\/live\/report\/IMS/.test(r.url()) &&
        !r.url().includes('/confirm') &&
        !r.url().includes('/correction') &&
        r.request().method() === 'PUT',
    )
    await detail.getByTestId('live-report-direct-save').click()
    const blockedBody = (await (await blockedResp).json()) as { code: number }
    expect(blockedBody.code).toBe(1047)
    await expect(detail.getByTestId('live-report-error')).toContainText('1047')
    await page.screenshot({ path: `${shotDir}/03-readonly-1047.png`, fullPage: true })

    await detail.getByTestId('live-report-correction-open').click()
    await expect(detail.getByTestId('live-report-correction-reason')).toBeVisible()
    await detail.getByTestId('live-report-gmv').fill('86000')
    await detail.getByTestId('live-report-correction-reason').fill('客单复核，调低 GMV')
    const corrResp = page.waitForResponse(
      (r) => r.url().includes('/correction') && r.request().method() === 'POST',
    )
    await detail.getByTestId('live-report-correction-submit').click()
    const corrBody = (await (await corrResp).json()) as {
      code: number
      data?: { correctionId?: number; before?: { gmv?: number }; after?: { gmv?: number } }
    }
    expect(corrBody.code).toBe(0)
    expect(corrBody.data?.correctionId).toBeTruthy()
    expect(corrBody.data?.before?.gmv).toBe(88000)
    expect(corrBody.data?.after?.gmv).toBe(86000)
    await expect(detail.getByTestId('live-correction-trace')).toContainText(String(corrBody.data?.correctionId))
    await expect(detail).toContainText('SUBMITTED')
    await page.screenshot({ path: `${shotDir}/04-correction-trace.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('overdue session shows 1048 on pending list, workbench and alarm', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })

    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/live/report/pending') && r.request().method() === 'GET',
    )
    await page.getByTestId('live-view-pending').click()
    const pendingBody = (await (await pendingResp).json()) as {
      code: number
      msg?: string
      data?: { list?: Array<{ sessionCode?: string; overdueHours?: number; overdue?: boolean }> }
    }
    expect(pendingBody.code).toBe(1048)
    const hit = pendingBody.data?.list?.find((row) => row.sessionCode === OVERDUE_SESSION)
    expect(hit?.overdue).toBe(true)
    expect(hit?.overdueHours).toBeGreaterThanOrEqual(24)
    await expect(page.getByTestId('live-overdue-hint')).toContainText('1048')
    const row = page.getByTestId('live-pending-row').filter({ hasText: OVERDUE_SESSION })
    await expect(row).toBeVisible()
    await expect(row.getByTestId('live-pending-overdue')).toHaveText('超 24h')
    await page.screenshot({ path: `${shotDir}/05-overdue-1048.png`, fullPage: true })

    await row.locator('td').first().click()
    const detail = page.locator('.drawer').filter({ hasText: OVERDUE_SESSION })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    const alarmResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET',
    )
    await detail.locator('.tab', { hasText: '关联' }).click()
    await alarmResp
    await expect(detail).toContainText('下播超时督办')
    await expect(detail).toContainText('1048')
    await page.screenshot({ path: `${shotDir}/06-overdue-alarm.png`, fullPage: true })

    await page.goto('/ims/workbench/todos')
    await expect(page.locator('h1')).toHaveText('待办中心', { timeout: 15_000 })
    const todoRow = page.locator('tbody tr').filter({ hasText: `下播超时督办 1048：${OVERDUE_SESSION}` })
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/07-workbench-todo.png`, fullPage: true })
    await todoRow.getByRole('button', { name: '完成' }).click()

    await page.goto('/ims/workbench/messages')
    await expect(page.locator('h1')).toHaveText('消息中心', { timeout: 15_000 })
    const msgRow = page.locator('tbody tr').filter({ hasText: `下播超时督办 1048：${OVERDUE_SESSION}` })
    await expect(msgRow).toBeVisible({ timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/08-workbench-message.png`, fullPage: true })
    const readBtn = msgRow.getByRole('button', { name: '标已读' })
    if (await readBtn.count()) {
      await readBtn.click()
    }
    expect(pageErrors).toEqual([])
  })
})
