import path from 'node:path'
import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'SCHED-COOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/collect-scheduler-147'

test.describe('采集任务调度与失败重试', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('下次执行、健康、启停与失败日志重试', async ({ page }) => {
    test.setTimeout(120_000)
    const stamp = Date.now().toString(36)
    const name = `E2E调度${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')
    await expect(page.locator('[data-testid=dy-company] option', { hasText: 'E2E抖音采集公司' })).toHaveCount(1)
    await page.getByTestId('dy-nickname').fill(name)
    await page.getByTestId('dy-company').selectOption({ label: 'E2E抖音采集公司' })
    await page.getByTestId('dy-ip-group').selectOption({ label: 'E2E抖音采集组' })
    await page.getByTestId('dy-platform-id').fill(`DY_SCH_${stamp}`)
    await page.getByTestId('dy-credential').fill(SECRET)
    await page.getByTestId('dy-save').click()
    await expect(page.getByTestId('dy-notice')).toContainText('已保存')
    await expect(page.locator('body')).not.toContainText(SECRET)

    await page.goto('/ims/collect/task')
    await expect(page.locator('h1')).toContainText('采集任务')
    await page.locator('input[placeholder="任务名"]').fill(name)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const row = page.locator('tr', { hasText: name })
    await expect(row).toHaveCount(1)
    await expect(row.getByTestId('task-health')).toHaveText('未绑定')
    await expect(row.getByTestId('task-next-run')).toContainText(/\d{4}-\d{2}-\d{2}/)
    await expect(row.getByTestId('task-status')).toHaveText('启用')
    await expect(row.getByTestId('task-stop')).toBeVisible()
    await page.screenshot({ path: path.join(SHOTS, '01-schedule-health.png'), fullPage: true })

    const stopResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/') && r.url().endsWith('/stop') && r.request().method() === 'POST',
    )
    await row.getByTestId('task-stop').click()
    expect(((await (await stopResp).json()) as { code: number }).code).toBe(0)
    await expect(row.getByTestId('task-status')).toHaveText('停用')
    await expect(row.getByTestId('task-next-run')).toHaveText('已停止，暂无下次执行')
    await expect(row.getByTestId('task-start')).toBeVisible()
    await page.screenshot({ path: path.join(SHOTS, '02-stopped.png'), fullPage: true })

    const startResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/') && r.url().endsWith('/start') && r.request().method() === 'POST',
    )
    await row.getByTestId('task-start').click()
    expect(((await (await startResp).json()) as { code: number }).code).toBe(0)
    await expect(row.getByTestId('task-status')).toHaveText('启用')
    await expect(row.getByTestId('task-next-run')).toContainText(/\d{4}-\d{2}-\d{2}/)
    await row.getByRole('button', { name: '编辑' }).click()
    await expect(page.getByTestId('task-monitor')).toContainText('健康')
    await expect(page.getByTestId('task-monitor')).toContainText('未绑定')
    await page.screenshot({ path: path.join(SHOTS, '03-started-monitor.png'), fullPage: true })
    await page.getByRole('button', { name: '取消' }).click()

    const runResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/') && r.url().endsWith('/run') && r.request().method() === 'POST',
    )
    await row.getByTestId('task-run').click()
    expect(((await (await runResp).json()) as { code: number }).code).toBe(0)
    await expect(page.locator('h1')).toContainText('采集日志')
    const failed = page.locator('tbody tr').first()
    await expect(failed).toContainText('失败')
    await expect(failed.getByTestId('log-retry-count')).toHaveText('0')
    await expect(page.getByTestId('log-retry-detail')).toBeVisible()
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: path.join(SHOTS, '04-failed-log.png'), fullPage: true })

    const retryResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/') && r.url().endsWith('/run') && r.request().method() === 'POST',
    )
    await page.getByTestId('log-retry-detail').click()
    expect(((await (await retryResp).json()) as { code: number }).code).toBe(0)
    const retried = page.locator('tbody tr').first()
    await expect(retried.getByTestId('log-retry-count')).toHaveText('1')
    await expect(retried).toContainText('失败')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: path.join(SHOTS, '05-retry-count.png'), fullPage: true })
  })
})
