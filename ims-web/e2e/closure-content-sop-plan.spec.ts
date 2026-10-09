import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createDraftPlanViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-101-screenshots'

/**
 * Checklist 切片 #101 · CONTENT S1（acceptance · 纯 UI）
 * Given: SOP 管理可进
 * When: DAG 加节点并保存 → 编辑生成新版本 → 逻辑删除；计划表单创建草稿
 * Then: 列表可见 v2；删除后该版本消失；计划行 DRAFT
 */
test.describe('content sop plan S1 closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('dag save, new version, logical delete, and draft plan', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-s1-${Date.now()}`
    const sopName = `E2E SOP ${label}`
    const nodeName = `脚本-${label}`
    const planName = `E2E 计划 ${label}`

    await loginAdmin(page)
    await page.goto('/ims/content/sop')
    await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })
    await expect(page.getByText('无 SOP 审核页')).toBeVisible()

    await page.getByRole('button', { name: '新增模板' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '新增 SOP 模板' })
    await expect(drawer).toBeVisible()
    await drawer.locator('.fld').filter({ hasText: '模板名称' }).locator('input').fill(sopName)
    await drawer.locator('.fld').filter({ hasText: '首节点名称' }).locator('input').fill(nodeName)
    await drawer.getByRole('button', { name: '内容发布' }).click()
    await expect(drawer.locator('[data-testid="sop-dag-node"]')).toHaveCount(2)

    const firstNode = drawer.locator('[data-testid="sop-dag-node"]', { hasText: nodeName })
    await firstNode.click()
    const cycleBox = drawer.locator('.dag-pred', { hasText: '内容发布' }).locator('input[type="checkbox"]')
    await cycleBox.check()
    await expect(drawer.getByTestId('sop-dag-error')).toHaveText('DAG 存在环')
    await page.screenshot({ path: `${SHOTS}/01-sop-dag-cycle.png` })
    await cycleBox.uncheck()
    await expect(drawer.getByTestId('sop-dag-error')).toHaveCount(0)

    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/sop') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByRole('button', { name: '保存', exact: true }).click()
    const created = (await (await createResp).json()) as { code: number; data?: { id?: number; version?: number } }
    expect(created.code).toBe(0)
    expect(created.data?.version).toBe(1)
    const sopId = created.data?.id
    expect(sopId).toBeTruthy()

    const row = page.locator('tr', { hasText: sopName }).filter({ hasText: 'v1' })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('ENABLED')
    await page.screenshot({ path: `${SHOTS}/02-sop-list.png` })

    await row.getByRole('button', { name: '节点' }).click()
    const nodeDrawer = page.locator('.drawer.on').filter({ hasText: '节点 ·' })
    await expect(nodeDrawer).toContainText('内容发布')
    await expect(nodeDrawer).toContainText(nodeName)
    await page.screenshot({ path: `${SHOTS}/03-sop-nodes.png` })
    await nodeDrawer.locator('.dr-x').click()
    await expect(nodeDrawer).not.toBeVisible()

    const nodesResp = page.waitForResponse(
      (r) => r.url().includes(`/content/sop/${sopId}/nodes`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await row.getByRole('button', { name: '编辑' }).click()
    await nodesResp
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑 SOP 模板' })
    await expect(editDrawer).toContainText('保存生成 v2')
    await expect(editDrawer.locator('[data-testid="sop-dag-node"]')).toHaveCount(2)
    await editDrawer.getByRole('button', { name: '普通节点' }).click()
    const putResp = page.waitForResponse(
      (r) => r.url().includes(`/content/sop/${sopId}`) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存新版本' }).click()
    const updated = (await (await putResp).json()) as { code: number; data?: { version?: number; id?: number } }
    expect(updated.code).toBe(0)
    expect(updated.data?.version).toBe(2)
    const v2id = updated.data?.id

    const v2 = page.locator('tr', { hasText: sopName }).filter({ hasText: 'v2' })
    await expect(v2).toBeVisible({ timeout: 15_000 })
    await expect(v2).toContainText('ENABLED')
    await expect(v2).toContainText('3')
    const v1 = page.locator('tr', { hasText: sopName }).filter({ hasText: 'v1' })
    await expect(v1).toContainText('DISABLED')
    await page.screenshot({ path: `${SHOTS}/04-sop-v2.png` })

    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId: v2id!, ipGroupId })
    await expect(page.locator('tr', { hasText: planName })).toContainText('DRAFT')
    await page.screenshot({ path: `${SHOTS}/05-plan-draft.png` })

    await page.goto('/ims/content/sop')
    const v2again = page.locator('tr', { hasText: sopName }).filter({ hasText: 'v2' })
    await expect(v2again).toBeVisible({ timeout: 15_000 })
    const delResp = page.waitForResponse(
      (r) => r.url().includes(`/content/sop/${v2id}`) && r.request().method() === 'DELETE',
    )
    await v2again.getByRole('button', { name: '删除' }).click()
    const deleted = (await (await delResp).json()) as { code: number }
    expect(deleted.code).toBe(0)
    await expect(page.locator('tr', { hasText: sopName }).filter({ hasText: 'v2' })).toHaveCount(0)
    await expect(page.locator('tr', { hasText: sopName }).filter({ hasText: 'v1' })).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/06-sop-deleted.png` })

    expect(pageErrors).toEqual([])
  })
})
