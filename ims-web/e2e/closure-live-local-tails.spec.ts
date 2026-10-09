import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

/**
 * #197 · 纯 UI
 * 台账种子场次无风控清单、未绑定 Football 点同步见 1041；
 * 草稿零订单/零成本显示「—」；结束早于开始拦截 1001；场次与告警空筛。
 */
const shotDir = '/opt/cursor/artifacts/e2e-197-screenshots'
const LEDGER = 'IMS20261008DYS0082'

fs.mkdirSync(shotDir, { recursive: true })

async function openSession(page: Page, code: string) {
  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(code)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const row = page.locator('tbody tr', { hasText: code }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.getByRole('button', { name: '详情' }).click()
  const detail = page.locator('.drawer.on')
  await expect(detail).toBeVisible({ timeout: 15_000 })
  return detail
}

test.describe('live local risk report tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty risk checklist, unbound football sync, and session miss', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const detail = await openSession(page, LEDGER)
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await expect(detail.getByTestId('live-risk-empty')).toContainText('尚未执行风控')
    await expect(detail.getByTestId('live-risk-empty')).toContainText('证件')
    await page.screenshot({ path: `${shotDir}/01-risk-empty.png`, fullPage: true })

    await detail.locator('.tab', { hasText: '直播数据' }).click()
    await expect(detail.getByTestId('live-metrics-empty')).toContainText('未绑定 Football 房间')
    const syncResp = page.waitForResponse(
      (r) => r.url().includes('/football-sync') && r.request().method() === 'POST',
    )
    await detail.getByTestId('live-sync-btn').click()
    const syncBody = (await (await syncResp).json()) as { code: number; msg?: string }
    expect(syncBody.code).toBe(1041)
    await expect(detail.getByTestId('live-sync-error')).toContainText('1041')
    await page.screenshot({ path: `${shotDir}/02-metrics-unlinked.png`, fullPage: true })

    await page.goto('/ims/live/sessions')
    await page.locator('input[placeholder="场次 ID"]').fill('IMS19990101DYS0000')
    const missResp = page.waitForResponse(
      (r) =>
        r.url().includes('/live/sessions/list') &&
        r.url().includes('sessionCode=IMS19990101DYS0000') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const missBody = (await (await missResp).json()) as { code: number; data?: { list?: unknown[] } }
    expect(missBody.code).toBe(0)
    expect(missBody.data?.list || []).toEqual([])
    await expect(page.getByTestId('live-sessions-empty')).toContainText('暂无场次')
    await page.screenshot({ path: `${shotDir}/03-sessions-empty.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('draft keeps zero denominators blank and blocks reversed times', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const topic = `E2E 草稿边界 ${Date.now()}`
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
    const regBody = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(regBody.code).toBe(0)
    const detail = page.locator('.drawer.on')
    await expect(detail).toBeVisible({ timeout: 15_000 })
    const openReport = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await openReport
    await expect(detail.getByTestId('live-report-draft')).toBeVisible()
    await expect(detail.getByTestId('live-report-duration')).toContainText('120 分钟')
    await detail.getByTestId('live-report-orders').fill('0')
    await detail.getByTestId('live-report-ad').fill('0')
    await detail.getByTestId('live-report-gmv').fill('80')
    const draftResp = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && !r.url().includes('/correction') && r.request().method() === 'PUT',
    )
    const draftLoaded = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await detail.getByTestId('live-report-draft').click()
    expect(((await (await draftResp).json()) as { code: number }).code).toBe(0)
    const loaded = (await (await draftLoaded).json()) as { code: number; data?: { entryStatus?: string; roas?: number | null } }
    expect(loaded.code).toBe(0)
    expect(loaded.data?.entryStatus).toBe('DRAFT')
    expect(loaded.data?.roas ?? null).toBeNull()
    await expect(detail.getByTestId('live-report-headline')).toContainText('DRAFT')
    await expect(detail.getByTestId('live-report-aov')).toHaveText('—')
    await expect(detail.getByTestId('live-report-roas')).toHaveText('—')
    await expect(detail.getByTestId('live-cost-empty')).toContainText('暂无成本明细')
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await expect(detail.getByTestId('live-session-status')).toContainText('APPROVED')
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await page.screenshot({ path: `${shotDir}/04-draft-zero.png`, fullPage: true })

    await detail.getByTestId('live-report-end').fill('2026-10-06T19:00:00+08:00')
    await expect(detail.getByTestId('live-report-duration')).toContainText('结束须晚于开始')
    const blockedResp = page.waitForResponse(
      (r) => /\/live\/report\/IMS/.test(r.url()) && r.request().method() === 'PUT',
    )
    await detail.getByTestId('live-report-draft').click()
    const blocked = (await (await blockedResp).json()) as { code: number }
    expect(blocked.code).toBe(1001)
    await expect(detail.getByTestId('live-report-error')).toContainText('1001')
    await expect(detail.getByTestId('live-report-headline')).toContainText('DRAFT')
    await page.screenshot({ path: `${shotDir}/05-draft-time.png`, fullPage: true })

    await page.goto('/ims/live/alarm')
    await expect(page.locator('h1')).toHaveText('直播风险告警', { timeout: 15_000 })
    await page.getByTestId('live-alarm-tab-records').click()
    await page.getByTestId('live-alarm-session').fill('IMS19990101DYS0000')
    const alarmResp = page.waitForResponse(
      (r) => r.url().includes('/live/alarm/records') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('live-alarm-query').click()
    const alarmBody = (await (await alarmResp).json()) as { code: number; data?: { list?: unknown[] } }
    expect(alarmBody.code).toBe(0)
    expect(alarmBody.data?.list || []).toEqual([])
    await expect(page.getByTestId('live-alarm-empty')).toContainText('该场次暂无风险告警')
    await page.screenshot({ path: `${shotDir}/06-alarm-empty.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
