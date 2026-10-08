import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('live smoke S2 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then live/sessions heading and session table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/live/sessions', '直播管理')
  })
})
