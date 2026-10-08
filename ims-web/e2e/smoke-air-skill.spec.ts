import { test } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

test.describe('air skill smoke S8 narrow', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('login then air/skill heading and table', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/air/skill', '技能库')
  })
})
