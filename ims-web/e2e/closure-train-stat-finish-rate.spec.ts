import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  completeTrainStudyViaUi,
  createTrainMaterialViaUi,
  createTrainTaskViaUi,
  loginAdmin,
} from './closure-helpers'

/**
 * Checklist **E2E-S10-02 延伸**（#49 · 纯 UI）
 * 资料→任务→学习 CONFIRMED → 培训统计看板完成率总览可见 100%
 */
test.describe('train stat finish-rate tab closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('complete study then finish-rate tab shows task at 100%', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-stat-${Date.now()}`
    const materialTitle = `E2E 统计资料 ${label}`
    const taskName = `E2E 统计任务 ${label}`

    await loginAdmin(page)

    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })
    const { taskId } = await createTrainTaskViaUi(page, {
      taskName,
      materialIds: [materialId],
      assignUserIds: [1],
    })

    await completeTrainStudyViaUi(page, taskId, taskName)

    await page.goto('/ims/train/stat')
    const finishResp = await page.waitForResponse(
      (r) => r.url().includes('/train/stat/finish-rate') && r.request().method() === 'GET' && r.status() === 200,
      { timeout: 15_000 },
    )
    await expect(page.locator('h1')).toHaveText('培训统计看板', { timeout: 15_000 })
    await expect(page.locator('.tab.on', { hasText: '完成率总览' })).toBeVisible()

    const finishBody = (await finishResp.json()) as {
      code: number
      data?: {
        totalFinishRate?: number
        byTask?: Array<{ taskName?: string; finishRate?: number }>
        byPerson?: Array<{ userId?: number; finishRate?: number; finishedCount?: number }>
      }
    }
    expect(finishBody.code).toBe(0)
    expect((finishBody.data?.totalFinishRate ?? 0) >= 0).toBeTruthy()
    const taskHit = finishBody.data?.byTask?.find((r) => r.taskName === taskName)
    expect(taskHit?.finishRate).toBe(100)
    const personHit = finishBody.data?.byPerson?.find((r) => r.userId === 1)
    expect((personHit?.finishedCount ?? 0) >= 1).toBeTruthy()

    const totalRate = page.locator('[data-testid="train-stat-total-rate"]')
    await expect(totalRate).toBeVisible()
    await expect(totalRate).not.toHaveText('0%')

    expect(pageErrors).toEqual([])
  })
})
