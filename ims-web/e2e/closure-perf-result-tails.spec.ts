import fs from 'node:fs'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #170 · E2E-S9 结果页尾巴（纯 UI）
 * 调整到 PerfGrade 边界后下发，结果页看到等级文案；
 * 单号/姓名筛空；导出空表说明；执行页无匹配空态。
 */
const SHOTS = '/opt/cursor/artifacts/e2e-170-screenshots'

function letterOf(score: number) {
  if (score >= 90) return 'S ≥90'
  if (score >= 80) return 'A 80-89'
  if (score >= 70) return 'B 70-79'
  if (score >= 60) return 'C 60-69'
  return 'D <60'
}

function pickTarget(base: number) {
  const limit = Math.round(base * 0.2 * 10000) / 10000
  const edges = [90, 80, 70, 60, 59.9]
  const current = letterOf(base)
  const fits = edges.filter((score) => Math.abs(Math.round((score - base) * 10) / 10) <= limit + 1e-6)
  const score = fits.find((item) => letterOf(item) !== current) ?? fits[0] ?? base
  const delta = Math.round((score - base) * 10) / 10
  return { score, delta, label: letterOf(score) }
}

async function readScore(page: Page, recordNo: string) {
  const row = page.locator('tbody tr').filter({ hasText: recordNo }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  const text = (await row.locator('td').nth(5).innerText()).replace('分', '').trim()
  return { row, score: Number(text) }
}

test.describe('perf result tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('grade edge, empty filter, and empty export (#170)', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const uniq = `e2e-perf-170-${Date.now()}`
    const schemeName = `E2E 边界方案 ${uniq}`
    const month = (Math.floor(Date.now() / 1000) % 11) + 1
    const periodStart = `2028-${String(month).padStart(2, '0')}-01`
    const periodEnd = `2028-${String(month).padStart(2, '0')}-28`

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
    const execBody = (await (await execResp).json()) as { code: number; data?: { id: number; recordNo: string } }
    expect(execBody.code).toBe(0)
    const recordNo = execBody.data!.recordNo
    const recordId = execBody.data!.id

    await page.goto('/ims/perf/execution')
    await expect(page.locator('h1')).toContainText('执行考核')
    let located = await readScore(page, recordNo)
    await located.row.getByText('算分').click()
    await expect(located.row.locator('.tag')).toContainText('已计算', { timeout: 15_000 })
    located = await readScore(page, recordNo)
    expect(Number.isFinite(located.score)).toBeTruthy()
    const target = pickTarget(located.score)

    if (target.delta !== 0) {
      await located.row.getByText('调整').click()
      const adjustModal = page.locator('.modal.card').filter({ hasText: '人工调整' })
      await adjustModal.locator('input[type="number"]').fill(String(target.delta))
      const adjustResp = page.waitForResponse(
        (r) => r.url().includes(`/perf/execution/${recordId}/adjust`) && r.request().method() === 'PUT',
      )
      await adjustModal.getByRole('button', { name: '保存' }).click()
      const adjustJson = (await (await adjustResp).json()) as { code: number; msg?: string }
      expect(adjustJson.code, adjustJson.msg || '').toBe(0)
      located = await readScore(page, recordNo)
    }

    await located.row.getByText('确认').click()
    await expect(located.row.locator('.tag')).toContainText('已确认', { timeout: 15_000 })
    await located.row.getByText('下发').click()
    await expect(located.row).toContainText('已下发', { timeout: 15_000 })

    await page.goto('/ims/perf/result')
    await expect(page.locator('h1')).toContainText('考核结果')
    await page.getByTestId('perf-result-status').selectOption('ISSUED')
    await page.getByTestId('perf-result-no').fill(recordNo)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/perf/result/list') && r.request().method() === 'GET',
    )
    await page.getByTestId('perf-result-query').click()
    expect(((await (await listResp).json()) as { code: number }).code).toBe(0)
    const resultRow = page.getByTestId('perf-result-row').filter({ hasText: recordNo })
    await expect(resultRow).toBeVisible({ timeout: 15_000 })
    await expect(resultRow.getByTestId('perf-result-grade')).toHaveText(target.label)
    await expect(page.getByTestId('perf-result-dist')).toContainText('边界 90 / 80 / 70 / 60')
    await page.screenshot({ path: `${SHOTS}/01-grade-edge.png`, fullPage: true })

    await page.getByTestId('perf-result-name').fill('NO-SUCH-PERF-170')
    await page.getByTestId('perf-result-query').click()
    await expect(page.getByTestId('perf-result-empty')).toContainText('当前筛选没有考核结果')
    await page.screenshot({ path: `${SHOTS}/02-filter-empty.png`, fullPage: true })

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('perf-result-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('perf_results.csv')
    await expect(page.getByTestId('perf-result-export-note')).toContainText('已导出空表')
    const filePath = await download.path()
    const text = fs.readFileSync(filePath!, 'utf8').replace(/^\uFEFF/, '')
    expect(text.trim()).toBe('recordNo,evaluateeName,position,cycleDisplay,totalScore,grade,status')
    expect(text).not.toContain(recordNo)
    await page.screenshot({ path: `${SHOTS}/03-empty-export.png`, fullPage: true })

    await page.goto('/ims/perf/execution')
    await page.getByPlaceholder('被考核人').fill('NO-SUCH-PERF-170')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('perf-exec-empty')).toContainText('没有符合筛选条件的考核单')
    await page.screenshot({ path: `${SHOTS}/04-issue-filter-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
