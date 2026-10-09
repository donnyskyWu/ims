import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #160 AIR/S8 本地尾巴（acceptance · 纯 UI）。
 * Key 列表空态、审计报表过滤、停用后再启用。
 * 认证失败 10 次冻结与解冻清窗在 pytest（test_air_s8_tails.py）。
 */
const shotDir = '/opt/cursor/artifacts/air-s8-160'

test.describe('air s8 local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('key empty state, freeze then enable, audit filters', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)

    await page.goto('/ims/air/cfg?tab=key')
    await expect(page.locator('h1')).toContainText('模型与提示词')
    const listed = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-search').click()
    expect((await (await listed).json()).code).toBe(0)
    const activeRow = page.locator('tbody tr').filter({ has: page.getByTestId('air-key-freeze') }).first()
    await expect(activeRow).toBeVisible({ timeout: 15_000 })
    const keyCode = ((await activeRow.locator('td').first().innerText()) || '').trim()
    await page.screenshot({ path: `${shotDir}/01-key-list.png`, fullPage: true })

    await activeRow.getByTestId('air-key-freeze').click()
    await expect(page.getByTestId('air-key-action-hint')).toContainText('401')
    await page.screenshot({ path: `${shotDir}/02-freeze-confirm.png`, fullPage: true })
    const frozen = page.waitForResponse(
      (response) => response.url().includes('/freeze') && response.request().method() === 'POST',
    )
    const frozenList = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-action-ok').click()
    expect((await (await frozen).json()).code).toBe(0)
    await frozenList
    const frozenRow = page.locator('tbody tr').filter({ hasText: keyCode })
    await expect(frozenRow.getByTestId('air-key-status-cell')).toContainText('冻结')
    await expect(frozenRow.getByTestId('air-key-status-cell')).toContainText('管理员停用')
    await page.screenshot({ path: `${shotDir}/03-key-frozen.png`, fullPage: true })

    await frozenRow.getByTestId('air-key-unfreeze').click()
    await expect(page.getByTestId('air-key-action-hint')).toContainText('认证失败计数')
    await page.screenshot({ path: `${shotDir}/04-unfreeze-confirm.png`, fullPage: true })
    const opened = page.waitForResponse(
      (response) => response.url().includes('/unfreeze') && response.request().method() === 'POST',
    )
    const openedList = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-action-ok').click()
    expect((await (await opened).json()).code).toBe(0)
    await openedList
    await expect(frozenRow.getByTestId('air-key-status-cell')).toContainText('启用')
    await expect(frozenRow.getByTestId('air-key-freeze')).toBeVisible()

    await page.getByTestId('air-key-user-filter').fill(`no-such-air-user-${Date.now()}`)
    const emptyKeys = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-search').click()
    expect((await (await emptyKeys).json()).data.total).toBe(0)
    await expect(page.getByTestId('air-key-empty')).toContainText('暂无 Key')
    await page.screenshot({ path: `${shotDir}/05-key-empty.png`, fullPage: true })

    const restored = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-reset').click()
    expect((await (await restored).json()).code).toBe(0)
    await expect(page.locator('tbody tr').filter({ hasText: keyCode })).toBeVisible()

    await page.goto('/ims/air/cfg?tab=audit')
    await expect(page.getByTestId('air-mcp-audit')).toBeVisible({ timeout: 15_000 })
    const missingKeyword = `zzz-no-tool-${Date.now()}`
    await page.getByTestId('air-mcp-keyword').fill(missingKeyword)
    const emptyAudit = page.waitForResponse(
      (response) =>
        response.url().includes('/air/mcp/audit-log') &&
        response.url().includes(`keyword=${missingKeyword}`) &&
        response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await emptyAudit).json()).data.total).toBe(0)
    await expect(page.getByTestId('air-mcp-audit')).toContainText('暂无调用日志')
    await page.screenshot({ path: `${shotDir}/06-audit-empty-keyword.png`, fullPage: true })

    const resetAudit = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-reset').click()
    await resetAudit
    await page.getByTestId('air-mcp-tool').selectOption('experts.assemble')
    await page.getByTestId('air-mcp-from').fill('1999-01-01')
    await page.getByTestId('air-mcp-to').fill('1999-01-02')
    const past = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await past).json()).data.total).toBe(0)
    await expect(page.getByTestId('air-mcp-audit')).toContainText('暂无调用日志')

    await page.getByTestId('air-mcp-from').fill('')
    await page.getByTestId('air-mcp-to').fill('1999-01-02')
    await page.getByTestId('air-mcp-search').click()
    await expect(page.getByTestId('air-mcp-filter-error')).toContainText('同时填写')

    const resetAgain = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-reset').click()
    await resetAgain
    await page.getByTestId('air-mcp-tool').selectOption('experts.assemble')
    await page.getByTestId('air-mcp-key').fill('KEY-NO-SUCH-160')
    const noKey = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await noKey).json()).data.total).toBe(0)

    await page.getByTestId('air-mcp-key').fill('')
    const assemble = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await assemble).json()).code).toBe(0)
    const logRow = page.locator('[data-testid="air-mcp-row"][data-tool="experts.assemble"]').first()
    await expect(logRow).toBeVisible()
    await expect(page.getByTestId('air-mcp-hint')).toContainText('不返回 knowledgeContext')
    await page.screenshot({ path: `${shotDir}/07-audit-tool-filter.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
