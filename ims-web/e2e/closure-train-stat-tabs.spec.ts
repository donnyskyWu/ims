import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  completeTrainStudyViaUi,
  createTrainMaterialViaUi,
  createTrainTaskViaUi,
  loginAdmin,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-76-screenshots'

/**
 * Checklist **E2E-S10-02 延伸**（#76 · 纯 UI）
 * 学完后看板：部门统计 / 时长排行 / 资料热度与完成率同一日期窗。
 * 逾期行来自 seed `E2E-TRAIN-OD-76`（页面不能把截止时间设到过去）。
 */
test.describe('train stat remaining tabs closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('dept rank heat and overdue tabs follow the finish-rate caliber', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-tabs-${Date.now()}`
    const materialTitle = `E2E 热度资料 ${label}`
    const taskName = `E2E 看板任务 ${label}`

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
    const heatWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/material-heat') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/train/stat')
    const finishBody = (await (await finishWait).json()) as {
      code: number
      data?: { byDept?: Array<{ assignedCount?: number; finishedCount?: number }> }
    }
    const heatBody = (await (await heatWait).json()) as {
      code: number
      data?: Array<{ title?: string; studyCount?: number; avgDurationMinutes?: number }>
    }
    expect(finishBody.code).toBe(0)
    expect(heatBody.code).toBe(0)
    const heatHit = heatBody.data?.find((row) => row.title === materialTitle)
    expect(heatHit?.studyCount).toBeGreaterThanOrEqual(1)
    expect(heatHit?.avgDurationMinutes).toBeGreaterThanOrEqual(1)
    await expect(page.locator('h1')).toHaveText('培训统计看板')
    await expect(page.locator('[data-testid="train-stat-heat-row"]', { hasText: materialTitle })).toBeVisible()
    await page.locator('[data-testid="train-stat-heat"]').screenshot({
      path: `${shotDir}/04-material-heat.png`,
    })

    const deptWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/dept') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('train-stat-tab-dept').click()
    const deptBody = (await (await deptWait).json()) as {
      code: number
      data?: Array<{ assignedCount?: number; finishedCount?: number; statDate?: string; finishRate?: number }>
    }
    expect(deptBody.code).toBe(0)
    const finishAssigned = (finishBody.data?.byDept || []).reduce((sum, row) => sum + (row.assignedCount || 0), 0)
    const finishDone = (finishBody.data?.byDept || []).reduce((sum, row) => sum + (row.finishedCount || 0), 0)
    const deptAssigned = (deptBody.data || []).reduce((sum, row) => sum + (row.assignedCount || 0), 0)
    const deptDone = (deptBody.data || []).reduce((sum, row) => sum + (row.finishedCount || 0), 0)
    expect(deptAssigned).toBe(finishAssigned)
    expect(deptDone).toBe(finishDone)
    expect(deptDone).toBeGreaterThanOrEqual(1)
    await expect(page.getByTestId('train-stat-as-of')).toContainText('数据截至')
    await expect(page.getByTestId('train-stat-dept-row').first()).toBeVisible()
    await page.screenshot({ path: `${shotDir}/01-dept-tab.png`, fullPage: true })

    const rankWait = page.waitForResponse(
      (r) =>
        r.url().includes('/train/stat/rank') &&
        r.url().includes('dimension=PERSON') &&
        r.request().method() === 'GET' &&
        r.status() === 200,
    )
    await page.getByTestId('train-stat-tab-rank').click()
    await page.getByTestId('train-stat-rank-person').click()
    const rankBody = (await (await rankWait).json()) as {
      code: number
      data?: Array<{ userName?: string; totalDurationMinutes?: number; finishRate?: number }>
    }
    expect(rankBody.code).toBe(0)
    const person = rankBody.data?.find((row) => row.userName === '管理员')
    expect(person?.totalDurationMinutes).toBeGreaterThanOrEqual(1)
    expect((person?.finishRate ?? 0) > 0).toBeTruthy()
    await expect(page.getByTestId('train-stat-rank-row').filter({ hasText: '管理员' })).toBeVisible()
    await expect(page.getByTestId('train-stat-rank-row').filter({ hasText: '管理员' })).toContainText('分钟')
    await page.screenshot({ path: `${shotDir}/02-rank-person.png`, fullPage: true })

    const overdueWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/overdue') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('train-stat-tab-overdue').click()
    const overdueBody = (await (await overdueWait).json()) as {
      code: number
      data?: { list?: Array<{ taskName?: string; overdueDays?: number; progress?: number }> }
    }
    expect(overdueBody.code).toBe(0)
    const overdueHit = overdueBody.data?.list?.find((row) => row.taskName === 'E2E-TRAIN-OD-76')
    expect(overdueHit?.progress).toBe(40)
    expect(overdueHit?.overdueDays).toBeGreaterThanOrEqual(1)
    const overdueRow = page.getByTestId('train-stat-overdue-row').filter({ hasText: 'E2E-TRAIN-OD-76' })
    await expect(overdueRow).toBeVisible()
    await expect(overdueRow.getByTestId('train-stat-overdue-days')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/03-overdue-tab.png`, fullPage: true })

    await page.getByTestId('train-stat-overdue-dept').fill('999999')
    const emptyWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/overdue') && r.url().includes('deptId=999999') && r.status() === 200,
    )
    await page.getByRole('button', { name: '筛选' }).click()
    await emptyWait
    await expect(page.getByTestId('train-stat-overdue-row').filter({ hasText: 'E2E-TRAIN-OD-76' })).toHaveCount(0)

    await page.getByTestId('train-stat-overdue-dept').fill('')
    const backWait = page.waitForResponse(
      (r) => r.url().includes('/train/stat/overdue') && !r.url().includes('deptId=') && r.status() === 200,
    )
    await page.getByRole('button', { name: '筛选' }).click()
    await backWait
    await expect(overdueRow).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('train-stat-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('train_overdue.xls')
    await expect(page.getByTestId('train-stat-export-msg')).toHaveText('导出任务已提交')
    await page.screenshot({ path: `${shotDir}/05-overdue-export.png`, fullPage: true })

    await overdueRow.getByRole('button', { name: '去督办' }).click()
    await expect(page.getByText('学习记录 · E2E-TRAIN-OD-76')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.modal-mask').getByText('NOT_CONFIRMED')).toBeVisible()

    expect(pageErrors).toEqual([])
  })
})
