import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createDraftPlanViaUi,
  createSopViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  startPlanRowViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/content-152'

/**
 * #152 · SOP/计划筛选空态、启动后进度、公推模板筛选与预览空态（纯 UI）
 */
test.describe('content sop plan layout filters', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filters, empty states, and plan progress', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-152-${Date.now()}`
    const sopName = `E2E SOP ${label}`
    const nodeName = `节点-${label}`
    const planName = `E2E 计划 ${label}`

    await loginAdmin(page)
    const { sopId } = await createSopViaUi(page, { sopName, nodeName })

    await page.goto('/ims/content/sop')
    await page.getByTestId('sop-filter-type').selectOption('ARTICLE')
    const missResp = page.waitForResponse(
      (r) => r.url().includes('/content/sop/list') && r.url().includes('contentType=ARTICLE') && r.status() === 200,
    )
    await page.getByTestId('sop-filters').getByRole('button', { name: '查询' }).click()
    await missResp
    await expect(page.getByTestId('sop-list-empty')).toContainText('没有符合筛选的 SOP')
    await page.screenshot({ path: `${SHOTS}/01-sop-filter-empty.png`, fullPage: true })

    await page.getByTestId('sop-filter-type').selectOption('SHORT_VIDEO')
    await page.getByTestId('sop-filter-name').fill(sopName)
    const hitResp = page.waitForResponse(
      (r) => r.url().includes('/content/sop/list') && r.url().includes('SHORT_VIDEO') && r.status() === 200,
    )
    await page.getByTestId('sop-filters').getByRole('button', { name: '查询' }).click()
    await hitResp
    const sopRow = page.locator('tr', { hasText: sopName })
    await expect(sopRow).toBeVisible()
    await expect(sopRow).toContainText('ENABLED')

    const sopReset = page.waitForResponse(
      (r) => r.url().includes('/content/sop/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('sop-filter-reset').click()
    await sopReset
    await expect(sopRow).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/02-sop-filter-hit.png`, fullPage: true })

    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })

    await page.getByTestId('plan-filter-status').selectOption('TERMINATED')
    const planMiss = page.waitForResponse(
      (r) => r.url().includes('/content/plan') && r.url().includes('status=TERMINATED') && r.request().method() === 'GET',
    )
    await page.getByTestId('plan-filters').getByRole('button', { name: '查询' }).click()
    await planMiss
    await expect(page.getByTestId('plan-list-empty')).toContainText('没有符合筛选的计划')
    await page.screenshot({ path: `${SHOTS}/03-plan-filter-empty.png`, fullPage: true })

    await page.getByTestId('plan-filter-reset').click()
    await page.getByTestId('plan-filter-name').fill(planName)
    await page.getByTestId('plan-filter-status').selectOption('DRAFT')
    const planHit = page.waitForResponse(
      (r) => r.url().includes('/content/plan') && r.url().includes('status=DRAFT') && r.request().method() === 'GET',
    )
    await page.getByTestId('plan-filters').getByRole('button', { name: '查询' }).click()
    await planHit
    const planRow = page.locator('tr', { hasText: planName })
    await expect(planRow).toBeVisible()
    await expect(planRow.getByTestId('plan-progress')).toHaveText('—')

    const planReset = page.waitForResponse(
      (r) =>
        r.url().includes('/content/plan') &&
        !r.url().includes('/start') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('plan-filter-reset').click()
    await planReset
    await startPlanRowViaUi(page, planName)
    await expect(planRow.getByTestId('plan-progress')).toHaveText('0/1 · 0%')
    await page.screenshot({ path: `${SHOTS}/04-plan-progress.png`, fullPage: true })

    await page.goto('/ims/content/layout')
    await expect(page.locator('h1')).toHaveText('公推模板库')
    await page.getByTestId('layout-filter-name').fill(`missing-${label}`)
    const layoutMiss = page.waitForResponse(
      (r) => r.url().includes('/content/layout-template/list') && r.status() === 200,
    )
    await page.getByTestId('layout-filters').getByRole('button', { name: '查询' }).click()
    await layoutMiss
    await expect(page.getByTestId('layout-list-empty')).toContainText('没有符合筛选的模板')
    await page.screenshot({ path: `${SHOTS}/05-layout-filter-empty.png`, fullPage: true })

    await page.getByTestId('layout-filter-reset').click()
    const tplName = `空预览 ${label}`
    await page.getByRole('button', { name: '新建模板' }).click()
    const createModal = page.locator('.modal-mask').filter({ hasText: '新建公推模板' })
    await createModal.locator('input').fill(tplName)
    await createModal.getByRole('button', { name: '保存' }).click()
    const tplRow = page.locator('tr', { hasText: tplName })
    await expect(tplRow).toBeVisible({ timeout: 15_000 })
    await tplRow.getByRole('button', { name: '预览' }).click()
    const preview = page.locator('.modal-mask').filter({ hasText: '预览' })
    await expect(preview.getByTestId('layout-preview-empty')).toContainText('这条模板还没有预览 HTML')
    await page.screenshot({ path: `${SHOTS}/06-layout-preview-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
