import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/fin-166-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

type ApiBody = { code: number; msg?: string; data?: { id?: number; version?: number; scope?: { ipGroupIds?: number[] } } }

/**
 * #166 FIN 分成规则 IP 组范围 CRUD，以及利润反查聚合 / 异常 Tab 的日期与空结果。
 */
test.describe('fin share scope and aggregate tabs', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share rule keeps ip groups across edit and rejects illegal ids', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const accountId = stamp
    const ruleName = `E2E组范围${stamp}`
    const editedName = `E2E组范围修订${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/fin/share/rule')
    await expect(page.locator('h1')).toHaveText('分成规则', { timeout: 15_000 })

    await page.getByTestId('fin-share-rule-create').click()
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && !r.url().includes('/simulate') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const emptyBody = (await (await emptyResp).json()) as ApiBody
    expect(emptyBody.code).toBe(1001)
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('规则名称必填')

    await fillFixed(page, {
      name: ruleName,
      accountId,
      groups: '88001,88002',
      priority: Math.floor(stamp / 1000) % 100000,
    })
    const created = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && !r.url().includes('/simulate') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const createdBody = (await (await created).json()) as ApiBody
    expect(createdBody.code).toBe(0)
    expect(createdBody.data?.scope?.ipGroupIds).toEqual([88001, 88002])

    const row = page.locator('tbody tr', { hasText: ruleName })
    await expect(row.getByTestId('fin-share-rule-scope')).toContainText('IP组×2')
    await expect(row.getByTestId('fin-share-rule-scope')).toHaveAttribute('title', /88001/)
    await expect(row.getByTestId('fin-share-rule-scope')).toHaveAttribute('title', /88002/)
    await page.screenshot({ path: `${shotDir}/01-rule-ip-group.png`, fullPage: true })

    await page.getByTestId('fin-share-rule-filter-status').selectOption('DISABLED')
    await page.getByTestId('fin-share-rule-query').click()
    await expect(page.locator('tbody tr', { hasText: ruleName })).toHaveCount(0)
    await page.getByTestId('fin-share-rule-reset').click()
    await expect(page.locator('tbody tr', { hasText: ruleName })).toBeVisible()

    await row.getByRole('button', { name: '编辑' }).click()
    await expect(page.getByTestId('fin-share-rule-groups')).toHaveValue('88001,88002')
    await page.getByTestId('fin-share-rule-name').fill(editedName)
    const edited = page.waitForResponse(
      (r) => /\/fin\/share\/rule\/\d+/.test(r.url()) && r.request().method() === 'PUT',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const editedBody = (await (await edited).json()) as ApiBody
    expect(editedBody.code).toBe(0)
    expect(editedBody.data?.version).toBe(2)
    expect(editedBody.data?.scope?.ipGroupIds).toEqual([88001, 88002])
    const editedRow = page.locator('tbody tr', { hasText: editedName })
    await expect(editedRow.getByTestId('fin-share-rule-scope')).toContainText('IP组×2')
    await page.screenshot({ path: `${shotDir}/02-rule-ip-group-edited.png`, fullPage: true })

    await editedRow.getByTestId('fin-share-rule-simulate').click()
    await page.getByTestId('fin-share-rule-sim-base').fill('-1')
    const sim = page.waitForResponse((r) => r.url().includes('/fin/share/simulate') && r.request().method() === 'POST')
    await page.getByTestId('fin-share-rule-sim-submit').click()
    expect(((await (await sim).json()) as ApiBody).code).toBe(1001)
    await expect(page.getByTestId('fin-share-rule-sim-error')).toContainText('1001')
    await page.getByTestId('fin-share-rule-sim-drawer').getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('fin-share-rule-create').click()
    await page.getByTestId('fin-share-rule-rate-type').selectOption('LADDER')
    await expect(page.getByTestId('fin-share-rule-ladder-min')).toHaveCount(2)
    await page.getByTestId('fin-share-rule-ladder-remove').first().click()
    await expect(page.getByTestId('fin-share-rule-ladder-min')).toHaveCount(1)
    await page.getByTestId('fin-share-rule-groups').fill('0')
    await page.getByTestId('fin-share-rule-name').fill(`E2E非法组${stamp}`)
    await page.getByTestId('fin-share-rule-save').click()
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('1001')
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('适用范围编号非法')
    await expect(page.getByTestId('fin-share-rule-drawer')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-rule-bad-group.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })

  test('aggregate and abnormal tabs reject inverted dates and show an empty range', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/fin/profit-trace')
    await expect(page.locator('h1')).toHaveText('利润反查', { timeout: 15_000 })
    await page.getByTestId('fin-trace-tab-aggregate').click()
    await page.getByTestId('fin-trace-aggregate-from').fill('2026-10-09')
    await page.getByTestId('fin-trace-aggregate-to').fill('2026-10-01')
    await page.getByTestId('fin-trace-aggregate-query').click()
    await expect(page.getByTestId('fin-trace-aggregate-error')).toContainText('dateRange 须为开始日,结束日')
    await page.screenshot({ path: `${shotDir}/04-aggregate-bad-range.png`, fullPage: true })

    await page.getByTestId('fin-trace-aggregate-from').fill('1999-01-01')
    await page.getByTestId('fin-trace-aggregate-to').fill('1999-01-31')
    await page.getByTestId('fin-trace-aggregate-query').click()
    await expect(page.getByTestId('fin-trace-aggregate-error')).toHaveCount(0)
    await expect(page.getByTestId('fin-trace-aggregate-table')).toContainText('该维度暂无已核算利润')
    await page.getByTestId('fin-trace-aggregate-reset').click()
    await expect(page.getByTestId('fin-trace-aggregate-from')).toHaveValue('')
    await expect(page.getByTestId('fin-trace-aggregate-error')).toHaveCount(0)

    await page.getByTestId('fin-trace-tab-abnormal').click()
    await page.getByTestId('fin-trace-abnormal-platform').fill('ZZZ')
    await page.getByTestId('fin-trace-abnormal-query').click()
    await expect(page.getByTestId('fin-trace-abnormal-table')).toContainText('暂无异常利润')
    await page.getByTestId('fin-trace-abnormal-from').fill('2026-02-02')
    await page.getByTestId('fin-trace-abnormal-to').fill('2026-02-01')
    await page.getByTestId('fin-trace-abnormal-query').click()
    await expect(page.getByTestId('fin-trace-abnormal-error')).toContainText('dateRange 须为开始日,结束日')
    await page.screenshot({ path: `${shotDir}/05-abnormal-empty-and-range.png`, fullPage: true })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.getByTestId('fin-profit-tab-abnormal').click()
    await page.getByTestId('fin-profit-abnormal-from').fill('2026-03-03')
    await page.getByTestId('fin-profit-abnormal-to').fill('2026-03-01')
    await page.getByTestId('fin-profit-abnormal-query').click()
    await expect(page.getByTestId('fin-profit-abnormal-error')).toContainText('dateRange 须为开始日,结束日')
    await page.getByTestId('fin-profit-abnormal-reset').click()
    await page.getByTestId('fin-profit-abnormal-from').fill('1999-01-01')
    await page.getByTestId('fin-profit-abnormal-to').fill('1999-01-31')
    await page.getByTestId('fin-profit-abnormal-query').click()
    await expect(page.getByTestId('fin-profit-abnormal-error')).toHaveCount(0)
    await expect(page.getByTestId('fin-profit-abnormal-table')).toContainText('暂无偏离 2σ 的场次')
    await page.screenshot({ path: `${shotDir}/06-profit-abnormal-empty-range.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})

async function fillFixed(
  page: Page,
  opts: { name: string; accountId: number; groups: string; priority: number },
) {
  const drawer = page.getByTestId('fin-share-rule-drawer')
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('fin-share-rule-name').fill(opts.name)
  await drawer.getByTestId('fin-share-rule-target').selectOption('TEAM')
  await drawer.getByTestId('fin-share-rule-base').selectOption('NET_PROFIT')
  await drawer.getByTestId('fin-share-rule-rate-type').selectOption('FIXED')
  await drawer.getByTestId('fin-share-rule-fixed-rate').fill('100')
  await drawer.getByTestId('fin-share-rule-accounts').fill(String(opts.accountId))
  await drawer.getByTestId('fin-share-rule-groups').fill(opts.groups)
  await drawer.getByTestId('fin-share-rule-priority').fill(String(opts.priority))
  await drawer.getByTestId('fin-share-rule-from').fill('2026-10-08')
}
