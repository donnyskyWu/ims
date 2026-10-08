import { test, expect } from '@playwright/test'
import { smokeListAfterLogin } from './smoke-helpers'

const l3 =
  process.env.IMS_DINGTALK_L3 === '1' &&
  !!process.env.IMS_DINGTALK_CLIENT_ID &&
  !!process.env.IMS_DINGTALK_CLIENT_SECRET

test.describe('org DingTalk L3 (gated)', () => {
  test.skip(!l3, 'Requires IMS_DINGTALK_L3=1 and OAuth credentials in env')

  test('org sync page loads after login (L3 smoke)', async ({ page }) => {
    await smokeListAfterLogin(page, '/ims/auth/org', '组织架构同步')

    const apiBase = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:18080'
    const login = await page.request.post(`${apiBase}/admin-api/ims/auth/login`, {
      data: { username: 'admin', password: 'Admin@123' },
    })
    expect(login.ok()).toBeTruthy()
    const body = await login.json()
    const token = body?.data?.accessToken as string
    expect(token).toBeTruthy()
    const events = await page.request.get(`${apiBase}/admin-api/ims/auth/org/events`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(events.ok()).toBeTruthy()
  })
})
