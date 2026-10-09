import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  completeTrainStudyViaUi,
  createTrainMaterialViaUi,
  createTrainTaskViaUi,
  loginAdmin,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/train-stat-177'

/**
 * #177 · TRAIN-003 本地尾巴（纯 UI）
 * 本月日期窗、资料热度行打开资料详情、部门趋势与部门明细抽屉、逾期进度条。
 * 逾期行来自 seed `E2E-TRAIN-OD-76`。不改完成率口径，不重做问卷重答或资料筛选。
 */
test.describe('train stat local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('month range, heat detail, dept trend drawer, and overdue meter', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-tails-${Date.now()}`
    const materialTitle = `E2E 热度跳转 ${label}`
    const taskName = `E2E 看板尾巴 ${label}`
    const now = new Date()
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`

    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })
    const { taskId } = await createTrainTaskViaUi(page, {
      taskName,
      materialIds: [materialId],
      assignUserIds: [1],
    })
    await completeTrainStudyViaUi(page, taskId, taskName)

    const finishWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/finish-rate') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/train/stat')
    const finishBody = (await (await finishWait).json()) as {
      code: number
      data?: { byDept?: Array<{ finishRate?: number }> }
    }
    expect(finishBody.code).toBe(0)
    const lowCount = (finishBody.data?.byDept || []).filter((row) => (row.finishRate ?? 100) < 85).length
    if (lowCount > 0) {
      await expect(page.getByTestId('train-stat-finish-dept-low')).toHaveCount(lowCount)
    }

    const monthFinishWait = page.waitForResponse(
      (r) =>
        r.url().includes('/train/stat/finish-rate') &&
        r.url().includes(monthStart) &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    const monthHeatWait = page.waitForResponse(
      (r) =>
        r.url().includes('/train/stat/material-heat') &&
        r.url().includes(monthStart) &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('train-stat-range-month').click()
    const monthHeatBody = (await (await monthHeatWait).json()) as {
      code: number
      data?: Array<{ title?: string }>
    }
    expect((await (await monthFinishWait).json()).code).toBe(0)
    expect(monthHeatBody.code).toBe(0)
    expect(monthHeatBody.data?.some((row) => row.title === materialTitle)).toBeTruthy()
    const heatRow = page.getByTestId('train-stat-heat-row').filter({ hasText: materialTitle })
    await expect(heatRow).toBeVisible()
    await page.screenshot({ path: `${shotDir}/01-month-heat.png`, fullPage: true })

    await heatRow.click()
    await expect(page).toHaveURL(/\/ims\/train\/material/)
    const detail = page.getByTestId('train-material-detail-drawer')
    await expect(detail).toBeVisible({ timeout: 15_000 })
    await expect(detail).toContainText(materialTitle)
    await page.screenshot({ path: `${shotDir}/02-heat-material-detail.png`, fullPage: true })

    const deptWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/dept') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/train/stat')
    await page.getByTestId('train-stat-tab-dept').click()
    const deptBody = (await (await deptWait).json()) as {
      code: number
      data?: Array<{ statDate?: string; finishRate?: number }>
    }
    expect(deptBody.code).toBe(0)
    expect((deptBody.data || []).length).toBeGreaterThan(0)
    await expect(page.getByTestId('train-stat-dept-trend')).toBeVisible()
    await expect(page.getByTestId('train-stat-dept-trend-bar').first()).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-dept-trend.png`, fullPage: true })

    const firstRow = page.getByTestId('train-stat-dept-row').first()
    const statDate = (await firstRow.locator('td').first().innerText()).trim()
    await firstRow.click()
    const drawer = page.getByTestId('train-stat-dept-drawer')
    await expect(drawer).toBeVisible()
    await expect(drawer).toContainText('部门明细')
    await expect(drawer.getByTestId('train-stat-drawer-row').filter({ hasText: statDate })).toBeVisible()
    await expect(drawer.getByTestId('train-stat-drawer-trend')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-dept-drawer.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toHaveCount(0)

    const overdueWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/overdue') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('train-stat-tab-overdue').click()
    await overdueWait
    const overdueRow = page.getByTestId('train-stat-overdue-row').filter({ hasText: 'E2E-TRAIN-OD-76' })
    await expect(overdueRow).toBeVisible()
    await expect(overdueRow.getByTestId('train-stat-overdue-progress')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/05-overdue-meter.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
