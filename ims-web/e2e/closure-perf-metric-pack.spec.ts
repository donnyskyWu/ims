import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist E2E-S9-01 / E2E-S9-02（acceptance · 纯 UI · #86）
 * Given: 指标配置页可创建指标，并已锁定 COMPETE_SUBMIT_RATE
 * When: 分段区间重叠、权重合计 99/101/100、查看后点启用
 * Then: 1152、1154、绑定成功、1153 锁定文案可见
 */
const shotDir = '/opt/cursor/artifacts/e2e-86-screenshots'

test.describe('perf metric pack closure S9', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('score rule 1152, weight 99/101/100, compete enable 1153', async ({ page }) => {
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const codeA = `E2E_GMV_${stamp}`
    const codeB = `E2E_LIVE_${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/perf/metric')
    await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })
    await expect(page.getByTestId('compete-view')).toBeVisible()

    await page.getByTestId('metric-create-open').click()
    await page.getByTestId('metric-code').fill(codeA)
    await page.getByTestId('metric-name').fill(`GMV ${stamp}`)
    await page.getByTestId('metric-weight').fill('60')
    await page.getByTestId('segment-0-max').fill('80')
    await page.getByTestId('segment-1-min').fill('50')
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/perf/metric') && r.request().method() === 'POST',
      { timeout: 15_000 },
    )
    await page.locator('.drawer.on').getByTestId('metric-save').click()
    const saveJson = (await (await saveResp).json()) as { code: number; msg?: string }
    expect(saveJson.code, saveJson.msg || '').toBe(1152)
    await expect(page.getByTestId('metric-form-error')).toContainText('1152')
    await page.screenshot({ path: `${shotDir}/01-score-rule-1152.png` })

    await page.locator('.drawer.on').getByTestId('metric-rule-type').selectOption('LINEAR')
    await page.locator('.drawer.on').getByTestId('metric-save').click()
    await expect(page.locator('tbody tr').filter({ hasText: codeA })).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('metric-create-open').click()
    await page.getByTestId('metric-code').fill(codeA)
    await page.getByTestId('metric-name').fill(`重复 ${stamp}`)
    await page.getByTestId('metric-weight').fill('10')
    await page.locator('.drawer.on').getByTestId('metric-rule-type').selectOption('LINEAR')
    await page.locator('.drawer.on').getByTestId('metric-save').click()
    await expect(page.getByTestId('metric-form-error')).toContainText('1151')
    await page.screenshot({ path: `${shotDir}/02-dup-code-1151.png` })
    await page.locator('.drawer.on .dr-x').click()

    await page.getByTestId('metric-create-open').click()
    await page.getByTestId('metric-code').fill(codeB)
    await page.getByTestId('metric-name').fill(`场次 ${stamp}`)
    await page.locator('.drawer.on').getByTestId('metric-weight').fill('40')
    await page.locator('.drawer.on').getByTestId('metric-rule-type').selectOption('LINEAR')
    await page.locator('.drawer.on').getByTestId('metric-save').click()
    await expect(page.locator('tbody tr').filter({ hasText: codeB })).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('metric-bind-open').click()
    const bindDrawer = page.locator('.drawer.on')
    await bindDrawer.getByTestId('bind-position').selectOption('R5')
    await bindDrawer.getByTestId(`bind-check-${codeA}`).check()
    await bindDrawer.getByTestId(`bind-check-${codeB}`).check()
    await bindDrawer.getByTestId(`bind-weight-${codeA}`).fill('60')
    await bindDrawer.getByTestId(`bind-weight-${codeB}`).fill('39')
    await expect(bindDrawer.getByTestId('metric-weight-total')).toContainText('99')
    await bindDrawer.getByTestId('metric-bind-save').click()
    await expect(page.getByTestId('metric-bind-error')).toContainText('1154')
    await expect(page.getByTestId('metric-bind-error')).toContainText('99.00%')
    await page.screenshot({ path: `${shotDir}/03-weight-99-1154.png` })

    await bindDrawer.getByTestId(`bind-weight-${codeB}`).fill('41')
    await expect(bindDrawer.getByTestId('metric-weight-total')).toContainText('101')
    await bindDrawer.getByTestId('metric-bind-save').click()
    await expect(bindDrawer.getByTestId('metric-bind-error')).toContainText('1154')
    await expect(bindDrawer.getByTestId('metric-bind-error')).toContainText('101.00%')
    await page.screenshot({ path: `${shotDir}/04-weight-101-1154.png` })

    await bindDrawer.getByTestId(`bind-weight-${codeB}`).fill('40')
    await expect(bindDrawer.getByTestId('metric-weight-total')).toContainText('100')
    await bindDrawer.getByTestId('metric-bind-save').click()
    await expect(page.getByTestId('metric-bind-ok')).toContainText('已绑定 2 项指标')
    await page.screenshot({ path: `${shotDir}/05-weight-100-ok.png` })
    await page.locator('.drawer.on .dr-x').click()

    await page.getByTestId('compete-view').click()
    const competeDrawer = page.locator('.drawer.on')
    await expect(competeDrawer.getByTestId('compete-note')).toContainText('BR-110')
    await competeDrawer.getByTestId('compete-enable').click()
    await expect(page.getByTestId('compete-lock-error')).toContainText('1153')
    await expect(page.getByTestId('compete-lock-error')).toContainText('锁定禁用')
    await page.screenshot({ path: `${shotDir}/06-compete-enable-1153.png` })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})