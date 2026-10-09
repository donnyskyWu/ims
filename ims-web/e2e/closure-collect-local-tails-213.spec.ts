import path from 'node:path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * 切片 #213（acceptance · 纯 UI）
 * 任务 / 外部账号 / 关键词列表的筛选空态。
 * 不改下次执行文案，也不改抖音探活。
 */
const SHOTS = '/opt/cursor/artifacts/collect-local-tails-213'

test.describe('collect list filter tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('keyword, account, and task filters explain empty local results', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = `f213-${Date.now().toString(36)}`

    await loginAdmin(page)

    await page.goto('/ims/collect/task')
    await expect(page.locator('h1')).toHaveText('采集任务')
    await page.getByTestId('task-name').fill(`missing-${stamp}`)
    await page.getByTestId('task-query').click()
    await expect(page.getByTestId('task-empty')).toContainText('没有符合筛选的采集任务')
    await page.screenshot({ path: path.join(SHOTS, '01-task-filter-empty.png'), fullPage: true })

    await page.getByTestId('task-reset').click()
    await page.getByTestId('task-status-filter').selectOption({ label: '运行中' })
    await page.getByTestId('task-query').click()
    await expect(page.getByTestId('task-empty')).toContainText('本地调度没有「运行中」任务')
    await expect(page.getByTestId('task-empty-hint')).toContainText('启用和停用')
    await expect(page.getByTestId('task-empty-hint')).toContainText('本地桩')
    await page.screenshot({ path: path.join(SHOTS, '02-task-running-empty.png'), fullPage: true })

    await page.getByTestId('task-reset').click()
    await page.getByTestId('task-platform').selectOption({ label: '多平台' })
    const ensureResp = page.waitForResponse(
      (r) => r.url().includes('/collect/task/ensure-external-unified') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '确保外部统一任务' }).click()
    expect((await (await ensureResp).json()).code).toBe(0)
    await page.getByTestId('task-query').click()
    const externalRow = page.locator('tr', { hasText: '外部竞品统一任务' })
    await expect(externalRow).toBeVisible()
    await expect(externalRow).toContainText('外部')
    await expect(externalRow.getByTestId('task-next-run')).not.toHaveText('尚未排期')
    await page.screenshot({ path: path.join(SHOTS, '03-task-multi-platform.png'), fullPage: true })

    await page.goto('/ims/collect/external/keyword')
    await expect(page.locator('h1')).toHaveText('竞品关键字配置')
    await page.getByTestId('kw-create').click()
    const kwDrawer = page.locator('.drawer.on')
    await kwDrawer.getByTestId('kw-form-keyword').fill(stamp)
    await kwDrawer.getByTestId('kw-form-collect').selectOption({ label: '否' })
    await kwDrawer.getByTestId('kw-save').click()
    await expect(page.locator('tr', { hasText: stamp })).toBeVisible()

    await page.getByTestId('kw-keyword').fill(stamp)
    await page.getByTestId('kw-collect-filter').selectOption({ label: '只看采集' })
    await page.getByTestId('kw-query').click()
    await expect(page.getByTestId('kw-empty')).toContainText('暂无关键词')
    await expect(page.getByTestId('kw-empty-hint')).toContainText('本地桩不需要平台 Cookie')
    await page.screenshot({ path: path.join(SHOTS, '04-keyword-collect-filter-empty.png'), fullPage: true })

    await page.getByTestId('kw-collect-filter').selectOption({ label: '只看不采集' })
    await page.getByTestId('kw-query').click()
    const kwRow = page.locator('tr', { hasText: stamp })
    await expect(kwRow).toBeVisible()
    await expect(kwRow.getByTestId('kw-collect')).toHaveAttribute('aria-pressed', 'false')
    await page.screenshot({ path: path.join(SHOTS, '05-keyword-collect-off.png'), fullPage: true })

    await page.goto('/ims/collect/external/account')
    await expect(page.locator('h1')).toHaveText('竞品账号配置')
    await page.getByTestId('acct-name').fill(`missing-${stamp}`)
    await page.getByTestId('acct-query').click()
    await expect(page.getByTestId('acct-empty')).toContainText('没有符合筛选的外部账号')
    await page.screenshot({ path: path.join(SHOTS, '06-account-filter-empty.png'), fullPage: true })

    await page.getByTestId('acct-reset').click()
    await page.getByTestId('acct-create').click()
    const acctDrawer = page.locator('.drawer.on')
    await acctDrawer.getByTestId('acct-form-name').fill(stamp)
    await acctDrawer.getByTestId('acct-form-id').fill(`id-${stamp}`)
    await acctDrawer.getByTestId('acct-form-collect').selectOption({ label: '否' })
    await acctDrawer.getByTestId('acct-save').click()
    await expect(page.locator('tr', { hasText: stamp })).toBeVisible()

    await page.getByTestId('acct-name').fill(stamp)
    await page.getByTestId('acct-collect').selectOption({ label: '只看采集' })
    await page.getByTestId('acct-query').click()
    await expect(page.getByTestId('acct-empty')).toContainText('没有打开采集的外部账号')
    await expect(page.getByTestId('acct-empty-hint')).toContainText('本地桩也不连快手或抖音')
    await page.screenshot({ path: path.join(SHOTS, '07-account-collect-filter-empty.png'), fullPage: true })

    await page.getByTestId('acct-collect').selectOption({ label: '只看不采集' })
    await page.getByTestId('acct-query').click()
    const acctRow = page.locator('tr', { hasText: stamp })
    await expect(acctRow).toBeVisible()
    await expect(acctRow.getByTestId('acct-collect-cell')).toHaveText('否')
    await expect(acctRow).toContainText('启用')
    await page.screenshot({ path: path.join(SHOTS, '08-account-collect-off.png'), fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
