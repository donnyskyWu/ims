import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  openDcSessionDetailViaUi,
  openDcTypedEntryTraceViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/dc-relation-drill-163'

/**
 * #163 · DC 六入口剩余下钻：结果区资产 / 责任人 / IP 组 chip 与抽屉再次穿透。
 * 订阅弹窗只核对 DAILY 与本地时刻，不触发外部定时任务。
 */
test.describe('dc relation drill closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('asset owner and ip group chips drill from the trace result', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    expect(ids.ipGroupId).toBeTruthy()
    const registered = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await openDcTypedEntryTraceViaUi(page, 'PERSON', registered.realnameName, registered.sessionCode, {
      entryId: String(ids.realnamePersonId),
    })
    const chips = page.getByTestId('dc-trace-relation-chips')
    await expect(chips).toBeVisible()
    await expect(chips.locator('[data-entry-type="ASSET"]')).toBeVisible()
    await expect(chips.locator('[data-entry-type="RESPONSIBLE"]')).toContainText(registered.responsibleUserName)
    await expect(chips.locator('[data-entry-type="IP_GROUP"]')).toContainText(ids.ipGroupName || '')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText('100,000.00')
    await page.screenshot({ path: `${SHOTS}/01-relation-chips.png`, fullPage: true })

    const ownerResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await chips.locator('[data-entry-type="RESPONSIBLE"]').click()
    expect((await (await ownerResp).json()).code).toBe(0)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('责任人')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/02-owner-drill.png`, fullPage: true })

    const assetResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('dc-trace-detail-asset').first().click()
    expect((await (await assetResp).json()).code).toBe(0)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('资产')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/03-asset-drill.png`, fullPage: true })

    const groupResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.locator('[data-testid="dc-trace-relation-chip"][data-entry-type="IP_GROUP"]').click()
    expect((await (await groupResp).json()).code).toBe(0)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('IP组')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/04-ip-group-drill.png`, fullPage: true })

    const { drawer } = await openDcSessionDetailViaUi(page, registered.sessionCode)
    await expect(drawer).toContainText(`责任人：${registered.responsibleUserName}`)
    await expect(drawer.getByTestId('dc-trace-drawer-asset')).toBeVisible()
    await expect(drawer.getByTestId('dc-trace-drawer-ip-group')).toContainText(ids.ipGroupName || '')
    await page.screenshot({ path: `${SHOTS}/05-drawer-drills.png`, fullPage: true })
    const drawerOwner = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('dc-trace-drawer-responsible').click()
    expect((await (await drawerOwner).json()).code).toBe(0)
    await expect(drawer).toBeHidden()
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('责任人')

    await page.getByTestId('dc-trace-entry-type').selectOption('ASSET')
    await page.getByTestId('dc-trace-keyword').fill('___no_such_asset___')
    const miss = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/entry') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('dc-trace-search-entry').click()
    expect(((await (await miss).json()) as { data?: unknown[] }).data).toEqual([])
    await expect(page.getByTestId('dc-trace-entry-empty')).toHaveText('未找到入口')
    await page.screenshot({ path: `${SHOTS}/06-asset-entry-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('daily subscribe form keeps a local push time', async ({ page }) => {
    test.setTimeout(60_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/bi/report/subscribe')
    await expect(page.locator('h1')).toContainText('订阅与分享')
    await expect(page.getByTestId('bi-sub-period-code').first()).toHaveText(/DAILY|WEEKLY|MONTHLY/)
    await page.getByRole('button', { name: '订阅推送' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '新建订阅' })
    await expect(modal.getByTestId('bi-sub-period')).toHaveValue('DAILY')
    await expect(modal.getByTestId('bi-sub-push-time')).toHaveValue('09:00')
    await expect(modal).toContainText('不触发外部定时任务')
    await page.screenshot({ path: `${SHOTS}/07-daily-subscribe.png`, fullPage: true })
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
