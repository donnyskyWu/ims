import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testIgnore:
    process.env.IMS_DINGTALK_L3 === '1' ? [] : ['**/dingtalk-org-l3.spec.ts'],
  timeout: 60_000,
  // 各 spec 独立登录；多 worker 并发易触发 ims_login_guard 锁定 admin（#23 签收）
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:6173',
    headless: true,
  },
})
