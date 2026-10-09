import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const ACCOUNT_NO = 'AC-E2E-ASSETX'
const PEER_USER = 'e2e_acct_peer'
const PEER_LABEL = '流转同事（e2e_acct_peer）'
const SHOTS = '/opt/cursor/artifacts/e2e-123-screenshots'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await expect(page.locator('h1')).toContainText('抖音')
}

async function searchAccount(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(ACCOUNT_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: ACCOUNT_NO })
  await expect(row).toBeVisible()
  return row
}

async function checkoutToInUse(page: Page) {
  const poolRow = await searchAccount(page)
  await expect(poolRow).toContainText('池可领用')
  await poolRow.getByRole('button', { name: '领用' }).click()
  await expect(page.locator('.drawer.on').getByText('发起账号领用')).toBeVisible()
  const applyResp = page.waitForResponse(
    (r) => r.url().includes('/account/apply') && r.request().method() === 'POST' && r.status() === 200,
  )
  await page.getByRole('button', { name: '提交申请' }).click()
  expect(((await (await applyResp).json()) as { code: number }).code).toBe(0)
  const approveResp = page.waitForResponse(
    (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
  )
  await page.getByRole('button', { name: '审批通过' }).click()
  await approveResp
  const confirmResp = page.waitForResponse(
    (r) => r.url().includes('/account/apply/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: '确认领用生效' }).click()
  expect(((await (await confirmResp).json()) as { code: number }).code).toBe(0)
  const inUseRow = await searchAccount(page)
  await expect(inUseRow).toContainText('在用')
  return inUseRow
}

/** #123 · 纯 UI · 账号流转时绑定办公设备则提示同步资产转移 */
test.describe('CORP account asset transfer hint', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('bound office asset prompts sync transfer on account handoff', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(SHOTS, { recursive: true })
    const assetCode = `AS-XFER-${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-asset-code').fill(assetCode)
    await create.getByTestId('corp-asset-name').fill(`流转提示显示器 ${assetCode}`)
    await create.getByTestId('corp-asset-bind-account').fill(ACCOUNT_NO)
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    await expect(create).toBeHidden()

    await openDouyin(page)
    const holderRow = await checkoutToInUse(page)
    await holderRow.getByTestId('acct-transfer-open').click()
    const transferDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号流转' })
    await expect(transferDrawer).toBeVisible()
    await transferDrawer.getByTestId('acct-transfer-to').selectOption({ label: PEER_LABEL })
    await transferDrawer.getByTestId('acct-transfer-reason').selectOption({ label: '业务调整' })
    await transferDrawer.getByTestId('acct-transfer-remark').fill('E2E 资产同步转移')
    const transferResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await transferDrawer.getByTestId('acct-transfer-submit').click()
    const transferBody = (await (await transferResp).json()) as {
      code: number
      data?: { assetTransferHint?: string; boundAssets?: { assetCode: string }[] }
    }
    expect(transferBody.code).toBe(0)
    expect(transferBody.data?.assetTransferHint).toContain('是否同步发起资产转移')
    expect(transferBody.data?.boundAssets?.[0]?.assetCode).toBe(assetCode)

    const hint = page.getByTestId('acct-asset-transfer-hint')
    await expect(hint).toBeVisible()
    await expect(hint.getByTestId('acct-asset-transfer-text')).toContainText('该账号绑定了 1 项资产')
    await expect(hint.getByTestId('acct-asset-transfer-item')).toContainText(assetCode)
    await page.screenshot({ path: `${SHOTS}/01-asset-transfer-hint.png`, fullPage: true })
    await hint.getByTestId('acct-asset-transfer-skip').click()
    await expect(hint).toBeHidden()
    await expect(transferDrawer.getByTestId('acct-transfer-status')).toContainText('待新责任人确认')
    await page.screenshot({ path: `${SHOTS}/02-transfer-still-pending.png`, fullPage: true })

    await loginAs(page, PEER_USER)
    const messagesReady = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/messages') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/workbench/messages')
    await messagesReady
    await expect(page.locator('h1')).toHaveText('消息中心')
    await expect(page.locator('tbody')).toContainText(`资产同步转移：${ACCOUNT_NO}`)
    await page.screenshot({ path: `${SHOTS}/03-workbench-message.png`, fullPage: true })

    await openDouyin(page)
    const confirmRow = await searchAccount(page)
    await confirmRow.getByTestId('acct-transfer-confirm-open').click()
    const confirmDrawer = page.getByTestId('acct-transfer-confirm-drawer')
    await expect(confirmDrawer).toContainText('流转同事')
    const acceptResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
    )
    await page.getByTestId('acct-transfer-confirm').click()
    const acceptBody = (await (await acceptResp).json()) as { code: number; data?: { assetTransferHint?: string } }
    expect(acceptBody.code).toBe(0)
    expect(acceptBody.data?.assetTransferHint).toContain('是否同步发起资产转移')
    const again = page.getByTestId('acct-asset-transfer-hint')
    await expect(again).toBeVisible()
    await expect(again.getByTestId('acct-asset-transfer-text')).toContainText('1 项资产')
    await page.screenshot({ path: `${SHOTS}/04-confirm-hint.png`, fullPage: true })
    await again.getByTestId('acct-asset-transfer-jump').click()
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    await page.screenshot({ path: `${SHOTS}/05-jump-office-assets.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
