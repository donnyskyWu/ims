import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('train smoke S10 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then train/task heading and table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/train/task', '学习任务管理')
  })
})
