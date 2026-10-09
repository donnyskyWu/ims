import { defineConfig } from '@playwright/test'

function e2eWorkers(): number {
  const raw = (process.env.IMS_E2E_WORKERS || '2').trim()
  const count = Number(raw)
  if (!Number.isFinite(count) || count < 1) return 2
  return Math.floor(count)
}

function e2eRetries(): number {
  const raw = (process.env.IMS_E2E_RETRIES ?? '1').trim()
  const count = Number(raw)
  if (!Number.isFinite(count) || count < 0) return 1
  return Math.floor(count)
}

export default defineConfig({
  testDir: './e2e',
  testIgnore:
    process.env.IMS_DINGTALK_L3 === '1' ? [] : ['**/dingtalk-org-l3.spec.ts'],
  timeout: 60_000,
  // 默认 2。IMS_E2E_WORKERS=1 退回单 worker（多路登录曾触发 ims_login_guard 锁定 admin，#23）。
  workers: e2eWorkers(),
  // 失败自动再跑 1 次。IMS_E2E_RETRIES=0 可关掉。
  retries: e2eRetries(),
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:6173',
    headless: true,
  },
})
