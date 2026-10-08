import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('flow smoke narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then flow page heading and instance table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/flow', '流程管理')
  })
})
