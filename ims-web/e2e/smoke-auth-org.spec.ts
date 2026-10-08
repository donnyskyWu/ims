import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('auth org smoke S1 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then auth/org heading and org table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/auth/org', '组织架构同步')
  })
})
