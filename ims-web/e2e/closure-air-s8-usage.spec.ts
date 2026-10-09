import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * S8 审计用量本地尾巴（acceptance · 纯 UI）。
 * 日志来自启动种子 ims_mcp_log，不经 admin-api 造数。
 * 不覆盖 #160 的 Key 空态、审计筛选条与解冻。
 */
const shotDir = '/opt/cursor/artifacts/air-s8-182'

test.describe('air usage stat and audit detail closure S8', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('usage card, tool drill, detail drawer, page export, retention', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)

    const logged = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    const usage = page.waitForResponse(
      (response) => response.url().includes('/air/usage/stat') && response.request().method() === 'GET',
    )
    await page.goto('/ims/air/cfg?tab=audit')
    expect((await (await logged).json()).code).toBe(0)
    const usageBody = await (await usage).json()
    expect(usageBody.code).toBe(0)
    expect(usageBody.data).toHaveLength(7)

    await expect(page.getByTestId('air-usage-card')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('air-usage-as-of')).toContainText('数据截至')
    await expect(page.getByTestId('air-usage-as-of')).toContainText(/\d{4}-\d{2}-\d{2}/)
    await expect(page.getByTestId('air-usage-retain')).toContainText('180 天')
    await expect(page.getByTestId('air-usage-stub')).toContainText('本地桩')
    await expect(page.getByTestId('air-usage-day')).toHaveCount(7)
    await page.screenshot({ path: `${shotDir}/01-usage-days.png`, fullPage: true })

    const byTool = page.waitForResponse(
      (response) => response.url().includes('/air/usage/stat') && response.url().includes('by=TOOL'),
    )
    await page.getByTestId('air-usage-by-tool').click()
    expect((await (await byTool).json()).code).toBe(0)
    const assemble = page.locator('[data-testid="air-usage-tool"][data-tool="experts.assemble"]')
    await expect(assemble).toBeVisible()
    await expect(assemble).toContainText('组装包下发')
    await expect(assemble).toContainText('网关不执行模型')
    await page.screenshot({ path: `${shotDir}/02-usage-tools.png`, fullPage: true })

    const drilled = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.url().includes('experts.assemble'),
    )
    await assemble.getByTestId('air-usage-drill').click()
    expect((await (await drilled).json()).code).toBe(0)
    await expect(page.getByTestId('air-mcp-drill')).toContainText('experts.assemble')
    const logRow = page.locator('[data-testid="air-mcp-row"][data-tool="experts.assemble"][data-digest="e2e-s8-11"]')
    await expect(logRow).toBeVisible()
    await logRow.click()
    const detail = page.getByTestId('air-mcp-detail')
    await expect(detail).toBeVisible()
    await expect(detail.getByTestId('air-mcp-detail-tool')).toHaveText('experts.assemble')
    await expect(detail.getByTestId('air-mcp-digest')).toHaveText('e2e-s8-11')
    await expect(detail.getByTestId('air-mcp-pack-note')).toContainText('不返回 knowledgeContext')
    await page.screenshot({ path: `${shotDir}/03-log-detail.png`, fullPage: true })
    await detail.getByTestId('air-mcp-detail-close').click()
    await expect(detail).toBeHidden()

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('air-mcp-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('air_mcp_audit_page.xls')
    const filePath = await download.path()
    const xml = fs.readFileSync(filePath!, 'utf8')
    expect(xml).toContain('e2e-s8-11')
    expect(xml).toContain('experts.assemble')
    await expect(page.getByTestId('air-mcp-export-msg')).toHaveText('已导出当前页')
    await expect(page.getByTestId('air-mcp-retain')).toContainText('180 天')
    await page.screenshot({ path: `${shotDir}/04-export-page.png`, fullPage: true })

    await page.getByTestId('air-usage-start').fill('2020-01-01')
    await page.getByTestId('air-usage-end').fill('2020-01-07')
    const rejected = page.waitForResponse((response) => response.url().includes('/air/usage/stat'))
    await page.getByTestId('air-usage-search').click()
    const rejectedBody = await (await rejected).json()
    expect(rejectedBody.code).toBe(1001)
    await expect(page.getByTestId('air-usage-error')).toContainText('180 天')
    await expect(page.getByTestId('air-usage-error')).toContainText('已清理')
    await page.screenshot({ path: `${shotDir}/05-retention.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
