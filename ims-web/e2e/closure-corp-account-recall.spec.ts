import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const RECALL_NO = 'AC-E2E-RECALL'
const PEER_USER = 'e2e_acct_peer'
const PEER_LABEL = '流转同事（e2e_acct_peer）'
const SHOTS = '/opt/cursor/artifacts/e2e-62-screenshots'

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

async function searchRecall(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(RECALL_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: RECALL_NO })
  await expect(row).toBeVisible()
  return row
}

test.describe('CORP account recall to FROZEN S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('E2E-S4-04 recall freezes account and blocks checkout and transfer with 1022 (#62)', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)
    await openDouyin(page)
    const poolRow = await searchRecall(page)
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

    const inUseRow = await searchRecall(page)
    await expect(inUseRow).toContainText('在用')
    await expect(inUseRow).toContainText('管理员')
    await page.screenshot({ path: `${SHOTS}/01-in-use-admin.png`, fullPage: true })

    await inUseRow.getByTestId('acct-recall-open').click()
    const recallDrawer = page.getByTestId('acct-recall-drawer')
    await expect(recallDrawer).toBeVisible()
    await expect(recallDrawer).toContainText('冻结态')
    await recallDrawer.getByTestId('acct-recall-reason').selectOption({ label: '业务调整' })
    await recallDrawer.getByTestId('acct-recall-remark').fill('E2E 账号收回冻结')
    const recallResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await recallDrawer.getByTestId('acct-recall-submit').click()
    const recallBody = (await (await recallResp).json()) as { code: number; data?: { transferNo?: string; status?: string } }
    expect(recallBody.code).toBe(0)
    expect(recallBody.data?.transferNo || '').toMatch(/^TR/)
    expect(recallBody.data?.status).toBe('EFFECTIVE')
    await expect(recallDrawer.getByTestId('acct-recall-status')).toContainText('已生效')
    await expect(recallDrawer.getByTestId('acct-recall-status')).toContainText('FROZEN')
    await expect(recallDrawer.getByTestId('acct-recall-status')).toContainText('TR')
    await page.screenshot({ path: `${SHOTS}/02-recall-effective.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    const frozenRow = await searchRecall(page)
    await expect(frozenRow).toContainText('冻结')
    await frozenRow.getByRole('button', { name: '领用' }).click()
    const checkoutDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号领用' })
    await expect(checkoutDrawer).toBeVisible()
    const checkoutBlocked = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST',
    )
    await checkoutDrawer.getByRole('button', { name: '提交申请' }).click()
    const checkoutBody = (await (await checkoutBlocked).json()) as { code: number }
    expect(checkoutBody.code).toBe(1022)
    await expect(checkoutDrawer.getByTestId('acct-checkout-msg')).toContainText('1022')
    await expect(checkoutDrawer.getByTestId('acct-checkout-msg')).toContainText('冻结')
    await page.screenshot({ path: `${SHOTS}/03-checkout-1022.png`, fullPage: true })
    await checkoutDrawer.getByRole('button', { name: '取消' }).click()

    const transferRow = await searchRecall(page)
    await transferRow.getByTestId('acct-transfer-open').click()
    const transferDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号流转' })
    await expect(transferDrawer).toBeVisible()
    await expect(transferDrawer.getByTestId('acct-transfer-to').locator('option', { hasText: PEER_USER })).toHaveCount(1)
    await transferDrawer.getByTestId('acct-transfer-to').selectOption({ label: PEER_LABEL })
    await transferDrawer.getByTestId('acct-transfer-reason').selectOption({ label: '业务调整' })
    await transferDrawer.getByTestId('acct-transfer-remark').fill('E2E 冻结后再流转')
    const transferBlocked = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await transferDrawer.getByTestId('acct-transfer-submit').click()
    const transferBody = (await (await transferBlocked).json()) as { code: number }
    expect(transferBody.code).toBe(1022)
    await expect(transferDrawer.getByTestId('acct-transfer-msg')).toContainText('1022')
    await expect(transferDrawer.getByTestId('acct-transfer-msg')).toContainText('冻结')
    await page.screenshot({ path: `${SHOTS}/04-transfer-1022.png`, fullPage: true })
    await transferDrawer.getByRole('button', { name: '关闭' }).click()

    const detailRow = await searchRecall(page)
    await expect(detailRow).toContainText('冻结')
    await detailRow.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    const timeline = page.locator('.timeline-list')
    await expect(timeline).toContainText('FREEZE')
    await expect(timeline).toContainText('FROZEN')
    await expect(timeline).toContainText('管理员')
    await page.screenshot({ path: `${SHOTS}/05-timeline-freeze.png`, fullPage: true })
  })
})
