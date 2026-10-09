import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testIgnore:
    process.env.IMS_DINGTALK_L3 === '1' ? [] : ['**/dingtalk-org-l3.spec.ts'],
  timeout: 60_000,
  // 默认 2。E2E_WORKERS=1 回退单 worker（登录守卫并发时使用）。
  workers: (() => {
    const raw = process.env.E2E_WORKERS
    if (raw === undefined || raw === '') return 2
    const parsed = Number(raw)
    return Number.isFinite(parsed) && parsed >= 1 ? parsed : 2
  })(),
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:6173',
    headless: true,
  },
})
