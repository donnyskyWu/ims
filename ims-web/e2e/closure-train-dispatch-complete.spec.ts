import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createTrainMaterialViaUi,
  createTrainTaskViaUi,
  loginAdmin,
} from './closure-helpers'

/**
 * Checklist **E2E-S10-01/02** 切片（#48 · 纯 UI）
 * admin 发布资料 → 下达任务 → 学习中心完成 → 学习记录 CONFIRMED
 */
test.describe('train dispatch and complete closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('admin dispatch task then learner completes study', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-train-${Date.now()}`
    const materialTitle = `E2E 培训资料 ${label}`
    const taskName = `E2E 学习任务 ${label}`

    await loginAdmin(page)

    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })
    const { taskId } = await createTrainTaskViaUi(page, {
      taskName,
      materialIds: [materialId],
      assignUserIds: [1],
    })

    await page.goto(`/ims/train/study/${taskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByText(taskName)).toBeVisible()

    const progressResp = page.waitForResponse(
      (r) =>
        r.url().includes(`/train/task/${taskId}/progress`) &&
        r.request().method() === 'PUT' &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '标记当前资料已学完' }).click()
    const progBody = (await (await progressResp).json()) as { code: number }
    expect(progBody.code).toBe(0)

    const confirmResp = page.waitForResponse(
      (r) =>
        r.url().includes(`/train/task/${taskId}/confirm`) &&
        r.request().method() === 'POST' &&
        r.status() === 200,
    )
    await page.getByRole('button', { name: '完成确认' }).click()
    const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { confirmStatus?: string } }
    expect(confirmBody.code).toBe(0)
    expect(confirmBody.data?.confirmStatus).toBe('CONFIRMED')

    await expect(page.getByText('学习已完成 · CONFIRMED')).toBeVisible({ timeout: 10_000 })

    await page.goto('/ims/train/task')
    await expect(page.locator('h1')).toHaveText('学习任务管理')
    const taskRow = page.locator('tr', { hasText: taskName })
    await expect(taskRow).toBeVisible()
    await taskRow.getByRole('button', { name: '学习记录' }).click()
    await expect(page.getByText('CONFIRMED')).toBeVisible({ timeout: 10_000 })

    expect(pageErrors).toEqual([])
  })
})
