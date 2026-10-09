import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #217 · 账号列表 IP 组改为整表筛选；离职归还补离职人与生效日。
 * 不重做 #173 解锁、#185 时间线筛选、#204 状态色标。
 */
const SHOTS = '/opt/cursor/artifacts/acct-217'
const POOL_NO = 'AC-E2E-POOL'

async function createUser(page: Page, username: string, nickname: string) {
  await page.goto('/ims/system/user')
  await expect(page.locator('h1')).toHaveText('用户管理', { timeout: 15_000 })
  await page.getByRole('button', { name: '新建用户' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新建用户' })
  await drawer.locator('input').nth(0).fill(username)
  await drawer.locator('input').nth(1).fill(nickname)
  await drawer.locator('input').nth(2).fill(`139${String(Date.now()).slice(-8)}`)
  await drawer.locator('input[type="password"]').fill('Admin@123')
  const saved = page.waitForResponse(
    (r) => r.url().includes('/system/user') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存' }).click()
  const body = (await (await saved).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(drawer).toBeHidden()
}

async function createEmptyGroup(page: Page, groupName: string) {
  const treeReady = page.waitForResponse((r) => r.url().includes('/ip-group/tree') && r.status() === 200)
  await page.goto('/ims/ip-group')
  await expect(page.locator('h1')).toHaveText('IP 组运营', { timeout: 15_000 })
  await treeReady
  await page.getByRole('button', { name: '+ 新建大组' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新建大组' })
  await drawer.locator('input').first().fill(groupName)
  const created = page.waitForResponse(
    (r) => r.url().includes('/ip-group/create') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '确定' }).click()
  const body = (await (await created).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(page.locator('.ipg-node', { hasText: groupName })).toBeVisible()
}

test.describe('ACCT list filter leftovers #217', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('ip group name filters the whole ledger, including an empty group', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const stamp = String(Date.now()).slice(-6)
    const emptyGroup = `E2E空组217-${stamp}`
    await createEmptyGroup(page, emptyGroup)

    const opened = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/corp/account/douyin')
    const baseline = (await (await opened).json()) as { data?: { total?: number } }
    const baselineTotal = Number(baseline.data?.total || 0)
    await expect(page.locator('h1')).toContainText('抖音')

    await page.getByTestId('acct-filter-ip-group').fill('E2E')
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('acct-ip-group-msg')).toContainText('请输入完整 IP 组名称')
    await expect(page.getByTestId('acct-list-empty')).toContainText('请改成完整 IP 组名称')
    await page.screenshot({ path: `${SHOTS}/01-ip-group-partial.png`, fullPage: true })

    await page.getByTestId('acct-filter-ip-group').fill('ZZ-NO-IP-217')
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('acct-ip-group-msg')).toContainText('未找到该 IP 组')
    await expect(page.getByTestId('acct-list-empty')).toContainText('换一个 IP 组名称')

    await page.getByTestId('acct-filter-ip-group').fill(emptyGroup)
    const emptyResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/account/page') &&
        r.url().includes('ipGroupId=') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    const emptyBody = (await (await emptyResp).json()) as { data?: { total?: number; list?: unknown[] } }
    expect(emptyBody.data?.total).toBe(0)
    expect(emptyBody.data?.list || []).toEqual([])
    await expect(page.getByTestId('acct-list-empty')).toContainText('当前没有该 IP 组的账号')
    await expect(page.locator('.pg-total')).toHaveText('共 0 条')
    await page.screenshot({ path: `${SHOTS}/02-ip-group-empty.png`, fullPage: true })

    await page.getByTestId('acct-list-filters').getByRole('button', { name: '重置' }).click()
    await page.getByTestId('acct-filter-keyword').fill(POOL_NO)
    const poolResp = page.waitForResponse(
      (r) => r.url().includes('/corp/account/page') && r.url().includes('keyword=') && r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    await poolResp
    const poolRow = page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })
    await poolRow.getByRole('button', { name: '详情' }).click()
    const detail = page.locator('.drawer.on').filter({ hasText: '详情' })
    const groupText = await detail.locator('.fld', { hasText: 'IP 组' }).innerText()
    const poolGroup = groupText
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && line !== 'IP 组')
      .pop()
    expect(poolGroup).toBeTruthy()
    await detail.getByRole('button', { name: '关闭' }).click()
    await expect(detail).toBeHidden()

    await page.getByTestId('acct-filter-keyword').fill('')
    await page.getByTestId('acct-filter-ip-group').fill(poolGroup || '')
    const hitResp = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/account/page') &&
        r.url().includes('ipGroupId=') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    const hit = await hitResp
    const hitBody = (await hit.json()) as { data?: { total?: number; list?: { accountNo?: string }[] } }
    const hitTotal = Number(hitBody.data?.total || 0)
    expect(hitTotal).toBeGreaterThan(0)
    expect(hitTotal).toBeLessThan(baselineTotal)
    expect((hitBody.data?.list || []).length).toBeLessThanOrEqual(hitTotal)
    await expect(page.locator('.pg-total')).toHaveText(`共 ${hitTotal} 条`)

    await page.getByTestId('acct-filter-keyword').fill(POOL_NO)
    const narrowed = page.waitForResponse(
      (r) =>
        r.url().includes('/corp/account/page') &&
        r.url().includes('ipGroupId=') &&
        r.url().includes('keyword=') &&
        r.status() === 200,
    )
    await page.getByTestId('acct-list-filters').getByRole('button', { name: '查询' }).click()
    const narrowedBody = (await (await narrowed).json()) as { data?: { list?: { accountNo?: string }[] } }
    expect((narrowedBody.data?.list || []).some((row) => row.accountNo === POOL_NO)).toBeTruthy()
    await expect(page.locator('.tbl-wrap tbody tr').filter({ hasText: POOL_NO })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/03-ip-group-hit.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })

  test('return list filters by leaver and resign dates', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    const stamp = String(Date.now()).slice(-6)
    const nickname = `离职筛选${stamp}`
    await createUser(page, `resign217${stamp}`, nickname)

    await page.goto('/ims/account/return')
    await expect(page.locator('h1')).toHaveText('离职归还', { timeout: 15_000 })
    await page.getByTestId('return-generate-open').click()
    const generate = page.locator('.drawer.on').filter({ hasText: '手动补建归还单' })
    await generate.getByTestId('return-generate-user').selectOption({ label: nickname })
    await generate.getByTestId('return-generate-date').fill('2026-04-08')
    const generated = page.waitForResponse(
      (r) => r.url().includes('/account/return/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await generate.getByTestId('return-generate-save').click()
    const order = (await (await generated).json()) as { code: number; data?: { returnNo?: string } }
    expect(order.code).toBe(0)
    const returnNo = order.data?.returnNo || ''
    expect(returnNo).toMatch(/^RT/)
    await page.locator('.drawer.on .dr-x').click()

    await page.getByTestId('return-filter-user').selectOption({ label: nickname })
    const byUser = page.waitForResponse(
      (r) => r.url().includes('/account/return/list') && r.url().includes('userId=') && r.status() === 200,
    )
    await page.getByTestId('return-filter-search').click()
    await byUser
    await expect(page.getByTestId('return-order-no').filter({ hasText: returnNo })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/04-return-user.png`, fullPage: true })

    await page.getByTestId('return-filter-from').fill('2026-05-01')
    await page.getByTestId('return-filter-to').fill('2026-04-01')
    let leaked = false
    const watch = (request: { url: () => string; method: () => string }) => {
      if (request.method() === 'GET' && request.url().includes('/account/return/list')) leaked = true
    }
    page.on('request', watch)
    await page.getByTestId('return-filter-search').click()
    await expect(page.getByTestId('return-filter-msg')).toContainText('生效日结束早于开始')
    await expect(page.getByTestId('return-order-no').filter({ hasText: returnNo })).toBeVisible()
    expect(leaked).toBeFalsy()
    page.off('request', watch)
    await page.screenshot({ path: `${SHOTS}/05-return-range-order.png`, fullPage: true })

    await page.getByTestId('return-filter-from').fill('2026-05-01')
    await page.getByTestId('return-filter-to').fill('2026-05-31')
    const missed = page.waitForResponse(
      (r) =>
        r.url().includes('/account/return/list') &&
        r.url().includes('timeFrom=2026-05-01') &&
        r.url().includes('timeTo=2026-05-31') &&
        r.status() === 200,
    )
    await page.getByTestId('return-filter-search').click()
    const missedBody = (await (await missed).json()) as { data?: { total?: number } }
    expect(missedBody.data?.total).toBe(0)
    const empty = page.getByTestId('return-list-empty')
    await expect(empty).toContainText('没有符合筛选的离职归还单')
    await expect(empty).toContainText('换一个单号或状态')
    await expect(empty).toContainText('离职人')
    await page.screenshot({ path: `${SHOTS}/06-return-range-empty.png`, fullPage: true })

    await page.getByTestId('return-filter-from').fill('')
    await page.getByTestId('return-filter-to').fill('2026-05-31')
    await page.getByTestId('return-filter-search').click()
    await expect(page.getByTestId('return-filter-msg')).toContainText('请同时填写生效日起止')

    const resetResp = page.waitForResponse(
      (r) => r.url().includes('/account/return/list') && !r.url().includes('userId=') && r.status() === 200,
    )
    await page.getByTestId('return-filter-reset').click()
    await resetResp
    await expect(page.getByTestId('return-filter-msg')).toHaveCount(0)
    expect(pageErrors).toEqual([])
  })
})
