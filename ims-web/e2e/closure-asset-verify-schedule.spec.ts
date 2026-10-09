import fs from 'fs'
import { test, expect, type Locator } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-131-screenshots'

/** Checklist 窄切片：办公设备关联校验的定时说明、指标、派发与复核闭环（#131） */
test.describe('corp asset verify schedule and dispatch closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('office verify drawer shows the schedule, dispatches a gap and closes it', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    const stamp = Date.now()
    const code = `AS-R2-${stamp}`
    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await create.getByTestId('corp-asset-code').fill(code)
    await create.getByTestId('corp-asset-name').fill(`校验限期显示器-${stamp}`)
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    const saved = (await (await saveResp).json()) as { code: number }
    expect(saved.code).toBe(0)
    await expect(create).toBeHidden()

    const board = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/batches') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('corp-asset-verify-open').click()
    await board
    const verify = page.locator('.drawer.on').filter({ hasText: '登记关联校验' })
    await expect(verify).toBeVisible()
    await expect(verify.getByTestId('asset-verify-schedule')).toContainText('每周一凌晨全量')
    await expect(verify.getByTestId('asset-verify-schedule')).toContainText('每日增量')
    await expect(verify.getByTestId('asset-verify-metrics')).toContainText('目标 98%')
    await expect(verify.getByTestId('asset-verify-complete')).toBeVisible()
    await expect(verify.getByTestId('asset-verify-consistency')).toBeVisible()
    const scheduled = verify.locator('[data-testid="asset-verify-batch-row"]').filter({ hasText: '定时' }).first()
    await expect(scheduled).toBeVisible({ timeout: 15_000 })
    await expect(scheduled.getByTestId('asset-verify-batch-scope')).toHaveText(/全量|增量/)
    await page.screenshot({ path: `${shotDir}/01-schedule-and-metrics.png`, fullPage: true })

    await verify.getByTestId('asset-verify-asset-code').fill(code)
    const ran = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/run') && r.request().method() === 'POST' && r.status() === 200,
    )
    await verify.getByTestId('asset-verify-run').click()
    const body = (await (await ran).json()) as { code: number; data?: { batchNo?: string } }
    expect(body.code).toBe(0)
    const runNo = body.data?.batchNo || ''
    expect(runNo).toMatch(/^AV/)
    await expect(verify.getByTestId('asset-verify-summary')).toContainText(runNo)
    const gap = verify.locator('[data-testid="asset-verify-row"]').filter({ hasText: code }).first()
    await expect(gap).toContainText('未关联实名人')
    await page.screenshot({ path: `${shotDir}/02-gap-found.png`, fullPage: true })

    const person = manualPersonRow(verify, runNo)
    await expect(person.getByTestId('asset-verify-batch-status')).toHaveText('待派发')
    await expect(person).toContainText(/20\d{2}/)
    await verify.getByTestId('asset-verify-owner').selectOption({ label: '管理员' })
    const dispatched = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/task/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await person.getByTestId('asset-verify-dispatch').click()
    const dispatchBody = (await (await dispatched).json()) as { code: number }
    expect(dispatchBody.code).toBe(0)
    await expect(manualPersonRow(verify, runNo).getByTestId('asset-verify-batch-status')).toHaveText('修复中')
    await page.screenshot({ path: `${shotDir}/03-dispatched.png`, fullPage: true })

    await verify.getByTestId('asset-verify-close-remark').fill('现场补录后复核')
    const closed = page.waitForResponse(
      (r) => r.url().includes('/asset/verify/task/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await manualPersonRow(verify, runNo).getByTestId('asset-verify-close').click()
    const closeBody = (await (await closed).json()) as { code: number }
    expect(closeBody.code).toBe(0)
    await expect(manualPersonRow(verify, runNo).getByTestId('asset-verify-batch-status')).toHaveText('已闭环')
    await page.screenshot({ path: `${shotDir}/04-closed.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})

function manualPersonRow(verify: Locator, runNo: string) {
  return verify
    .locator('[data-testid="asset-verify-batch-row"]')
    .filter({ hasText: '手动' })
    .filter({ hasText: '资产↔实名人' })
    .filter({ hasText: runNo })
    .first()
}
