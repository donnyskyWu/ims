import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/dc-dashboard-133'

/**
 * #133 · DC-003 看板布局设计器 + freshness 同步任务（纯 UI）
 * 登录后打开全链路看板，创建并保存布局，再改一格后保存；同步任务表可见。
 */
test.describe('dc dashboard layout and freshness', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('create and save dashboard layout and show sync freshness', async ({ page }) => {
    test.setTimeout(90_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/dc/trace')
    await page.getByTestId('dc-trace-dashboard').click()
    await page.waitForURL(/\/ims\/dc\/dashboard/)

    const freshness = page.getByTestId('dc-dash-freshness')
    await expect(freshness).toBeVisible()
    await expect(freshness).toContainText('DWD→DWS')
    await expect(freshness).toContainText('SUCCESS')
    await expect(page.getByTestId('dc-dash-asof')).toContainText('数据截至')
    await expect(page.getByTestId('dc-dash-gmv')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/01-overview-freshness.png`, fullPage: true })

    await page.getByTestId('dc-dash-manage').click()
    const drawer = page.getByTestId('dc-dash-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('dc-dash-new').click()
    await drawer.getByTestId('dc-dash-name').fill('经营总览-133')
    await drawer.getByTestId('dc-dash-widget-METRIC_CARD').click()
    await drawer.getByTestId('dc-dash-widget-HEALTH_PANEL').click()
    await expect(drawer.getByTestId('dc-dash-canvas-widget')).toHaveCount(2)
    await page.screenshot({ path: `${SHOTS}/02-layout-designer.png`, fullPage: true })

    const created = page.waitForResponse(
      (res) => res.url().includes('/dc/dashboard') && res.request().method() === 'POST' && res.status() === 200,
    )
    await drawer.getByTestId('dc-dash-save').click()
    const createdBody = await (await created).json()
    expect(createdBody.code).toBe(0)
    expect(createdBody.data.dashboardName).toBe('经营总览-133')
    await expect(drawer.getByTestId('dc-dash-save-note')).toContainText('看板已创建')
    await expect(page.getByTestId('dc-dash-select')).toContainText('经营总览-133')
    await expect(page.getByTestId('dc-dash-layout-preview')).toContainText('指标卡')
    await expect(page.getByTestId('dc-dash-layout-preview')).toContainText('健康面板')

    await drawer.getByTestId('dc-dash-canvas-widget').first().click()
    await drawer.getByTestId('dc-dash-pos-y').fill('3')
    const saved = page.waitForResponse(
      (res) => res.url().includes('/dc/dashboard/') && res.request().method() === 'PUT' && res.status() === 200,
    )
    await drawer.getByTestId('dc-dash-save').click()
    const savedBody = await (await saved).json()
    expect(savedBody.code).toBe(0)
    expect(savedBody.data).toBeNull()
    await expect(drawer.getByTestId('dc-dash-save-note')).toContainText('布局已保存')
    await page.screenshot({ path: `${SHOTS}/03-layout-saved.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
