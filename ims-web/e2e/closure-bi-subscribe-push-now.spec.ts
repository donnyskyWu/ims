import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist **E2E-S12-切片**（acceptance · **纯 UI** · #39）
 * Given: UI 新建报表 + ACTIVE 订阅
 * When: `/ims/bi/report/subscribe`「立即推送」
 * Then: 快照区 GMV · 行内推送结果「钉钉成功」· 上次推送时间非「—」
 */
test.describe('bi subscribe push-now closure S12', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('push-now updates snapshot and last push columns', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-bi-push-${Date.now()}`
    const reportName = `E2E 报表 ${label}`
    const subName = `E2E 订阅 ${label}`

    await loginAdmin(page)

    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')

    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await expect(reportModal).toBeVisible()
    await reportModal.locator('input.fld-in').first().fill(reportName)
    const createReportResp = page.waitForResponse(
      (r) => r.url().includes('/bi/report') && r.request().method() === 'POST' && r.status() === 200,
    )
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    const createReportBody = (await (await createReportResp).json()) as {
      code: number
      data?: { id: number }
    }
    expect(createReportBody.code).toBe(0)
    const reportId = createReportBody.data!.id

    await page.goto('/ims/bi/report/subscribe')
    await expect(page.locator('h1')).toContainText('订阅与分享')

    await page.getByRole('button', { name: '订阅推送' }).click()
    const subModal = page.locator('.modal-mask .card').filter({ hasText: '新建订阅' })
    await expect(subModal).toBeVisible()
    await subModal.locator('input.fld-in').first().fill(subName)
    await subModal.locator('input[type="number"]').fill(String(reportId))
    const createSubResp = page.waitForResponse(
      (r) => r.url().includes('/bi/subscribe') && r.request().method() === 'POST' && r.status() === 200,
    )
    await subModal.getByRole('button', { name: '保存' }).click()
    const createSubBody = (await (await createSubResp).json()) as { code: number }
    expect(createSubBody.code).toBe(0)

    const row = page.locator('.tbl-wrap tbody tr', { hasText: subName })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('生效')
    await expect(row).toContainText('未推送')

    await row.getByText('立即推送').click()
    const confirm = page.getByTestId('bi-push-confirm')
    await expect(confirm).toContainText('本地桩')
    await confirm.getByRole('button', { name: '取消' }).click()
    await expect(confirm).toBeHidden()
    await expect(row).toContainText('未推送')

    const pushResp = page.waitForResponse(
      (r) => r.url().includes('/push-now') && r.request().method() === 'POST' && r.status() === 200,
    )
    await row.getByText('立即推送').click()
    await page.getByTestId('bi-push-confirm-ok').click()
    const pushBody = (await (await pushResp).json()) as {
      code: number
      data?: { lastPushStatus?: string; snapshot?: { summary?: { gmv: number } } }
    }
    expect(pushBody.code).toBe(0)
    expect(pushBody.data?.lastPushStatus).toMatch(/DING_OK|SITE_OK/)

    await expect(page.locator('.card').filter({ hasText: `快照 · ${subName}` })).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText(/GMV 4128000/)).toBeVisible()

    await expect(row).toContainText('钉钉成功', { timeout: 15_000 })
    const lastPushCell = row.locator('td').nth(6)
    await expect(lastPushCell).not.toHaveText('—')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
