import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('content smoke S7 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then content list heading and table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/content/list', '内容管理')
  })
})
