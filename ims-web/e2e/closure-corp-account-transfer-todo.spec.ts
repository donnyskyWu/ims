import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin, loginAs } from './closure-helpers'

const XTODO_NO = 'AC-E2E-XTODO'
const PEER_USER = 'e2e_acct_peer'
const PEER_LABEL = '流转同事（e2e_acct_peer）'
const SHOTS = '/opt/cursor/artifacts/e2e-122-screenshots'

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

async function searchAccount(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(XTODO_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: XTODO_NO })
  await expect(row).toBeVisible()
  return row
}

async function checkoutInUse(page: Page) {
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
  await expect(inUseRow).toContainText('管理员')
}

test.describe('CORP account transfer workbench and flow todo', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('transfer todo shows on workbench and flow list, recipient confirms from it (#122)', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)
    await openDouyin(page)
    await checkoutInUse(page)

    const holderRow = await searchAccount(page)
    await holderRow.getByTestId('acct-transfer-open').click()
    const transferDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号流转' })
    await expect(transferDrawer).toBeVisible()
    await transferDrawer.getByTestId('acct-transfer-to').selectOption({ label: PEER_LABEL })
    await transferDrawer.getByTestId('acct-transfer-reason').selectOption({ label: '业务调整' })
    await transferDrawer.getByTestId('acct-transfer-remark').fill('E2E 流转工作台待办')
    const transferResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await transferDrawer.getByTestId('acct-transfer-submit').click()
    const transferBody = (await (await transferResp).json()) as { code: number; data?: { transferNo?: string } }
    expect(transferBody.code).toBe(0)
    expect(transferBody.data?.transferNo || '').toMatch(/^TR/)
    await expect(transferDrawer.getByTestId('acct-transfer-status')).toContainText('待新责任人确认')
    await page.screenshot({ path: `${SHOTS}/01-transfer-pending.png`, fullPage: true })

    await loginAs(page, PEER_USER)
    const todoReady = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.request().method() === 'GET' && r.status() === 200,
    )
    const flowReady = page.waitForResponse(
      (r) => r.url().includes('/flow/task/my-todo') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/workbench')
    await todoReady
    await flowReady

    const todoRow = page.getByTestId('wb-acct-transfer-todo').filter({ hasText: XTODO_NO })
    await expect(todoRow).toBeVisible()
    await expect(todoRow).toContainText('账号流转待确认')
    await expect(todoRow.getByTestId('wb-acct-transfer-go')).toBeVisible()
    const flowRow = page.getByTestId('wb-acct-transfer-flow').filter({ hasText: XTODO_NO })
    await expect(flowRow).toBeVisible()
    await expect(flowRow).toContainText('账号流转确认')
    await expect(flowRow).toContainText('新责任人确认')
    await expect(flowRow.getByTestId('wb-acct-transfer-flow-go')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/02-workbench-transfer-todos.png`, fullPage: true })

    await todoRow.getByTestId('wb-acct-transfer-go').click()
    const confirmDrawer = page.getByTestId('acct-transfer-confirm-drawer')
    await expect(confirmDrawer).toBeVisible({ timeout: 20_000 })
    await expect(confirmDrawer).toContainText(XTODO_NO)
    await expect(confirmDrawer).toContainText('管理员')
    await expect(confirmDrawer).toContainText('流转同事')
    await page.screenshot({ path: `${SHOTS}/03-confirm-from-todo.png`, fullPage: true })

    const acceptResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
    )
    await page.getByTestId('acct-transfer-confirm').click()
    expect(((await (await acceptResp).json()) as { code: number }).code).toBe(0)

    const movedRow = await searchAccount(page)
    await expect(movedRow).toContainText('在用')
    await expect(movedRow).toContainText('流转同事')
    await page.screenshot({ path: `${SHOTS}/04-holder-changed.png`, fullPage: true })

    const clearedTodo = page.waitForResponse(
      (r) => r.url().includes('/auth/workbench/todos') && r.request().method() === 'GET' && r.status() === 200,
    )
    const clearedFlow = page.waitForResponse(
      (r) => r.url().includes('/flow/task/my-todo') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/workbench')
    await clearedTodo
    await clearedFlow
    await expect(page.getByTestId('wb-acct-transfer-todo').filter({ hasText: XTODO_NO })).toHaveCount(0)
    await expect(page.getByTestId('wb-acct-transfer-flow').filter({ hasText: XTODO_NO })).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/05-workbench-cleared.png`, fullPage: true })
  })
})
