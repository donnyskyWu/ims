import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('certificate smoke S6 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then certificate registry list', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/corp/resource/certificate', '证件管理')
  })
})
