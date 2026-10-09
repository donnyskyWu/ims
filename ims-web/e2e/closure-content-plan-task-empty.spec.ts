import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/content-171'

/**
 * #171 内容本地缺口（acceptance · 纯 UI）
 * 计划/任务空态区分「真的没有」和「筛选落空」；不造计划、不走审核。
 */
test.describe('content plan and task empty states', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('plan and task empty copy follows filters', async ({ page }) => {
    mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const missingName = `e2e-plan-missing-${Date.now()}`

    await loginAdmin(page)

    const planLoad = page.waitForResponse(
      (r) => r.url().includes('/content/plan') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/content/plan')
    await planLoad
    await expect(page.locator('h1')).toHaveText('计划管理', { timeout: 15_000 })
    const planIdle = page.getByTestId('plan-empty')
    if (await planIdle.isVisible()) {
      await expect(planIdle).toContainText('暂无计划')
      await expect(planIdle).toContainText('新增计划')
      await page.screenshot({ path: `${shotDir}/01-plan-empty.png`, fullPage: true })
    }

    await page.getByTestId('plan-name-filter').fill(missingName)
    const planQuery = page.waitForResponse(
      (r) => r.url().includes('/content/plan') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await planQuery
    const planEmpty = page.getByTestId('plan-empty')
    await expect(planEmpty).toBeVisible()
    await expect(planEmpty).toContainText('没有符合条件的计划')
    await expect(planEmpty).toContainText('换个计划名或状态后再查')
    await page.screenshot({ path: `${shotDir}/02-plan-filter-empty.png`, fullPage: true })

    await page.getByRole('button', { name: '重置' }).click()
    await expect(page.getByTestId('plan-name-filter')).toHaveValue('')

    const superviseLoad = page.waitForResponse(
      (r) => r.url().includes('/content/publish/pending') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/content/publish')
    await superviseLoad
    await expect(page.locator('h1')).toHaveText('发布管理', { timeout: 15_000 })
    await expect(page.getByTestId('publish-supervise')).toContainText('督办：待发布')
    await page.screenshot({ path: `${shotDir}/07-publish-supervise.png`, fullPage: true })

    const taskLoad = page.waitForResponse(
      (r) => r.url().includes('/content/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.goto('/ims/content/task')
    await taskLoad
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const mineEmpty = page.getByTestId('task-empty')
    if (await mineEmpty.isVisible()) {
      await expect(mineEmpty).toContainText('暂无我的任务')
      await expect(mineEmpty).toContainText('全部任务')
      await page.screenshot({ path: `${shotDir}/03-task-mine-empty.png`, fullPage: true })
    }

    const allLoad = page.waitForResponse(
      (r) => r.url().includes('/content/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.locator('.tab', { hasText: '全部任务' }).click()
    await allLoad
    const allEmpty = page.getByTestId('task-empty')
    if (await allEmpty.isVisible()) {
      await expect(allEmpty).toContainText('暂无任务')
      await expect(allEmpty).toContainText('启动计划')
      await page.screenshot({ path: `${shotDir}/04-task-all-empty.png`, fullPage: true })
    }

    await page.getByTestId('task-ip-filter').fill('900000171')
    const taskQuery = page.waitForResponse(
      (r) => r.url().includes('/content/task/page') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await taskQuery
    const taskEmpty = page.getByTestId('task-empty')
    await expect(taskEmpty).toBeVisible()
    await expect(taskEmpty).toContainText('当前筛选下暂无任务')
    await expect(taskEmpty).toContainText('清空 IP 组')
    await page.screenshot({ path: `${shotDir}/05-task-filter-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
