import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * TC-15 C001～C003（纯 UI）
 * 指标编辑生成新版本；方案编辑指标，权重 ≠100 返回 1154，=100 提示方案已保存；
 * 启停开关切换生效中/已停用，停用后发起考核被拦截。
 */
const shotDir = '/opt/cursor/artifacts/e2e-tc15-screenshots'

test.describe('perf TC-15 C001-C003', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('edit metric version, scheme weights, and enable switch', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const codeA = `TC15A_${stamp}`
    const codeB = `TC15B_${stamp}`
    const schemeName = `TC15方案${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/perf/metric')
    await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })

    async function createManual(code: string, name: string) {
      await page.getByTestId('metric-create-open').click()
      const drawer = page.locator('.drawer.on')
      await drawer.getByTestId('metric-code').fill(code)
      await drawer.getByTestId('metric-name').fill(name)
      await drawer.getByTestId('metric-weight').fill('10')
      await drawer.getByTestId('metric-rule-type').selectOption('LINEAR')
      await drawer.getByTestId('metric-save').click()
      await expect(page.locator('tbody tr').filter({ hasText: code })).toBeVisible({ timeout: 15_000 })
    }

    await createManual(codeA, `指标甲${stamp}`)
    await page.getByTestId(`metric-edit-${codeA}`).click()
    const editDrawer = page.locator('.drawer.on')
    await expect(editDrawer.getByTestId('metric-edit-hint')).toContainText('历史周期')
    await editDrawer.getByTestId('linear-max-score').fill('80')
    await editDrawer.getByTestId('metric-save').click()
    await expect(page.getByTestId('metric-version-toast')).toContainText('已生成新版本 v2')
    await expect(page.getByTestId('metric-version-toast')).toContainText('历史周期不受影响')
    await expect(page.locator('tbody tr').filter({ hasText: codeA })).toContainText('v2')
    await page.screenshot({ path: `${shotDir}/01-metric-v2.png` })

    await createManual(codeB, `指标乙${stamp}`)

    await page.goto('/ims/perf/scheme')
    await expect(page.locator('h1')).toHaveText('考核方案', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建方案' }).click()
    const schemeModal = page.locator('.modal.card').filter({ hasText: '新建考核方案' })
    await schemeModal.locator('input').first().fill(schemeName)
    await schemeModal.getByRole('button', { name: '保存' }).click()
    const card = page.locator('.scheme-card').filter({ hasText: schemeName })
    await expect(card).toBeVisible({ timeout: 15_000 })

    await card.getByTestId('scheme-edit-metrics').click()
    const weightDrawer = page.locator('.drawer.on')
    await weightDrawer.getByTestId(`scheme-check-${codeA}`).check()
    await weightDrawer.getByTestId(`scheme-check-${codeB}`).check()
    await weightDrawer.getByTestId(`scheme-weight-${codeA}`).fill('40')
    await weightDrawer.getByTestId(`scheme-weight-${codeB}`).fill('40')
    await weightDrawer.getByTestId('scheme-edit-save').click()
    await expect(weightDrawer.getByTestId('scheme-edit-error')).toContainText('1154')
    await page.screenshot({ path: `${shotDir}/02-weight-1154.png` })

    await weightDrawer.getByTestId(`scheme-weight-${codeB}`).fill('60')
    await weightDrawer.getByTestId('scheme-edit-save').click()
    await expect(page.getByTestId('scheme-toast')).toContainText('方案已保存')
    await expect(card).toContainText('指标甲')
    await page.screenshot({ path: `${shotDir}/03-scheme-saved.png` })

    await card.getByTestId('scheme-toggle').click()
    await expect(page.getByTestId('scheme-toast')).toContainText('方案已停用')
    await expect(card.getByTestId('scheme-status')).toHaveText('已停用')
    await card.getByTestId('scheme-launch').click()
    await expect(page.getByTestId('scheme-toast')).toContainText('方案已停用，需启用后发起')
    await page.screenshot({ path: `${shotDir}/04-scheme-disabled.png` })

    await card.getByTestId('scheme-toggle').click()
    await expect(page.getByTestId('scheme-toast')).toContainText('方案已启用')
    await expect(card.getByTestId('scheme-status')).toHaveText('生效中')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
