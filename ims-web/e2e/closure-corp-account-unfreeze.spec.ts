import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const UNFREEZE_NO = 'AC-E2E-UNFREEZE'
const SHOTS = '/opt/cursor/artifacts/e2e-66-screenshots'

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
  await page.locator('input[placeholder="账号编号/昵称"]').fill(UNFREEZE_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: UNFREEZE_NO })
  await expect(row).toBeVisible()
  return row
}

test.describe('CORP account unfreeze FROZEN to IN_POOL S4', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('E2E-S4 unfreeze returns a recalled account to the pool (#66)', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)
    await openDouyin(page)
    const poolRow = await searchAccount(page)
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

    const inUseRow = await searchAccount(page)
    await expect(inUseRow).toContainText('在用')
    await page.screenshot({ path: `${SHOTS}/01-in-use.png`, fullPage: true })

    await inUseRow.getByTestId('acct-recall-open').click()
    const recallDrawer = page.locator('.drawer.on').filter({ hasText: '收回至冻结' })
    await expect(recallDrawer).toBeVisible()
    await recallDrawer.getByTestId('acct-recall-reason').selectOption({ label: '业务调整' })
    await recallDrawer.getByTestId('acct-recall-remark').fill('E2E 解冻前收回')
    const recallResp = page.waitForResponse(
      (r) => r.url().includes('/account/transfer') && !r.url().includes('/list') && r.request().method() === 'POST',
    )
    await recallDrawer.getByTestId('acct-recall-submit').click()
    const recallBody = (await (await recallResp).json()) as { code: number }
    expect(recallBody.code).toBe(0)
    await recallDrawer.getByRole('button', { name: '关闭' }).click()

    const frozenRow = await searchAccount(page)
    await expect(frozenRow).toContainText('冻结')
    await frozenRow.getByRole('button', { name: '领用' }).click()
    const blockedDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号领用' })
    const blockedResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST',
    )
    await blockedDrawer.getByRole('button', { name: '提交申请' }).click()
    const blockedBody = (await (await blockedResp).json()) as { code: number }
    expect(blockedBody.code).toBe(1022)
    await expect(blockedDrawer.getByTestId('acct-checkout-msg')).toContainText('1022')
    await page.screenshot({ path: `${SHOTS}/02-frozen-checkout-1022.png`, fullPage: true })
    await blockedDrawer.getByRole('button', { name: '取消' }).click()

    const thawRow = await searchAccount(page)
    await thawRow.getByTestId('acct-unfreeze-open').click()
    const thawDrawer = page.locator('.drawer.on').filter({ hasText: '解冻回账号池' })
    await expect(thawDrawer).toBeVisible()
    await expect(thawDrawer).toContainText('IN_POOL')
    await thawDrawer.getByTestId('acct-unfreeze-remark').fill('E2E 管理员解冻回池')
    const thawResp = page.waitForResponse(
      (r) => r.url().includes('/unfreeze') && r.request().method() === 'POST',
    )
    await thawDrawer.getByTestId('acct-unfreeze-submit').click()
    const thawBody = (await (await thawResp).json()) as { code: number; data?: { status?: string } }
    expect(thawBody.code).toBe(0)
    expect(thawBody.data?.status).toBe('IN_POOL')
    await expect(thawDrawer.getByTestId('acct-unfreeze-status')).toContainText('IN_POOL')
    await expect(thawDrawer.getByTestId('acct-unfreeze-msg')).toContainText('已解冻')
    await page.screenshot({ path: `${SHOTS}/03-unfreeze-in-pool.png`, fullPage: true })
    await thawDrawer.getByRole('button', { name: '关闭' }).click()

    const poolAgain = await searchAccount(page)
    await expect(poolAgain).toContainText('池可领用')
    await expect(poolAgain).toContainText('—')
    await page.screenshot({ path: `${SHOTS}/04-row-back-in-pool.png`, fullPage: true })

    await poolAgain.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '领用时间线' }).click()
    const timeline = page.locator('.timeline-list')
    await expect(timeline).toContainText('UNFREEZE')
    await expect(timeline).toContainText('IN_POOL')
    await expect(timeline).toContainText('管理员')
    await page.screenshot({ path: `${SHOTS}/05-timeline-unfreeze.png`, fullPage: true })
    await page.locator('.drawer.on').getByRole('button', { name: '关闭' }).click()

    const reapplyRow = await searchAccount(page)
    await reapplyRow.getByRole('button', { name: '领用' }).click()
    const reapplyDrawer = page.locator('.drawer.on').filter({ hasText: '发起账号领用' })
    const reapplyResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST',
    )
    await reapplyDrawer.getByRole('button', { name: '提交申请' }).click()
    const reapplyBody = (await (await reapplyResp).json()) as { code: number }
    expect(reapplyBody.code).toBe(0)
    await expect(reapplyDrawer).not.toContainText('1022')
  })
})
