import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

const SECRET = 'DYCOOKIE-PLAINTEXT-SHOULD-NOT-LEAK'
const SHOTS = '/opt/cursor/artifacts/collect-douyin-probe-178'

test.describe('抖音探活空态与凭证清空', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('未绑定探活、清空凭证后不调用采集器', async ({ page }) => {
    test.setTimeout(120_000)
    const stamp = Date.now().toString(36)
    const platformId = `DY_PROBE_E2E_${stamp}`
    const name = `E2E抖音探活${stamp}`
    await loginAdmin(page)
    await page.goto('/ims/collect/douyin')
    await expect(page.locator('h1')).toContainText('抖音内部账号采集')

    await page.getByTestId('dy-nickname').fill(name)
    await page.getByTestId('dy-company').selectOption({ label: 'E2E抖音采集公司' })
    await page.getByTestId('dy-ip-group').selectOption({ label: 'E2E抖音采集组' })
    await page.getByTestId('dy-platform-id').fill(platformId)
    await page.getByTestId('dy-credential').fill(SECRET)
    await page.getByTestId('dy-save').click()
    await expect(page.getByTestId('dy-notice')).toContainText('已保存')
    await expect(page.getByTestId('dy-notice')).not.toContainText(SECRET)

    const row = page.locator(`[data-testid="dy-row-${platformId}"]`)
    await row.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('未绑定')
    await expect(page.getByTestId('dy-notice')).toContainText('请先导入')
    await expect(row.getByTestId('dy-health')).toContainText('未绑定')
    await expect(row.getByTestId('dy-probe-at')).toHaveText('尚未探活')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/01-unbound-probe.png`, fullPage: true })

    await row.getByRole('button', { name: '导入 Collector' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('已导入 Collector')
    await row.getByRole('button', { name: '测试连接' }).click()
    await expect(row.getByTestId('dy-health')).toContainText('连接正常')
    await expect(row.getByTestId('dy-probe-at')).not.toHaveText('尚未探活')

    await row.getByRole('button', { name: '编辑' }).click()
    await page.getByTestId('dy-clear-credential').click()
    await expect(page.getByTestId('dy-notice')).toContainText('凭证已清空')
    await expect(row.getByTestId('dy-health')).toContainText('未探活')
    await expect(row.getByTestId('dy-mask')).toContainText('未配置')
    await expect(row.getByTestId('dy-probe-at')).toHaveText('尚未探活')
    await row.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('dy-notice')).toContainText('凭证未配置')
    await expect(row.getByTestId('dy-health')).toContainText('未探活')
    await expect(page.locator('body')).not.toContainText(SECRET)
    await page.screenshot({ path: `${SHOTS}/02-cleared-probe.png`, fullPage: true })

    await page.goto('/ims/corp/account/douyin')
    await page.locator('input[placeholder="账号编号/昵称"]').fill(name)
    await page.getByRole('button', { name: '查询' }).click()
    const acct = page.locator('.tbl-wrap tbody tr').filter({ hasText: name })
    await acct.getByRole('button', { name: '详情' }).click()
    await page.getByRole('button', { name: '采集' }).click()
    await expect(page.getByTestId('dy-tab-health')).toContainText('未探活')
    await expect(page.getByTestId('dy-tab-probe')).toHaveText('尚未探活')
    await expect(page.getByTestId('dy-tab-mask')).toContainText('未配置')
    await page.screenshot({ path: `${SHOTS}/03-account-tab-empty.png`, fullPage: true })

    await page.getByTestId('dy-tab-credential').fill(SECRET)
    await page.getByTestId('dy-tab-save-credential').click()
    await expect(page.getByTestId('dy-tab-collect-msg')).toContainText('未探活')
    await expect(page.getByTestId('dy-tab-mask')).toContainText('****')
    await expect(page.locator('.drawer.on')).not.toContainText(SECRET)
    await page.getByRole('button', { name: '测试连接' }).click()
    await expect(page.getByTestId('dy-tab-health')).toContainText('连接正常')
    await expect(page.getByTestId('dy-tab-probe')).toContainText('成功')
    await expect(page.getByTestId('dy-tab-collect-msg')).toContainText('探活成功')
    await page.screenshot({ path: `${SHOTS}/04-account-tab-probed.png`, fullPage: true })
  })
})
