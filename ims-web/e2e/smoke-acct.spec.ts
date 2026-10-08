import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('corp account smoke S4 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then douyin account pool list', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/corp/account/douyin', '抖音')
  })
})
