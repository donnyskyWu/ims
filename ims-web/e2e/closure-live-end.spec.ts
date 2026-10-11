import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, fillLiveRegisterDrawer, loginAdmin, resolveLiveFinRegisterIdsViaUi } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-live-end-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

/** BUG-036 · 直播中才出现确认下播，确认后状态变为已下播。R5 按钮由 endAllowed 控制，接口在 pytest 覆盖。 */
test.describe('live confirm end', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('end button appears only while live and confirmation records the end', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    await page.goto('/ims/live/sessions')
    await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建场次登记' }).click()
    const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
    await fillLiveRegisterDrawer(drawer, ids, `E2E 确认下播 ${Date.now()}`)
    const regResp = page.waitForResponse(
      (r) => r.url().includes('/live/register') && !r.url().includes('/risk-check') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交登记' }).click()
    const created = (await (await regResp).json()) as { code: number; data?: { sessionCode?: string } }
    expect(created.code).toBe(0)
    const sessionCode = created.data?.sessionCode || ''
    const detail = page.locator('.drawer.on').filter({ has: page.getByTestId('live-session-status') })
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await expect(detail.getByTestId('live-end-btn')).toHaveCount(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('APPROVED')

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/start') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await detail.getByTestId('live-start-btn').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(0)
    await expect(detail.getByTestId('live-session-status')).toContainText('LIVE')
    await expect(detail.getByTestId('live-end-btn')).toBeVisible()
    await detail.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(detail.getByTestId('live-report-locked')).toContainText('场次未下播，下播录入在状态为已下播后开放')
    await expect(detail.getByTestId('live-report-submit')).toHaveCount(0)
    await expect(detail.getByTestId('live-report-gmv')).toHaveJSProperty('readOnly', true)
    await detail.locator('.tab', { hasText: '风控登记' }).click()
    await detail.getByTestId('live-end-btn').click()
    await expect(page.getByTestId('live-end-copy')).toHaveText('确认下播后开始 24 小时数据录入计时，确定下播？')
    await page.getByTestId('live-end-dismiss').click()
    await expect(detail.getByTestId('live-session-status')).toContainText('LIVE')
    await page.screenshot({ path: `${shotDir}/01-live-before-end.png`, fullPage: true })

    await detail.locator('.dr-x').click()
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/live/sessions/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(row.getByTestId('live-row-end')).toBeVisible()
    await row.getByTestId('live-row-end').click()
    await expect(page.getByTestId('live-end-copy')).toHaveText('确认下播后开始 24 小时数据录入计时，确定下播？')
    const endResp = page.waitForResponse(
      (r) => r.url().includes('/end') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByTestId('live-end-confirm').click()
    expect(((await (await endResp).json()) as { code: number }).code).toBe(0)
    await expect(row).toContainText('ENDED')
    await expect(row.getByTestId('live-row-end')).toHaveCount(0)

    await row.getByRole('button', { name: '详情' }).click()
    const after = page.locator('.drawer.on').filter({ hasText: '场次' })
    await expect(after).toBeVisible({ timeout: 15_000 })
    await expect(after.getByTestId('live-end-btn')).toHaveCount(0)
    await after.locator('.tab', { hasText: '基本信息' }).click()
    await expect(after.locator('tr', { hasText: '实际下播' })).not.toContainText('—')
    await after.locator('.tab', { hasText: '下播与 GMV' }).click()
    await expect(after.getByTestId('live-report-locked')).toHaveCount(0)
    await expect(after.getByTestId('live-report-submit')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-ended.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
