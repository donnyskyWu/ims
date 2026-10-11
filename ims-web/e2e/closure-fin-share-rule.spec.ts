import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-84-screenshots'
fs.mkdirSync(shotDir, { recursive: true })

type ApiBody = { code: number; msg?: string; data?: { id?: number; version?: number } }

/**
 * #84 FIN-003 分成规则（纯 UI）
 * 创建固定比例 → 同基数不足 100% 可保存且提示剩余归公司 → 超过 100% 为 1146
 * → 编辑版本 +1 → 试算 → 1147 冲突确认 → 停用 → 阶梯重叠 1146 → 阶梯逐档试算
 */
test.describe('fin share rule closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('share rule crud validates 1146 and 1147 then simulates ladder', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const priorityBase = Math.floor(stamp / 1000)
    const groupName = `E2E分成${stamp}`
    const darenName = `E2E达人${stamp}`
    const darenEdited = `E2E达人修订${stamp}`
    const realnameName = `E2E实名${stamp}`
    const overName = `E2E超额${stamp}`
    const clashName = `E2E冲突${stamp}`
    const ladderName = `E2E阶梯${stamp}`

    await loginAdmin(page)
    await createIpGroup(page, groupName)
    await page.goto('/ims/fin/share/rule')
    await expect(page.locator('h1')).toHaveText('分成规则', { timeout: 15_000 })

    await saveFixed(page, {
      name: darenName,
      target: 'DAREN',
      percent: '60',
      groupName,
      priority: priorityBase,
    })
    await expect(page.locator('tbody tr', { hasText: darenName })).toContainText('启用')
    await page.screenshot({ path: `${shotDir}/01-rule-created.png`, fullPage: true })

    await page.getByTestId('fin-share-rule-create').click()
    await fillCommon(page, {
      name: realnameName,
      target: 'REALNAME',
      groupName,
      priority: priorityBase + 1,
    })
    await page.getByTestId('fin-share-rule-fixed-rate').fill('39.99')
    const lowResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST' && !r.url().includes('/simulate'),
    )
    await page.getByTestId('fin-share-rule-save').click()
    const lowBody = (await (await lowResp).json()) as ApiBody
    expect(lowBody.code).toBe(0)
    await expect(page.getByTestId('fin-share-rule-sum')).toContainText('剩余归公司')
    await page.screenshot({ path: `${shotDir}/02-sum-shortfall.png`, fullPage: true })

    await page.getByTestId('fin-share-rule-create').click()
    await fillCommon(page, {
      name: overName,
      target: 'REALNAME',
      groupName,
      priority: priorityBase + 2,
    })
    await page.getByTestId('fin-share-rule-fixed-rate').fill('40.01')
    const highResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST' && !r.url().includes('/simulate'),
    )
    await page.getByTestId('fin-share-rule-save').click()
    const highBody = (await (await highResp).json()) as ApiBody
    expect(highBody.code).toBe(1146)
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('1146')
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('100.01%')
    await page.screenshot({ path: `${shotDir}/02-error-1146-sum.png`, fullPage: true })
    await page.getByTestId('fin-share-rule-drawer').getByRole('button', { name: '关闭' }).click()

    const darenRow = page.locator('tbody tr', { hasText: darenName })
    await darenRow.getByRole('button', { name: '编辑' }).click()
    await expect(page.getByTestId('fin-share-rule-drawer')).toContainText('不影响已生成分成单')
    await page.getByTestId('fin-share-rule-name').fill(darenEdited)
    const editResp = page.waitForResponse(
      (r) => /\/fin\/share\/rule\/\d+/.test(r.url()) && r.request().method() === 'PUT',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const editBody = (await (await editResp).json()) as ApiBody
    expect(editBody.code).toBe(0)
    expect(editBody.data?.version).toBe(2)
    const editedRow = page.locator('tbody tr', { hasText: darenEdited })
    await expect(editedRow).toContainText('V2')

    await editedRow.getByTestId('fin-share-rule-simulate').click()
    await page.getByTestId('fin-share-rule-sim-base').fill('10000')
    const simResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/simulate') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-sim-submit').click()
    expect(((await (await simResp).json()) as ApiBody).code).toBe(0)
    await expect(page.getByTestId('fin-share-rule-sim-amount')).toContainText('6,000.00')
    await page.screenshot({ path: `${shotDir}/03-simulate-fixed.png`, fullPage: true })
    await page.getByTestId('fin-share-rule-sim-drawer').getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('fin-share-rule-create').click()
    await fillCommon(page, {
      name: clashName,
      target: 'DAREN',
      groupName,
      priority: priorityBase + 3,
    })
    await page.getByTestId('fin-share-rule-fixed-rate').fill('60')
    const clashResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const clashBody = (await (await clashResp).json()) as ApiBody
    expect(clashBody.code).toBe(1147)
    await expect(page.getByTestId('fin-share-rule-conflict')).toContainText('确认强制保存')
    await page.screenshot({ path: `${shotDir}/04-conflict-1147.png`, fullPage: true })
    const forcedResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-conflict-confirm').click()
    expect(((await (await forcedResp).json()) as ApiBody).code).toBe(0)
    const clashRow = page.locator('tbody tr', { hasText: clashName })
    await expect(clashRow).toContainText('启用')

    await clashRow.getByTestId('fin-share-rule-disable').click()
    await expect(page.getByTestId('fin-share-rule-disable-dialog')).toContainText('历史分成单引用不受影响')
    const disableResp = page.waitForResponse(
      (r) => /\/fin\/share\/rule\/\d+/.test(r.url()) && r.request().method() === 'DELETE',
    )
    await page.getByTestId('fin-share-rule-disable-confirm').click()
    expect(((await (await disableResp).json()) as ApiBody).code).toBe(0)
    await expect(clashRow).toContainText('停用')
    await page.screenshot({ path: `${shotDir}/05-rule-disabled.png`, fullPage: true })

    await page.getByTestId('fin-share-rule-create').click()
    await fillCommon(page, {
      name: ladderName,
      target: 'TEAM',
      groupName,
      priority: priorityBase + 4,
    })
    await page.getByTestId('fin-share-rule-rate-type').selectOption('LADDER')
    const mins = page.getByTestId('fin-share-rule-ladder-min')
    const maxes = page.getByTestId('fin-share-rule-ladder-max')
    const rates = page.getByTestId('fin-share-rule-ladder-rate')
    await mins.nth(0).fill('0')
    await maxes.nth(0).fill('100')
    await rates.nth(0).fill('10')
    await mins.nth(1).fill('50')
    await maxes.nth(1).fill('200')
    await rates.nth(1).fill('20')
    const overlapResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-save').click()
    const overlapBody = (await (await overlapResp).json()) as ApiBody
    expect(overlapBody.code).toBe(1146)
    await expect(page.getByTestId('fin-share-rule-error')).toContainText('重叠')

    await maxes.nth(0).fill('10000')
    await mins.nth(1).fill('10000')
    await maxes.nth(1).fill('')
    const ladderResp = page.waitForResponse(
      (r) => r.url().includes('/fin/share/rule') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-save').click()
    expect(((await (await ladderResp).json()) as ApiBody).code).toBe(0)
    const ladderRow = page.locator('tbody tr', { hasText: ladderName })
    await expect(ladderRow).toContainText('阶梯')
    await ladderRow.getByTestId('fin-share-rule-simulate').click()
    await page.getByTestId('fin-share-rule-sim-base').fill('15000')
    const ladderSim = page.waitForResponse(
      (r) => r.url().includes('/fin/share/simulate') && r.request().method() === 'POST',
    )
    await page.getByTestId('fin-share-rule-sim-submit').click()
    expect(((await (await ladderSim).json()) as ApiBody).code).toBe(0)
    await expect(page.getByTestId('fin-share-rule-sim-amount')).toContainText('2,000.00')
    await expect(page.getByTestId('fin-share-rule-sim-detail')).toContainText('1,000.00')
    await page.screenshot({ path: `${shotDir}/06-simulate-ladder.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})

async function createIpGroup(page: Page, name: string) {
  await page.goto('/ims/ip-group')
  await page.getByRole('button', { name: '+ 新建大组' }).click()
  const panel = page.locator('.drawer-panel')
  await panel.locator('input').first().fill(name)
  const created = page.waitForResponse((r) => r.url().includes('/ip-group/create') && r.request().method() === 'POST')
  await panel.getByRole('button', { name: '确定' }).click()
  expect(((await (await created).json()) as ApiBody).code).toBe(0)
  await expect(page.getByText('已创建 IP 组')).toBeVisible()
}

async function selectGroup(page: Page, groupName: string) {
  const search = page.getByTestId('fin-share-rule-group-search')
  await search.fill(groupName)
  const listed = page.waitForResponse((r) => r.url().includes('/ip-group/list'))
  await search.press('Enter')
  await listed
  await page.getByTestId('fin-share-rule-groups').getByText(groupName, { exact: true }).click()
}

async function fillCommon(
  page: Page,
  opts: { name: string; target: string; groupName: string; priority: number },
) {
  const drawer = page.getByTestId('fin-share-rule-drawer')
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('fin-share-rule-name').fill(opts.name)
  await drawer.getByTestId('fin-share-rule-target').selectOption(opts.target)
  await drawer.getByTestId('fin-share-rule-base').selectOption('NET_PROFIT')
  await drawer.getByTestId('fin-share-rule-rate-type').selectOption('FIXED')
  await selectGroup(page, opts.groupName)
  await drawer.getByTestId('fin-share-rule-priority').fill(String(opts.priority))
  await drawer.getByTestId('fin-share-rule-from').fill('2026-10-08')
}

async function saveFixed(
  page: Page,
  opts: { name: string; target: string; percent: string; groupName: string; priority: number },
) {
  await page.getByTestId('fin-share-rule-create').click()
  await fillCommon(page, opts)
  await page.getByTestId('fin-share-rule-fixed-rate').fill(opts.percent)
  const resp = page.waitForResponse(
    (r) => r.url().includes('/fin/share/rule') && !r.url().includes('/simulate') && r.request().method() === 'POST',
  )
  await page.getByTestId('fin-share-rule-save').click()
  const body = (await (await resp).json()) as ApiBody
  expect(body.code).toBe(0)
}
