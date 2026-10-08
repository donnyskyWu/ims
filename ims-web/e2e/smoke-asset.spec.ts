import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('corp asset smoke S5 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then office device list', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/corp/device/office', '办公设备管理')
  })
})
