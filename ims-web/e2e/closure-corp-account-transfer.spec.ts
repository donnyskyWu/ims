import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin, loginAs } from './closure-helpers'

const XFER_NO = 'AC-E2E-XFER'
const PEER_USER = 'e2e_acct_peer'
const PEER_LABEL = '流转同事（e2e_acct_peer）'
const SHOTS = '/opt/cursor/artifacts/e2e-60-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  const transferReady = page.waitForResponse(
    (r) => r.url().includes('/account/transfer/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await transferReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchXfer(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(XFER_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: XFER_NO })
  await expect(row).toBeVisible()
  return row
}

test.describe('CORP account transfer and other-user checkout block S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('E2E-S4-02/03 other user 1021 then transfer holder and timeline (#60)', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)
    await openDouyin(page)
    const poolRow = await searchXfer(page)
    await expect(poolRow).toContainText('池可领用')

    await poolRow.getByRole('button', { name: '领用' }).click()
    await expect(page.locator('.drawer.on').getByText('发起账号领用')).toBeVisible()
    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交申请' }).click()
    const applyBody = (await (await applyResp).json()) as { code: number }
    expect(applyBody.code).toBe(0)

    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '审批通过' }).click()
    await approveResp

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
    )
    await page.getByRole('button', { name: '确认领用生效' }).click()
    const confirmBody = (await (await confirmResp).json()) as { code: number }
    expect(confirmBody.code).toBe(0)

    const inUseRow = await searchXfer(page)
    await expect(inUseRow).toContainText('在用')
    await expect(inUseRow).toContainText('管理员')
    await page.screenshot({ path: `${SHOTS}/01-in-use-admin.png`, fullPage: true })

    await loginAs(page, PEER_USER)
    await openDouyin(page)
    const peerRow = await searchXfer(page)
    await expect(peerRow).toContainText('在用')
    await peerRow.getByRole('button', { name: '领用' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '发起账号领用' })
    await expect(drawer).toBeVisible()
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST',
    )
    await drawer.getByRole('button', { name: '提交申请' }).click()
    const blockedBody = (await (await blockedResp).json()) as { code: number }
    expect(blockedBody.code).toBe(1021)
    await expect(drawer.getByTestId('acct-checkout-msg')).toContainText('1021')
    await expect(drawer.getByTestId('acct-checkout-msg')).toContainText('已被领用')
    await page.screenshot({ path: `${SHOTS}/02-peer-checkout-1021.png`, fullPage: true })

    await loginAdmin(page)
    await openDouyin(page)
    const holderRow = await searchXfer(page)
    await holderRow.getByTestId('acct-transfer-open').click()
    const transferDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号流转' })
    await expect(transferDrawer).toBeVisible()
    await expect(transferDrawer.getByTestId('acct-transfer-to').locator('option', { hasText: PEER_USER })).toHaveCount(1)
    await transferDrawer.getByTestId('acct-transfer-to').selectOption({ label: PEER_LABEL })
    await transferDrawer.getByTestId('acct-transfer-reason').selectOption({ label: '业务调整' })
    await transferDrawer.getByTestId('acct-transfer-remark').fill('E2E 账号流转交接')
    const transferResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await transferDrawer.getByTestId('acct-transfer-submit').click()
    const transferBody = (await (await transferResp).json()) as { code: number; data?: { transferNo?: string } }
    expect(transferBody.code).toBe(0)
    expect(transferBody.data?.transferNo || '').toMatch(/^TR/)
    await expect(transferDrawer.getByTestId('acct-transfer-status')).toContainText('待新责任人确认')
    await expect(transferDrawer.getByTestId('acct-transfer-status')).toContainText('TR')
    await page.screenshot({ path: `${SHOTS}/03-transfer-pending.png`, fullPage: true })

    await loginAs(page, PEER_USER)
    await openDouyin(page)
    const confirmRow = await searchXfer(page)
    await confirmRow.getByTestId('acct-transfer-confirm-open').click()
    const confirmDrawer = page.getByTestId('acct-transfer-confirm-drawer')
    await expect(confirmDrawer).toContainText('审批流')
    await expect(confirmDrawer).toContainText('管理员')
    await expect(confirmDrawer).toContainText('流转同事')
    const acceptResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
    )
    await page.getByTestId('acct-transfer-confirm').click()
    const acceptBody = (await (await acceptResp).json()) as { code: number }
    expect(acceptBody.code).toBe(0)

    const movedRow = await searchXfer(page)
    await expect(movedRow).toContainText('在用')
    await expect(movedRow).toContainText('流转同事')
    await page.screenshot({ path: `${SHOTS}/04-holder-changed.png`, fullPage: true })

    await movedRow.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    const timeline = page.locator('.timeline-list')
    await expect(timeline).toContainText('TRANSFER')
    await expect(timeline).toContainText('流转同事')
    await expect(timeline).toContainText('管理员')
    await page.screenshot({ path: `${SHOTS}/05-timeline-transfer.png`, fullPage: true })
  })
})
