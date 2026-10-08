import fs from 'fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-75-screenshots'
const GOOD_SESSION = 'IMS20261008DYE0076'
const CANCEL_SESSION = 'IMS20261008DYE0075'

/** 实名人下拉与列表接口一致，只展示首尾，中间打星。 */
function maskedName(name: string) {
  const text = name.trim()
  if (text.length <= 1) return text ? '*' : ''
  if (text.length === 2) return `${text[0]}*`
  return `${text[0]}${'*'.repeat(text.length - 2)}${text[text.length - 1]}`
}

async function openCreate(page: Page) {
  const existing = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  if (await existing.count()) return existing
  await page.getByTestId('corp-asset-create-btn').click()
  const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
  await expect(create).toBeVisible()
  return create
}

async function saveAndRead(page: Page, create: ReturnType<Page['locator']>) {
  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
  )
  await create.getByTestId('corp-asset-save').click()
  return (await (await saveResp).json()) as { code: number; msg?: string }
}

/** Checklist **E2E-S5-07**（#75 · 纯 UI · 登记关联校验 + 场次/成本层） */
test.describe('corp asset register association verify closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('office register form shows 1500 1501 1001 and a valid link shows session and cost layers', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const code = `AS-VY-${stamp}`
    const create = await openCreate(page)
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`关联校验显示器-${stamp}`)

    await create.getByTestId('corp-asset-bind-account').fill('AC-NO-SUCH-75')
    const missing = await saveAndRead(page, create)
    expect(missing.code).toBe(1500)
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('1500')
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('账号不存在')
    await page.screenshot({ path: `${shotDir}/01-account-missing-1500.png`, fullPage: true })

    await create.getByTestId('corp-asset-bind-account').fill('AC-E2E-ASSET-OFF')
    const stopped = await saveAndRead(page, create)
    expect(stopped.code).toBe(1501)
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('1501')
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('账号已停用')
    await page.screenshot({ path: `${shotDir}/02-account-disabled-1501.png`, fullPage: true })

    await create.getByTestId('corp-asset-bind-account').fill('AC-E2E-FIN')
    await create.getByTestId('corp-asset-bind-session').fill(CANCEL_SESSION)
    const cancelled = await saveAndRead(page, create)
    expect(cancelled.code).toBe(1501)
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('场次已取消')
    await page.screenshot({ path: `${shotDir}/03-session-cancelled-1501.png`, fullPage: true })

    await create.getByTestId('corp-asset-bind-account').fill('AC-E2E-LIVE1045')
    await create.getByTestId('corp-asset-bind-session').fill(GOOD_SESSION)
    const wrongAccount = await saveAndRead(page, create)
    expect(wrongAccount.code).toBe(1001)
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('1001')
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('场次不属于该账号')
    await page.screenshot({ path: `${shotDir}/04-session-owner-1001.png`, fullPage: true })

    await expect.poll(async () => create.getByTestId('corp-asset-realname').locator('option').count()).toBeGreaterThan(1)
    await create.getByTestId('corp-asset-realname').selectOption({ label: maskedName('E2E-Live-1045') })
    await create.getByTestId('corp-asset-bind-account').fill('AC-E2E-FIN')
    await create.getByTestId('corp-asset-bind-session').fill('')
    const wrongPerson = await saveAndRead(page, create)
    expect(wrongPerson.code).toBe(1001)
    await expect(create.getByTestId('corp-asset-form-error')).toContainText('账号不属于该实名人')
    await page.screenshot({ path: `${shotDir}/05-person-owner-1001.png`, fullPage: true })

    await create.getByTestId('corp-asset-realname').selectOption({ label: maskedName('E2E财务实名人') })
    await create.getByTestId('corp-asset-bind-account').fill('AC-E2E-FIN')
    await create.getByTestId('corp-asset-bind-session').fill(GOOD_SESSION)
    const saved = await saveAndRead(page, create)
    expect(saved.code).toBe(0)
    await expect(create).toBeHidden()

    await page.locator('.qbar input').first().fill(code)
    const filtered = page.waitForResponse(
      (r) => r.url().includes('/corp/device/office/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.qbar button[type="submit"]').click()
    await filtered
    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await expect(row.getByTestId('corp-asset-status')).toHaveText('待审核')
    await page.screenshot({ path: `${shotDir}/06-register-success.png`, fullPage: true })

    await row.getByTestId('corp-asset-forward-btn').click()
    const forward = page.locator('.drawer.on').filter({ hasText: '正向穿透' })
    await expect(forward.getByTestId('asset-forward-session')).toContainText(GOOD_SESSION)
    await expect(forward.getByTestId('asset-forward-session')).toContainText('已结束')
    await expect(forward.getByTestId('asset-forward-cost')).toHaveText('1,860.00')
    await expect(forward.getByTestId('asset-forward-revenue')).toHaveText('12,800.00')
    await page.screenshot({ path: `${shotDir}/07-session-cost-layers.png`, fullPage: true })
    await forward.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('corp-asset-verify-open').click()
    const verify = page.locator('.drawer.on').filter({ hasText: '登记关联校验' })
    await expect(verify).toBeVisible()
    await verify.getByTestId('asset-verify-asset-code').fill(code)
    const ran = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/run') && r.request().method() === 'POST' && r.status() === 200,
    )
    await verify.getByTestId('asset-verify-run').click()
    const body = (await (await ran).json()) as { code: number; data?: { batchNo?: string } }
    expect(body.code).toBe(0)
    expect(body.data?.batchNo || '').toMatch(/^AV/)
    await expect(verify.getByTestId('asset-verify-summary')).toContainText(body.data?.batchNo || '')
    await expect(verify.getByTestId('asset-verify-clean')).toContainText('该资产没有关联异常')
    await page.screenshot({ path: `${shotDir}/08-verify-clean.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
