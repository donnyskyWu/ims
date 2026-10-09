import fs from 'node:fs'
import { test, expect } from '@playwright/test'

/**
 * #234 local tails: template-domain empty, start-form validation, businessKey replay,
 * and the approve drawer (empty form + comment length). No /admin-api seeding.
 */
const shots = '/opt/cursor/artifacts'

async function shot(page: import('@playwright/test').Page, name: string) {
  if (!fs.existsSync(shots)) fs.mkdirSync(shots, { recursive: true })
  await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true })
}

test.describe('flow form edges closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('domain empty, start limits, idempotent replay, approve form', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    const uniq = `e2e-flow-234-${Date.now()}`
    const title = `E2E 表单边角 ${uniq}`

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '流程模板' }).click()
    const tplTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '模板编码' }) })
    await expect(tplTable.locator('tbody tr').first()).toBeVisible({ timeout: 15_000 })
    const tplForm = page.locator('form.qbar')
    await tplForm.locator('select').nth(0).selectOption('COMMON')
    await tplForm.getByRole('button', { name: '查询' }).click()
    const tplEmpty = page.getByTestId('flow-template-empty')
    await expect(tplEmpty).toBeVisible({ timeout: 15_000 })
    await expect(tplEmpty).toContainText('该业务域暂无模板')
    await expect(tplEmpty).toContainText('换一个业务域')
    await shot(page, 'flow-234-template-domain-empty')

    let startPosts = 0
    page.on('request', (req) => {
      if (req.method() === 'POST' && req.url().includes('/flow/instance')) startPosts += 1
    })

    await page.getByRole('button', { name: '发起流程' }).click()
    const drawer = page.locator('aside.drawer.on')
    await expect(drawer.getByTestId('flow-start-idem-hint')).toContainText('沿用原单')
    await drawer.getByTestId('flow-start-submit').click()
    await expect(drawer.getByTestId('flow-start-msg')).toContainText('请填写标题')
    expect(startPosts).toBe(0)

    await drawer.getByTestId('flow-start-title').fill('标'.repeat(257))
    await drawer.getByTestId('flow-start-submit').click()
    await expect(drawer.getByTestId('flow-start-msg')).toContainText('标题不能超过 256 字')
    expect(startPosts).toBe(0)

    await drawer.getByTestId('flow-start-title').fill(title)
    await drawer.getByTestId('flow-start-key').fill('k'.repeat(65))
    await drawer.getByTestId('flow-start-submit').click()
    await expect(drawer.getByTestId('flow-start-msg')).toContainText('businessKey 不能超过 64 字')
    expect(startPosts).toBe(0)
    await shot(page, 'flow-234-start-validation')

    await drawer.getByTestId('flow-start-key').fill(uniq)
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('flow-start-submit').click()
    const started = await startResp
    const startBody = (await started.json()) as { code: number; data?: { instanceNo?: string } }
    expect(startBody.code).toBe(0)
    const instanceNo = startBody.data?.instanceNo ?? ''
    expect(instanceNo.length).toBeGreaterThan(0)
    await expect(drawer).toBeHidden()

    await page.getByRole('button', { name: '发起流程' }).click()
    const again = page.locator('aside.drawer.on')
    await again.getByTestId('flow-start-title').fill(`${title} 重放`)
    await again.getByTestId('flow-start-key').fill(uniq)
    await again.getByTestId('flow-start-submit').click()
    await expect(again.getByTestId('flow-start-msg')).toContainText('沿用原单')
    await expect(again.getByTestId('flow-start-msg')).toContainText(instanceNo)
    await expect(again.getByTestId('flow-start-msg')).toContainText('未新建')
    await expect(again).toBeVisible()
    await shot(page, 'flow-234-idempotent')
    await again.getByRole('button', { name: '取消' }).click()

    await page.getByRole('button', { name: '我的待办' }).click()
    const todoTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: 'SLA 截止' }) })
    const seedRow = todoTable.locator('tbody tr').filter({ hasText: '部门负责人审批' }).first()
    await expect(seedRow).toBeVisible({ timeout: 15_000 })
    await seedRow.getByText('通过', { exact: true }).click()
    const emptyApprove = page.getByTestId('flow-approve-form-empty')
    await expect(emptyApprove).toContainText('暂无补充表单')
    await shot(page, 'flow-234-approve-empty-form')
    await page.getByTestId('flow-approve-cancel').click()
    await expect(page.locator('aside.drawer.on')).toHaveCount(0)

    const ownRow = todoTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(ownRow).toBeVisible()
    let handlePuts = 0
    page.on('request', (req) => {
      if (req.method() === 'PUT' && req.url().includes('/flow/task/') && req.url().includes('/handle')) handlePuts += 1
    })
    await ownRow.getByText('通过', { exact: true }).click()
    const approve = page.locator('aside.drawer.on')
    await expect(approve.getByTestId('flow-approve-form')).toContainText(title)
    await approve.getByTestId('flow-approve-comment').fill('意'.repeat(513))
    await approve.getByTestId('flow-approve-confirm').click()
    await expect(approve.getByTestId('flow-approve-msg')).toContainText('审批意见不能超过 512 字')
    expect(handlePuts).toBe(0)
    await shot(page, 'flow-234-approve-comment-limit')
    await approve.getByTestId('flow-approve-cancel').click()
    await expect(ownRow).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
