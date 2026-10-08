import fs from 'node:fs'
import { inflateRawSync } from 'node:zlib'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist E2E-S12-02（acceptance · 纯 UI · #87）
 * Given: 报表管理新建报表，设计器把表格拖进画布并保存
 * When: 预览页按 DrillDimension 六维逐级点击，再导出当前层，再点 GMV
 * Then: 平台→账号→场次→人员→日期→主体均可见；再下钻 1195；xlsx 含主体值；穿透为来源模块详情
 */
const shotDir = '/opt/cursor/artifacts/e2e-87-screenshots'

const STEPS = [
  { label: '平台', value: '抖音' },
  { label: '账号', value: '神鱼官方' },
  { label: '场次', value: 'LS-20260928-01' },
  { label: '人员', value: '主播-林晓' },
  { label: '日期', value: '2026-09-28' },
  { label: '主体', value: '神鱼文化' },
]

function zipEntry(buf: Buffer, name: string): string {
  let offset = 0
  while (offset + 30 < buf.length) {
    if (buf.readUInt32LE(offset) !== 0x04034b50) break
    const method = buf.readUInt16LE(offset + 8)
    const compSize = buf.readUInt32LE(offset + 18)
    const nameLen = buf.readUInt16LE(offset + 26)
    const extraLen = buf.readUInt16LE(offset + 28)
    const entryName = buf.subarray(offset + 30, offset + 30 + nameLen).toString('utf8')
    const start = offset + 30 + nameLen + extraLen
    const data = buf.subarray(start, start + compSize)
    if (entryName === name) {
      const raw = method === 0 ? data : inflateRawSync(data)
      return raw.toString('utf8')
    }
    offset = start + compSize
  }
  throw new Error(`zip 中没有 ${name}`)
}

test.describe('bi drill pack closure S12', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('drag table then drill six dimensions, export and cell jump', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const reportName = `E2E 六维 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/bi/report/list')
    await expect(page.locator('h1')).toContainText('报表管理')

    await page.getByRole('button', { name: '新建报表' }).click()
    const reportModal = page.locator('.modal-mask .card').filter({ hasText: '新建报表' })
    await expect(reportModal).toBeVisible()
    await reportModal.locator('input.fld-in').first().fill(reportName)
    await reportModal.getByRole('button', { name: '保存草稿' }).click()
    await expect(page.locator('h1')).toContainText('报表设计器', { timeout: 15_000 })
    await expect(page.getByTestId('bi-palette-TABLE')).toBeVisible()

    await page.getByTestId('bi-palette-TABLE').dragTo(page.getByTestId('bi-canvas'))
    await expect(page.getByTestId('bi-canvas-comp')).toHaveCount(1)
    await expect(page.getByTestId('bi-canvas-comp')).toContainText('表格')
    await page.screenshot({ path: `${shotDir}/01-designer-drag.png` })

    await page.getByTestId('bi-save').click()
    await expect(page.getByTestId('bi-save-status')).toHaveText('已保存', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/02-designer-saved.png` })

    await page.getByTestId('bi-open-drill').click()
    await expect(page.locator('h1')).toHaveText('预览与下钻', { timeout: 15_000 })

    for (let index = 0; index < STEPS.length; index += 1) {
      const step = STEPS[index]
      await expect(page.getByTestId('bi-drill-dimension')).toHaveText(step.label)
      await expect(page.getByTestId('bi-drill-value').first()).toContainText(step.value)
      if (index === 0) await page.screenshot({ path: `${shotDir}/03-drill-platform.png` })
      if (index === 2) await page.screenshot({ path: `${shotDir}/04-drill-session.png` })
      if (index === STEPS.length - 1) await page.screenshot({ path: `${shotDir}/05-drill-subject.png` })
      if (index < STEPS.length - 1) await page.getByTestId('bi-drill-value').first().click()
    }

    await expect(page.getByTestId('bi-crumb-PLATFORM')).toContainText('抖音')
    await expect(page.getByTestId('bi-crumb-SESSION')).toContainText('LS-20260928-01')
    await expect(page.getByTestId('bi-crumb-DATE')).toContainText('2026-09-28')

    await page.getByTestId('bi-drill-value').first().click()
    await expect(page.getByTestId('bi-drill-toast')).toContainText('1195')
    await expect(page.getByTestId('bi-drill-dimension')).toHaveText('主体')
    await page.screenshot({ path: `${shotDir}/06-drill-1195.png` })

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('bi-export-xlsx').click(),
    ])
    expect(download.suggestedFilename()).toBe('bi_drill.xlsx')
    await expect(page.getByTestId('bi-export-note')).toContainText('神鱼文化')
    const saved = await download.path()
    expect(saved).toBeTruthy()
    const xml = zipEntry(fs.readFileSync(saved!), 'xl/worksheets/sheet1.xml')
    expect(xml).toContain('神鱼文化')
    expect(xml).toContain('主体')
    await page.screenshot({ path: `${shotDir}/07-export-xlsx.png` })

    await page.getByTestId('bi-metric-gmv').first().click()
    await expect(page.getByTestId('bi-cell-jump')).toContainText('来源模块详情')
    await expect(page.getByTestId('bi-cell-jump')).toContainText('LS-20260928-01')
    await page.screenshot({ path: `${shotDir}/08-cell-jump.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})