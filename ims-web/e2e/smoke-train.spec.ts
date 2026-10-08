import { test, expect } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('train smoke S10 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then train/task heading and table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/train/task', '学习任务管理')
  })

  test('login then train/stat finish-rate tab', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    await smokeListAfterLogin(page, '/ims/train/task', '学习任务管理')
    await page.goto('/ims/train/stat')
    await expect(page.locator('h1')).toHaveText('培训统计看板')
    await page.waitForResponse(
      (r) => r.url().includes('/train/stat/finish-rate') && r.status() === 200,
      { timeout: 15_000 },
    )
    await expect(page.locator('[data-testid="train-stat-total-rate"]')).toBeVisible()
    expect(pageErrors).toEqual([])
  })
})
