import path from 'node:path'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const KS_SECRET = 'KSCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const WX_SECRET = 'WXCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/collect-local-tails-195'

test.describe('采集排期空态、快手视频号探活与关键词筛选', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('快手与视频号未绑定、清空凭证后不调用采集器', async ({ page }) => {
    test.setTimeout(180_000)
    const stamp = Date.now().toString(36)
    await loginAdmin(page)

    const ksName = `E2E快手探活${stamp}`
    const ksId = `KS_PROBE_E2E_${stamp}`
    await page.goto('/ims/collect/kuaishou')
    await expect(page.locator('h1')).toContainText('快手内部账号采集')
    await saveKuaishou(page, ksName, ksId)
    const ksRow = page.locator(`[data-testid="ks-row-${ksId}"]`)
    await ksRow.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('ks-notice')).toContainText('未绑定')
    await expect(page.getByTestId('ks-notice')).toContainText('请先导入')
    await expect(ksRow.getByTestId('ks-health')).toContainText('未绑定')
    await expect(ksRow.getByTestId('ks-probe-at')).toHaveText('尚未探活')
    await expect(page.locator('body')).not.toContainText(KS_SECRET)
    await page.screenshot({ path: path.join(SHOTS, '01-kuaishou-unbound-probe.png'), fullPage: true })

    await ksRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('ks-notice')).toContainText('已导入 Collector')
    await ksRow.getByRole('button', { name: '测试连接' }).click()
    await expect(ksRow.getByTestId('ks-health')).toContainText('连接正常')
    await expect(ksRow.getByTestId('ks-probe-at')).not.toHaveText('尚未探活')

    await ksRow.getByRole('button', { name: '编辑' }).click()
    await page.getByTestId('ks-clear-credential').click()
    await expect(page.getByTestId('ks-notice')).toContainText('凭证已清空')
    await expect(ksRow.getByTestId('ks-health')).toContainText('未探活')
    await expect(ksRow.getByTestId('ks-mask')).toContainText('未配置')
    await ksRow.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('ks-notice')).toContainText('凭证未配置')
    await expect(ksRow.getByTestId('ks-health')).toContainText('未探活')
    await expect(page.locator('body')).not.toContainText(KS_SECRET)
    await page.screenshot({ path: path.join(SHOTS, '02-kuaishou-cleared-probe.png'), fullPage: true })

    await page.goto('/ims/corp/account/kuaishou')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(ksName)
    await page.getByRole('button', { name: '查询' }).click()
    const ksAcct = page.locator('.tbl-wrap tbody tr').filter({ hasText: ksName })
    await ksAcct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    await expect(page.getByTestId('ks-tab-health')).toContainText('未探活')
    await expect(page.getByTestId('ks-tab-probe')).toHaveText('尚未探活')
    await expect(page.getByTestId('ks-tab-mask')).toContainText('未配置')
    await page.screenshot({ path: path.join(SHOTS, '03-kuaishou-account-tab.png'), fullPage: true })

    const wxName = `E2E视频号探活${stamp}`
    const wxId = `WX_PROBE_E2E_${stamp}`
    await page.goto('/ims/collect/wechat-channels')
    await expect(page.locator('h1')).toContainText('视频号内部账号采集')
    await saveWechat(page, wxName, wxId)
    const wxRow = page.locator(`[data-testid="wx-row-${wxId}"]`)
    await wxRow.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('wx-notice')).toContainText('请先导入')
    await expect(wxRow.getByTestId('wx-health')).toContainText('未绑定')
    await expect(wxRow.getByTestId('wx-probe-at')).toHaveText('尚未探活')
    await wxRow.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('wx-notice')).toContainText('已导入 Collector')
    await wxRow.getByRole('button', { name: '编辑' }).click()
    await page.getByTestId('wx-clear-credential').click()
    await expect(page.getByTestId('wx-notice')).toContainText('凭证已清空')
    await wxRow.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('wx-notice')).toContainText('凭证未配置')
    await expect(wxRow.getByTestId('wx-health')).toContainText('未探活')
    await expect(page.locator('body')).not.toContainText(WX_SECRET)
    await page.screenshot({ path: path.join(SHOTS, '04-wechat-cleared-probe.png'), fullPage: true })
  })

  test('停止后的排期空态、筛选空表与重复关键词', async ({ page }) => {
    test.setTimeout(180_000)
    const stamp = Date.now().toString(36)
    const name = `E2E排期空态${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/collect/kuaishou')
    await saveKuaishou(page, name, `KS_SCH_EMPTY_${stamp}`)
    const row = page.locator(`[data-testid="ks-row-KS_SCH_EMPTY_${stamp}"]`)
    await expect(row.getByTestId('ks-schedule')).toContainText(/\d{4}-\d{2}-\d{2}/)

    await page.goto('/ims/collect/task')
    await page.locator('input[placeholder="任务名"]').fill(name)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const task = page.locator('tr', { hasText: name })
    await expect(task).toHaveCount(1)
    await expect(task.getByTestId('task-next-run')).toContainText(/\d{4}-\d{2}-\d{2}/)
    await task.getByTestId('task-stop').click()
    await expect(task.getByTestId('task-status')).toHaveText('停用')
    await expect(task.getByTestId('task-next-run')).toHaveText('已停止，暂无下次执行')
    await task.getByRole('button', { name: '编辑' }).click()
    await expect(page.getByTestId('task-monitor')).toContainText('已停止，暂无下次执行')
    await page.screenshot({ path: path.join(SHOTS, '05-schedule-stopped.png'), fullPage: true })
    await page.getByRole('button', { name: '取消' }).click()

    await page.locator('input[placeholder="任务名"]').fill(`没有这个任务${stamp}`)
    const emptyResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await emptyResp
    await expect(page.getByTestId('task-empty')).toContainText('没有符合筛选的采集任务')
    await page.screenshot({ path: path.join(SHOTS, '06-schedule-filter-empty.png'), fullPage: true })

    await page.goto('/ims/collect/kuaishou')
    await expect(page.locator(`[data-testid="ks-row-KS_SCH_EMPTY_${stamp}"]`).getByTestId('ks-schedule')).toHaveText(
      '已停止，暂无下次执行',
    )
    await page.screenshot({ path: path.join(SHOTS, '07-kuaishou-schedule-empty.png'), fullPage: true })

    const keyword = `神鱼空态${stamp}`
    await page.goto('/ims/collect/external/keyword')
    await expect(page.locator('h1')).toContainText('竞品关键字配置')
    await page.getByTestId('kw-keyword').fill(`没有这个词${stamp}`)
    await page.getByTestId('kw-query').click()
    await expect(page.getByTestId('kw-empty')).toContainText('没有符合筛选的关键词')
    await page.screenshot({ path: path.join(SHOTS, '08-keyword-filter-empty.png'), fullPage: true })
    await page.getByTestId('kw-reset').click()

    await page.getByRole('button', { name: '新增关键词' }).click()
    await page.getByTestId('kw-form-keyword').fill(keyword)
    await page.getByTestId('kw-save').click()
    await expect(page.getByTestId('kw-form-msg')).toHaveCount(0)
    await expect(page.locator('td', { hasText: keyword })).toBeVisible()

    await page.getByRole('button', { name: '新增关键词' }).click()
    await page.getByTestId('kw-form-keyword').fill(keyword)
    await page.getByTestId('kw-save').click()
    await expect(page.getByTestId('kw-form-msg')).toContainText('同平台关键词已存在')
    await page.screenshot({ path: path.join(SHOTS, '09-keyword-duplicate.png'), fullPage: true })
  })
})

async function saveKuaishou(page: Page, name: string, platformId: string) {
  await page.getByTestId('ks-nickname').fill(name)
  await page.getByTestId('ks-company').selectOption({ label: 'E2E快手采集公司' })
  await page.getByTestId('ks-ip-group').selectOption({ label: 'E2E快手采集组' })
  await page.getByTestId('ks-platform-id').fill(platformId)
  await page.getByTestId('ks-credential').fill(KS_SECRET)
  await page.getByTestId('ks-save').click()
  await expect(page.getByTestId('ks-notice')).toContainText('已保存')
  await expect(page.locator('body')).not.toContainText(KS_SECRET)
}

async function saveWechat(page: Page, name: string, platformId: string) {
  await page.getByTestId('wx-nickname').fill(name)
  await page.getByTestId('wx-company').selectOption({ label: 'E2E视频号采集公司' })
  await page.getByTestId('wx-ip-group').selectOption({ label: 'E2E视频号采集组' })
  await page.getByTestId('wx-platform-id').fill(platformId)
  await page.getByTestId('wx-credential').fill(WX_SECRET)
  await page.getByTestId('wx-save').click()
  await expect(page.getByTestId('wx-notice')).toContainText('已保存')
  await expect(page.locator('body')).not.toContainText(WX_SECRET)
}
