import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  loginAdmin,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/e2e-59-screenshots'

/**
 * Checklist **E2E-S3-06 / E2E-S3-07**（#59 · 纯 UI）
 * 结账 → LOCKED · 同期间再录入拦截 1142 · 锁后更正须 R4（FLOW 嵌入）通过后红冲
 * 期间取计划开播月，且每次用独立年月，避免锁住默认 2026-10 场次。
 */
test.describe('fin period lock and post-lock correction', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('close period blocks entry then R4 approval allows red correction', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOT_DIR, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const stamp = Date.now()
    const year = 3000 + (stamp % 5000)
    const month = String((Math.floor(stamp / 5000) % 12) + 1).padStart(2, '0')
    const periodMonth = `${year}-${month}`
    const planStartTime = `${periodMonth}-15T20:00:00+08:00`

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    const { sessionCode } = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E period lock ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })
    await submitAndConfirmFinCostViaUi(page, sessionCode)

    await page.getByTestId('fin-period-month').fill(periodMonth)
    await page.getByTestId('fin-period-month').blur()
    const closeResp = page.waitForResponse(
      (r) => r.url().includes('/fin/period/close') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('fin-period-close').click()
    const closeBody = (await (await closeResp).json()) as { code: number; data?: { financeStatus?: string } }
    expect(closeBody.code).toBe(0)
    expect(closeBody.data?.financeStatus).toBe('LOCKED')
    await expect(page.getByTestId('fin-period-status')).toHaveText('LOCKED')
    await expect(page.getByTestId('fin-period-lock-banner')).toContainText('财务期间已结账')
    await page.screenshot({ path: `${SHOT_DIR}/01-period-locked.png`, fullPage: true })

    const blocked = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      topic: `E2E period block ${stamp}`,
      planStartTime,
      gmv: 100_000,
      refundAmount: 2_000,
    })

    await page.goto('/ims/fin/cost')
    await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
    const reloadPeriod = page.waitForResponse(
      (r) =>
        r.url().includes('/fin/period') &&
        r.url().includes(encodeURIComponent(periodMonth)) &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('fin-period-month').fill(periodMonth)
    await page.getByTestId('fin-period-month').blur()
    await reloadPeriod
    await expect(page.getByTestId('fin-period-status')).toHaveText('LOCKED')
    await page.locator('.tab', { hasText: '待录入清单' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(blocked.sessionCode)
    const pendingResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await pendingResp
    const pendingRow = page.locator('tbody tr', { hasText: blocked.sessionCode }).first()
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await pendingRow.getByRole('button', { name: '录入' }).click()
    const entryDrawer = page.locator('.drawer.on').filter({ hasText: '成本录入' })
    await expect(entryDrawer).toBeVisible()
    const deniedResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/') && r.request().method() === 'POST' && r.status() === 200,
    )
    await entryDrawer.getByRole('button', { name: '提交' }).click()
    const deniedBody = (await (await deniedResp).json()) as { code: number; msg?: string }
    expect(deniedBody.code).toBe(1142)
    await expect(entryDrawer.getByTestId('fin-cost-entry-error')).toContainText('财务期间已结账')
    await page.screenshot({ path: `${SHOT_DIR}/02-entry-blocked-1142.png`, fullPage: true })
    await entryDrawer.locator('.dr-x').click()
    await expect(entryDrawer).not.toBeVisible({ timeout: 10_000 })

    await page.locator('.tab', { hasText: '已录入管理' }).click()
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const enteredRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(enteredRow).toContainText('已核准', { timeout: 15_000 })
    await enteredRow.getByTestId('fin-cost-correction-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '成本更正' })
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('fin-lock-adjust-panel')).toBeVisible()
    await drawer.getByRole('spinbutton', { name: '投放成本' }).fill('4000')
    await drawer.getByTestId('fin-cost-correction-reason').fill('锁后红冲投放')
    const blockedCorr = page.waitForResponse(
      (r) => r.url().includes('/correction') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('fin-cost-correction-submit').click()
    const blockedCorrBody = (await (await blockedCorr).json()) as { code: number }
    expect(blockedCorrBody.code).toBe(1155)
    await expect(drawer.getByTestId('fin-lock-adjust-error')).toContainText('R4')
    await page.screenshot({ path: `${SHOT_DIR}/03-correction-needs-r4.png`, fullPage: true })

    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('fin-lock-adjust-apply').click()
    const applyBody = (await (await applyResp).json()) as { code: number }
    expect(applyBody.code).toBe(0)
    await expect(drawer.getByTestId('fin-lock-adjust-status')).toHaveText('待审批')

    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/flow/task/') && r.url().includes('/handle') && r.request().method() === 'PUT',
    )
    await drawer.getByTestId('fin-lock-adjust-approve').click()
    const approveBody = (await (await approveResp).json()) as { code: number; data?: { newStatus?: string } }
    expect(approveBody.code).toBe(0)
    expect(approveBody.data?.newStatus).toBe('APPROVED')
    await expect(drawer.getByTestId('fin-lock-adjust-status')).toHaveText('已通过')
    await page.screenshot({ path: `${SHOT_DIR}/04-r4-approved.png`, fullPage: true })

    const corrResp = page.waitForResponse(
      (r) => r.url().includes('/correction') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('fin-cost-correction-submit').click()
    const corrBody = (await (await corrResp).json()) as {
      code: number
      data?: { recalcTriggered?: boolean; redEntries?: Array<{ item?: string; amount?: number }> }
    }
    expect(corrBody.code).toBe(0)
    expect(corrBody.data?.recalcTriggered).toBe(true)
    expect(corrBody.data?.redEntries?.some((entry) => entry.item === '投放成本' && entry.amount === -1000)).toBe(true)
    await expect(page.getByTestId('fin-lock-red-entries')).toContainText('红冲')
    await expect(page.getByTestId('fin-lock-red-entries')).toContainText('投放成本')
    await page.screenshot({ path: `${SHOT_DIR}/05-red-reverse-entry.png`, fullPage: true })

    await page.goto('/ims/fin/profit')
    await expect(page.locator('h1')).toHaveText('利润核算', { timeout: 15_000 })
    await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
    const profitResp = page.waitForResponse(
      (r) => r.url().includes('/fin/profit/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    const profitBody = (await (await profitResp).json()) as {
      code: number
      data?: { list?: Array<{ sessionCode?: string; calcStatus?: string; netProfit?: number }> }
    }
    expect(profitBody.code).toBe(0)
    const hit = profitBody.data?.list?.find((row) => row.sessionCode === sessionCode)
    expect(hit?.calcStatus).toBe('RECALCULATED')
    expect(hit?.netProfit).toBe(82_400)
    const profitRow = page.locator('tbody tr', { hasText: sessionCode }).first()
    await expect(profitRow).toContainText('82,400.00', { timeout: 15_000 })
    await expect(profitRow.getByTestId('fin-profit-calc-status')).toHaveText('已重算')
    await expect(profitRow.getByTestId('fin-profit-calculated-at')).toHaveText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    await profitRow.getByRole('button', { name: '详情' }).click()
    const detailDrawer = page.locator('.drawer').filter({ hasText: '利润详情' })
    await expect(detailDrawer).toBeVisible()
    await expect(detailDrawer).toContainText('已重算')

    expect(pageErrors).toEqual([])
  })
})
