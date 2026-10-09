import { mkdirSync } from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin, prepareIpGroupWithAdminMember } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/content-201'

/**
 * #201 · 内容列表/审核/补偿空态、编辑标题与排版空态、SOP 节点只读 SLA、工作任务 SOP 匹配
 * 纯 UI。不改 #152 计划筛选，不重建 #183 文案/视频桩客户端。
 */
test.describe('content production local tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty states, editor edges, and sop node meta', async ({ page }) => {
    test.setTimeout(180_000)
    mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-201-${Date.now()}`
    const title = `E2E 内容尾巴 ${label}`
    const body = `正文尾巴 ${label}`
    const sopName = `E2E SOP 尾巴 ${label}`
    const nodeName = `节点-${label}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })

    await page.getByTestId('content-filter-title').fill(`miss-${label}`)
    const missResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.url().includes(`title=miss-${label}`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('content-filters').getByRole('button', { name: '查询' }).click()
    await missResp
    await expect(page.getByTestId('content-list-empty')).toContainText('没有符合筛选的内容')
    await page.screenshot({ path: `${SHOTS}/01-content-filter-empty.png`, fullPage: true })

    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.getByRole('button', { name: '保存' }).click()
    await expect(createDrawer.getByTestId('content-title-error')).toHaveText('请填写标题')
    await page.screenshot({ path: `${SHOTS}/02-content-title-empty.png`, fullPage: true })

    await createDrawer.getByTestId('content-edit-title').fill(title)
    await createDrawer.locator('.fld').filter({ hasText: '内容类型' }).locator('select').selectOption('ARTICLE')
    await expect(createDrawer.getByTestId('content-ai-layout-need-body')).toBeVisible()
    await createDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(body)
    await expect(createDrawer.getByTestId('content-ai-layout-need-body')).toHaveCount(0)
    await createDrawer.getByRole('button', { name: 'AI 语义排版' }).click()
    await expect(createDrawer.getByTestId('content-ai-layout-empty')).toContainText('尚未预览版式')
    await page.screenshot({ path: `${SHOTS}/03-ai-layout-empty.png`, fullPage: true })

    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const created = (await (await createResp).json()) as { code: number }
    expect(created.code).toBe(0)

    await page.getByTestId('content-filter-reset').click()
    await page.getByTestId('content-filter-title').fill(title)
    const hitResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.url().includes('title=') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('content-filters').getByRole('button', { name: '查询' }).click()
    await hitResp
    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    const detailResp = page.waitForResponse(
      (r) => /\/content\/\d+(\?|$)/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row.getByRole('button', { name: '查看' }).click()
    await detailResp
    const viewDrawer = page.locator('.drawer.on').filter({ hasText: '查看内容' })
    await expect(viewDrawer.getByTestId('content-view-media')).toContainText('未生成')
    await expect(viewDrawer.getByTestId('content-view-layout-empty')).toContainText('未写版式 HTML')
    await expect(viewDrawer.getByTestId('content-layout-body')).toContainText(body)
    await page.screenshot({ path: `${SHOTS}/04-content-view-empty.png`, fullPage: true })
    await viewDrawer.getByRole('button', { name: '关闭' }).click()
    await row.getByRole('button', { name: '提审' }).click()
    await expect(row).not.toContainText('DRAFT', { timeout: 15_000 })

    await page.goto('/ims/content/review')
    await expect(page.locator('h1')).toHaveText('内容审核', { timeout: 15_000 })
    await page.getByTestId('review-filter-title').fill(`miss-${label}`)
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/content/review') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('review-filters').getByRole('button', { name: '查询' }).click()
    await reviewResp
    await expect(page.getByTestId('review-list-empty')).toContainText('暂无待审，没有符合当前标题')
    await page.screenshot({ path: `${SHOTS}/05-review-filter-empty.png`, fullPage: true })

    await page.goto('/ims/content/fb-sync')
    await expect(page.locator('h1')).toHaveText('Football 补偿队列', { timeout: 15_000 })
    await page.getByTestId('fb-sync-filter-status').selectOption('FAILED')
    const syncResp = page.waitForResponse(
      (r) => r.url().includes('/fb-sync/outbox/page') && r.url().includes('syncStatus=FAILED') && r.status() === 200,
    )
    await page.getByTestId('fb-sync-filters').getByRole('button', { name: '查询' }).click()
    await syncResp
    const syncEmpty = page.getByTestId('fb-sync-empty')
    if (await syncEmpty.count()) {
      await expect(syncEmpty).toContainText('没有符合筛选的补偿任务')
    } else {
      await expect(page.locator('tbody tr').first()).toContainText('FAILED')
    }
    await page.screenshot({ path: `${SHOTS}/06-fb-sync-filter.png`, fullPage: true })

    await createSopViaUi(page, { sopName, nodeName })
    const sopRow = page.locator('tr', { hasText: sopName }).first()
    await sopRow.getByRole('button', { name: '节点' }).click()
    const nodeDrawer = page.locator('.drawer.on').filter({ hasText: '节点' })
    await expect(nodeDrawer.getByTestId('sop-node-meta').first()).toContainText('SLA')
    await expect(nodeDrawer.getByTestId('sop-node-meta').first()).toContainText('节点免审')
    await page.screenshot({ path: `${SHOTS}/07-sop-node-meta.png`, fullPage: true })
    await nodeDrawer.locator('.dr-x').click()

    await sopRow.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑 SOP 模板' })
    await expect(editDrawer).toBeVisible()
    await editDrawer.locator('.fld').filter({ hasText: '营销计划' }).locator('select').selectOption('PAID_SALES')
    const putResp = page.waitForResponse(
      (r) => r.url().includes('/content/sop/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存新版本' }).click()
    const updated = (await (await putResp).json()) as { code: number }
    expect(updated.code).toBe(0)

    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await page.goto('/ims/content/work-task')
    await expect(page.locator('h1')).toHaveText('工作任务登记', { timeout: 15_000 })
    await page.locator('input[placeholder="IP 组 id"]').first().fill(String(ipGroupId))
    await page.locator('input[type="date"]').first().fill('2099-03-21')
    const sheetResp = page.waitForResponse(
      (r) => r.url().includes('/content/work-task/sheet') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).first().click()
    await sheetResp
    const firstRow = page.locator('tbody tr').first()
    await firstRow.locator('select').first().selectOption('PAID_SALES')
    const sopSelect = firstRow.getByTestId('wt-sop')
    await expect(sopSelect.locator('option', { hasText: sopName })).toHaveCount(1)
    await expect(firstRow.getByTestId('wt-sop-empty')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/08-work-task-sop-match.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
