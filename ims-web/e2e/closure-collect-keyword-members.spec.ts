import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * 切片 #158（acceptance · 纯 UI）
 * Given: 竞品关键字可开关「是否采集」
 * When: 关闭后看外部统一任务成员，再打开
 * Then: 成员抽屉只在开启采集时出现该关键词；健康空态与日志重试文案可见
 */
const SHOTS = '/opt/cursor/artifacts'

test.describe('collect keyword members closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('keyword collect flag shows in external members', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = `kw158-${Date.now().toString(36)}`
    const missing = `missing-${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/collect/external/keyword')
    await expect(page.locator('h1')).toHaveText('竞品关键字配置')

    await page.getByTestId('kw-keyword').fill(missing)
    await page.getByTestId('kw-query').click()
    await expect(page.getByTestId('kw-empty')).toContainText('暂无关键词')
    await page.screenshot({ path: `${SHOTS}/collect-keyword-empty.png`, fullPage: true })

    await page.getByTestId('kw-reset').click()
    await page.getByTestId('kw-create').click()
    const drawer = page.locator('.drawer.on')
    await expect(drawer).toContainText('新增关键词')
    await drawer.getByTestId('kw-form-keyword').fill(stamp)
    await drawer.getByTestId('kw-form-match').selectOption('CONTAINS')
    await drawer.getByTestId('kw-form-collect').selectOption({ label: '是' })
    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/collect/external/keyword') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('kw-save').click()
    const saveBody = (await (await saveResp).json()) as { code: number; data?: { collectEnabled?: boolean } }
    expect(saveBody.code).toBe(0)
    expect(saveBody.data?.collectEnabled).toBe(true)

    const row = page.locator('tr', { hasText: stamp })
    await expect(row).toBeVisible()
    await expect(row).toContainText('包含')
    await expect(row).toContainText('启用')
    await expect(row.getByTestId('kw-collect')).toHaveAttribute('aria-pressed', 'true')
    await expect(row.getByTestId('kw-updated')).not.toHaveText('—')
    await page.screenshot({ path: `${SHOTS}/collect-keyword-enabled.png`, fullPage: true })

    const offResp = page.waitForResponse(
      (r) => r.url().includes('/collect/external/keyword/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await row.getByTestId('kw-collect').click()
    const offBody = (await (await offResp).json()) as { code: number; data?: { collectEnabled?: boolean } }
    expect(offBody.code).toBe(0)
    expect(offBody.data?.collectEnabled).toBe(false)
    await expect(row.getByTestId('kw-collect')).toHaveAttribute('aria-pressed', 'false')

    await page.goto('/ims/collect/task')
    await expect(page.locator('h1')).toHaveText('采集任务')
    const ensureResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/ensure-external-unified') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '确保外部统一任务' }).click()
    expect((await (await ensureResp).json()).code).toBe(0)
    const externalRow = page.locator('tr', { hasText: '外部统一' }).first()
    await expect(externalRow).toBeVisible()
    await externalRow.getByTestId('collect-external-members').click()
    const members = page.locator('.drawer.on')
    await expect(members).toContainText('外部统一任务成员')
    await expect(members).not.toContainText(stamp)
    await members.getByRole('button', { name: '关闭' }).click()

    await page.goto('/ims/collect/external/keyword')
    await page.getByTestId('kw-keyword').fill(stamp)
    await page.getByTestId('kw-query').click()
    const again = page.locator('tr', { hasText: stamp })
    await expect(again.getByTestId('kw-collect')).toHaveAttribute('aria-pressed', 'false')
    const onResp = page.waitForResponse(
      (r) => r.url().includes('/collect/external/keyword/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await again.getByTestId('kw-collect').click()
    expect((await (await onResp).json()).code).toBe(0)
    await expect(again.getByTestId('kw-collect')).toHaveAttribute('aria-pressed', 'true')

    await page.goto('/ims/collect/task')
    const externalAgain = page.locator('tr', { hasText: '外部统一' }).first()
    await expect(externalAgain).toBeVisible()
    const membersResp = page.waitForResponse(
      (r) => /\/collect\/task\/\d+\/members/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await externalAgain.getByTestId('collect-external-members').click()
    const membersBody = (await (await membersResp).json()) as {
      code: number
      data?: { list?: Array<{ memberName?: string; memberKind?: string }> }
    }
    expect(membersBody.code).toBe(0)
    expect(membersBody.data?.list?.some((item) => item.memberName === `关键词「${stamp}」` && item.memberKind === 'KEYWORD')).toBe(
      true,
    )
    const openDrawer = page.locator('.drawer.on')
    await expect(openDrawer).toContainText(`关键词「${stamp}」`)
    await page.screenshot({ path: `${SHOTS}/collect-external-members.png`, fullPage: true })

    await page.goto('/ims/collect/log')
    await expect(page.locator('h1')).toHaveText('采集日志')
    const health = page.getByTestId('collect-health-rate').or(page.getByTestId('collect-health-empty'))
    await expect(health).toBeVisible()
    await expect(page.locator('th', { hasText: '重试' })).toBeVisible()
    const retryCell = page.getByTestId('collect-log-retry').first()
    if (await retryCell.count()) {
      await expect(retryCell).toHaveText(/尚未重试|已重试|无需重试|—/)
    }
    await page.screenshot({ path: `${SHOTS}/collect-log-retry.png`, fullPage: true })

    await page.goto('/ims/collect/kuaishou')
    await expect(page.locator('h1')).toContainText('快手内部账号采集')
    const healthEmpty = page.getByTestId('ks-health-empty')
    const healthCell = page.getByTestId('ks-health').first()
    if (await healthEmpty.count()) {
      await expect(healthEmpty).toContainText('暂无快手内部账号')
    } else {
      await expect(healthCell).toBeVisible()
      await expect(healthCell).not.toHaveText(/^\s*$/)
    }
    await page.screenshot({ path: `${SHOTS}/collect-kuaishou-health.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
