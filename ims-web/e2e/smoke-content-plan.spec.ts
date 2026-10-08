import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('content plan smoke S1 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then plan page heading and table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/content/plan', '计划管理')
  })
})
