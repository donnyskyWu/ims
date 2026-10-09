import { defineConfig } from '@playwright/test'

/** 全量默认 2（PO 2026-10-09）。不稳定失败时回退：E2E_WORKERS=1，并在 e2e_result.txt 说明。 */
function e2eWorkers(): number {
  const raw = process.env.E2E_WORKERS
  if (raw == null || raw.trim() === '') return 2
  const n = Number(raw)
  if (!Number.isInteger(n) || n < 1) return 2
  return n
}

export default defineConfig({
  testDir: './e2e',
  testIgnore:
    process.env.IMS_DINGTALK_L3 === '1' ? [] : ['**/dingtalk-org-l3.spec.ts'],
  timeout: 60_000,
  // 各 spec 独立登录；worker 过多仍可能触发 ims_login_guard 锁定 admin。
  // 回退：PowerShell `$env:E2E_WORKERS='1'`；bash `E2E_WORKERS=1`。
  workers: e2eWorkers(),
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:6173',
    headless: true,
  },
})
