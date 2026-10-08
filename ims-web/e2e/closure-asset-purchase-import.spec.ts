import fs from 'fs'
import os from 'os'
import path from 'path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-68-screenshots'

/** Checklist **E2E-S5-01**（#68 · 纯 UI）· 采购入台账 → 批量导入；行级错误；部分成功 */
test.describe('corp asset purchase import closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('csv import writes good purchase rows and locates the bad row', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    const stamp = Date.now()
    const ok1 = `AS-E2E68-${stamp}-A`
    const bad = `AS-E2E68-${stamp}-B`
    const ok2 = `AS-E2E68-${stamp}-C`
    const csvPath = path.join(os.tmpdir(), `ims-purchase-${stamp}.csv`)
    fs.writeFileSync(
      csvPath,
      [
        'assetCode,assetName,assetType,spec,purchaseDate',
        `${ok1},采购笔记本,OFFICE,14寸,2026-10-08`,
        `${bad},,OFFICE,坏行,2026-13-01`,
        `${ok2},采购显示器,OFFICE,27寸,2026-10-08`,
        '',
      ].join('\n'),
      'utf8',
    )

    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })
    await page.getByTestId('corp-asset-import-btn').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '采购导入' })
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('corp-asset-import-file').setInputFiles(csvPath)
    await page.screenshot({ path: `${shotDir}/01-import-file-chosen.png`, fullPage: true })

    const importResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger/import') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('corp-asset-import-save').click()
    const imported = (await (await importResp).json()) as {
      code: number
      data?: {
        partial?: boolean
        successCount?: number
        failCount?: number
        batchNo?: string
        errors?: Array<{ rowNo?: number; field?: string }>
      }
    }
    expect(imported.code).toBe(0)
    expect(imported.data?.partial).toBe(true)
    expect(imported.data?.successCount).toBe(2)
    expect(imported.data?.failCount).toBe(1)
    expect(imported.data?.errors?.[0]?.rowNo).toBe(3)
    expect(imported.data?.errors?.[0]?.field).toBe('assetName')

    const summary = drawer.getByTestId('corp-asset-import-summary')
    await expect(summary).toContainText('部分成功')
    await expect(summary).toContainText('成功 2 条')
    await expect(summary).toContainText('失败 1 条')
    const errors = drawer.getByTestId('corp-asset-import-errors')
    await expect(errors).toContainText('第 3 行')
    await expect(errors).toContainText('assetName')
    await expect(errors).toContainText('资产名称')
    await expect(drawer.getByTestId('corp-asset-import-ok')).toContainText(ok1)
    await expect(drawer.getByTestId('corp-asset-import-ok')).toContainText(ok2)
    await expect(drawer.getByTestId('corp-asset-import-ok')).not.toContainText(bad)
    await expect(drawer.getByTestId('corp-asset-import-batch')).toHaveText(imported.data?.batchNo || '')
    await page.screenshot({ path: `${shotDir}/02-partial-success-row-error.png`, fullPage: true })

    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()
    const keyword = page.locator('form.qbar input').first()
    await keyword.fill(`AS-E2E68-${stamp}`)
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    const rowA = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: ok1 })
    const rowC = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: ok2 })
    await expect(rowA).toBeVisible()
    await expect(rowC).toBeVisible()
    await expect(rowA.getByTestId('corp-asset-status')).toHaveText('待审核')
    await expect(rowC.getByTestId('corp-asset-status')).toHaveText('待审核')
    await expect(rowA).toContainText('2026-10-08')
    await expect(page.locator('.tbl-wrap').first()).not.toContainText(bad)
    await page.screenshot({ path: `${shotDir}/03-ledger-partial-rows.png`, fullPage: true })

    await rowA.getByTestId('corp-asset-detail-btn').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(detail).toBeVisible()
    await expect(detail.getByTestId('corp-asset-detail-batch')).toHaveText(imported.data?.batchNo || '')
    const timeline = detail.getByTestId('corp-asset-timeline')
    await expect(timeline).toContainText('登记')
    await expect(timeline).toContainText('采购入台账')
    await page.screenshot({ path: `${shotDir}/04-purchase-timeline.png`, fullPage: true })
    await detail.getByRole('button', { name: '关闭' }).click()
    await expect(detail).toBeHidden()

    await keyword.fill(bad)
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.locator('.tbl-wrap').first()).toContainText('没有办公设备')
    await expect(page.locator('.tbl-wrap').first()).not.toContainText(bad)
    await page.screenshot({ path: `${shotDir}/05-bad-row-not-in-ledger.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
