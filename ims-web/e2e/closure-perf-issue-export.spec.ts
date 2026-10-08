import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/** Checklist 逐步闭环 · UI 方案/考核 → CONFIRMED → UI 下发 → 结果页导出 CSV（UTF-8 BOM） */
test.describe('perf issue export csv closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('issue from execution then export csv on result page', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)

    const uniq = `e2e-perf-closure-${Date.now()}`
    const schemeName = `E2E 闭环方案 ${uniq}`
    const month = (Math.floor(Date.now() / 1000) % 11) + 1
    const periodStart = `2027-${String(month).padStart(2, '0')}-01`
    const periodEnd = `2027-${String(month).padStart(2, '0')}-28`

    await loginAdmin(page)

    await page.goto('/ims/perf/scheme')
    await expect(page.locator('h1')).toHaveText('考核方案', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建方案' }).click()
    const schemeModal = page.locator('.modal.card').filter({ hasText: '新建考核方案' })
    await schemeModal.locator('input').first().fill(schemeName)
    const schemeResp = page.waitForResponse(
      (r) => r.url().includes('/perf/scheme') && r.request().method() === 'POST' && r.status() === 200,
    )
    await schemeModal.getByRole('button', { name: '保存' }).click()
    const schemeBody = (await (await schemeResp).json()) as { code: number; data?: { id: number } }
    expect(schemeBody.code).toBe(0)
    const schemeId = schemeBody.data!.id

    await page.goto(`/ims/perf/execution?schemeId=${schemeId}`)
    const execModal = page.locator('.modal.card').filter({ hasText: '创建考核' })
    await expect(execModal).toBeVisible({ timeout: 15_000 })
    await execModal.locator('input[type="number"]').first().fill(String(schemeId))
    await execModal.locator('input[type="number"]').nth(1).fill('1')
    await execModal.locator('select').first().selectOption('MONTHLY')
    await execModal.locator('.fld').filter({ hasText: '周期开始' }).locator('input').fill(periodStart)
    await execModal.locator('.fld').filter({ hasText: '周期结束' }).locator('input').fill(periodEnd)

    const execResp = page.waitForResponse(
      (r) => r.url().includes('/perf/execution') && r.request().method() === 'POST' && r.status() === 200,
    )
    await execModal.getByRole('button', { name: '保存' }).click()
    const execBody = (await (await execResp).json()) as {
      code: number
      data?: { id: number; recordNo: string }
    }
    expect(execBody.code).toBe(0)
    const recordNo = execBody.data!.recordNo
    const recordId = execBody.data!.id

    await page.goto('/ims/perf/execution')
    await expect(page.locator('h1')).toContainText('执行考核')

    const execTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '单号' }) })
    const execRow = execTable.locator('tbody tr').filter({ hasText: recordNo }).first()
    await expect(execRow).toBeVisible({ timeout: 15_000 })

    await execRow.getByText('算分').click()
    await expect(execRow.locator('.tag')).toContainText('已计算', { timeout: 15_000 })

    await execRow.getByText('确认').click()
    await expect(execRow.locator('.tag')).toContainText('已确认', { timeout: 15_000 })

    const issueResp = page.waitForResponse(
      (r) =>
        r.url().includes(`/perf/execution/${recordId}/issue`) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await execRow.getByText('下发').click()
    const issueJson = (await (await issueResp).json()) as { code: number }
    expect(issueJson.code).toBe(0)
    await expect(execRow).toContainText('已下发', { timeout: 15_000 })

    await page.goto('/ims/perf/result')
    await expect(page.locator('h1')).toContainText('考核结果')
    await page.locator('select').first().selectOption('ISSUED')
    await page.getByRole('button', { name: '查询' }).click()

    const resultTable = page.locator('.tbl-wrap table')
    await expect(resultTable.locator('tbody tr').filter({ hasText: recordNo })).toBeVisible({
      timeout: 15_000,
    })

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出 CSV' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('perf_results.csv')

    const filePath = await download.path()
    expect(filePath).toBeTruthy()
    const buf = fs.readFileSync(filePath!)
    expect(buf[0]).toBe(0xef)
    expect(buf[1]).toBe(0xbb)
    expect(buf[2]).toBe(0xbf)
    const text = buf.toString('utf8').replace(/^\uFEFF/, '')
    expect(text.split('\n')[0].trim()).toMatch(/^recordNo,/)
    expect(text).toContain(recordNo)
    expect(text).toContain('ISSUED')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
