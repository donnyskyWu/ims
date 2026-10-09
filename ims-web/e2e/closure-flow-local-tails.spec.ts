import fs from 'node:fs'
import { test, expect } from '@playwright/test'

/**
 * #172 local tails: filtered empty states on start/todo lists, and timeout urge edges
 * (blank message and over-256 do not increment remindCount).
 * #188: todo SLA, draft preview, empty reject, and the local DingTalk urge stub.
 * 数据全部来自页面按钮，不直连 /admin-api 造数。
 */
const shots = '/opt/cursor/artifacts'

async function shot(page: import('@playwright/test').Page, name: string) {
  if (!fs.existsSync(shots)) return
  await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true })
}

test.describe('flow local tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filtered empty lists and urge message edges', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '发起流程' }).click()
    const drawer = page.locator('aside.drawer.on')
    await expect(drawer.getByTestId('flow-start-template')).toBeVisible()
    await expect(drawer.getByTestId('flow-start-empty')).toHaveCount(0)
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-start-drawer.png', fullPage: true })
    await drawer.getByRole('button', { name: '取消' }).click()
    await expect(drawer).toBeHidden()

    const miss = `no-such-flow-${Date.now()}`
    await page.locator('input[placeholder="标题/单号"]').fill(miss)
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    const instEmpty = page.getByTestId('flow-instance-empty')
    await expect(instEmpty).toBeVisible({ timeout: 15_000 })
    await expect(instEmpty).toContainText('没有符合条件的流程实例')
    await expect(instEmpty).toContainText('调整标题、单号或状态后再查询')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-instance-empty.png', fullPage: true })

    await page.getByRole('button', { name: '我的待办' }).click()
    await page.getByTestId('flow-todo-domain').selectOption('COMMON')
    await page.getByTestId('flow-todo-qbar').getByRole('button', { name: '查询' }).click()
    const todoEmpty = page.getByTestId('flow-todo-empty')
    await expect(todoEmpty).toBeVisible({ timeout: 15_000 })
    await expect(todoEmpty).toContainText('该业务域暂无待办')
    await expect(todoEmpty).toContainText('换一个业务域')
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-todo-empty.png', fullPage: true })

    await page.getByRole('button', { name: '超时督办' }).click()
    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '提醒次数' }) })
    await expect(timeoutTable).toBeVisible({ timeout: 15_000 })
    const firstRow = timeoutTable.locator('tbody tr').first()
    await expect(firstRow).not.toContainText('暂无')
    const remindCell = firstRow.locator('td').nth(5)
    const before = parseInt((await remindCell.innerText()).trim(), 10)

    await firstRow.getByText('督办', { exact: true }).click()
    const modal = page.getByTestId('flow-urge-modal')
    await expect(modal).toBeVisible()
    await modal.getByTestId('flow-urge-message').fill('   ')
    let urgeCalls = 0
    page.on('request', (req) => {
      if (req.method() === 'PUT' && req.url().includes('/flow/timeout/') && req.url().includes('/urge')) urgeCalls += 1
    })
    await modal.getByTestId('flow-urge-confirm').click()
    await expect(modal.getByTestId('flow-urge-msg')).toContainText('请填写督办说明')
    expect(urgeCalls).toBe(0)
    await expect(remindCell).toHaveText(String(before))

    await modal.getByTestId('flow-urge-message').fill('督'.repeat(257))
    await modal.getByTestId('flow-urge-confirm').click()
    await expect(modal.getByTestId('flow-urge-msg')).toContainText('不能超过 256 字')
    expect(urgeCalls).toBe(0)
    await page.screenshot({ path: '/opt/cursor/artifacts/flow-172-urge-overlong.png', fullPage: true })
    await modal.getByTestId('flow-urge-cancel').click()
    await expect(remindCell).toHaveText(String(before))

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('todo sla, draft preview, empty reject, dingtalk stub', async ({ page }) => {
    const pageErrors: string[] = []
    page.on('pageerror', (err) => pageErrors.push(err.message))
    let promptText = ''
    page.on('dialog', async (d) => {
      if (d.type() === 'prompt') await d.accept(promptText)
      else await d.accept()
    })

    const uniq = `e2e-flow-tail-${Date.now()}`
    const title = `E2E 驳回尾巴 ${uniq}`

    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('Admin@123')
    await page.locator('button[type="submit"]').click()
    await page.waitForURL(/\/ims\//, { timeout: 30_000 })

    await page.goto('/ims/flow')
    await expect(page.locator('h1')).toContainText('流程管理')

    await page.getByRole('button', { name: '我的待办' }).click()
    const todoTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: 'SLA 截止' }) })
    await expect(todoTable).toBeVisible({ timeout: 15_000 })
    await expect(todoTable).toContainText('超时')
    await expect(todoTable).toContainText('临期')
    await shot(page, 'flow-188-todo-sla')

    await page.getByTestId('flow-todo-domain').selectOption('COMMON')
    await page.getByTestId('flow-todo-qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('flow-todo-empty')).toContainText('该业务域暂无待办')
    await shot(page, 'flow-188-todo-empty-domain')
    await page.getByTestId('flow-todo-qbar').getByRole('button', { name: '重置' }).click()

    await page.getByRole('button', { name: '发起流程' }).click()
    const drawer = page.locator('aside.drawer.on')
    await drawer.locator('select').selectOption({ index: 0 })
    await drawer.locator('input[placeholder="formData.title"]').fill(title)
    await drawer.locator('input').nth(1).fill(uniq)
    const startResp = page.waitForResponse(
      (r) => r.url().includes('/flow/instance') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByRole('button', { name: '提交发起' }).click()
    const started = await startResp
    const startBody = (await started.json()) as { code: number; data?: { instanceNo?: string } }
    expect(startBody.code).toBe(0)
    const instanceNo = startBody.data?.instanceNo ?? ''
    expect(instanceNo.length).toBeGreaterThan(0)

    await page.getByRole('button', { name: '我的待办' }).click()
    const todoRow = todoTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(todoRow).toBeVisible({ timeout: 15_000 })
    promptText = ''
    await todoRow.getByTestId('flow-reject').click()
    await page.getByTestId('flow-reject-confirm').click()
    await expect(page.getByTestId('flow-handle-hint')).toContainText('退回建议填写意见')
    await shot(page, 'flow-188-reject-empty-comment')

    await page.getByRole('button', { name: '流程实例' }).click()
    const instTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '状态' }) })
    const instRow = instTable.locator('tbody tr').filter({ hasText: instanceNo }).first()
    await expect(instRow.locator('.tag')).toContainText('已驳回', { timeout: 15_000 })

    await page.getByRole('button', { name: '流程模板' }).click()
    const tplForm = page.locator('form.qbar')
    await tplForm.locator('select').nth(1).selectOption('DRAFT')
    await tplForm.getByRole('button', { name: '查询' }).click()
    const tplTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '模板编码' }) })
    const draftRow = tplTable.locator('tbody tr').filter({ hasText: '开播审批' }).first()
    await expect(draftRow).toBeVisible({ timeout: 15_000 })
    await draftRow.getByText('预览').click()
    const preview = page.getByTestId('flow-template-preview')
    await expect(preview).toContainText('草稿仅可预览，不可发起')
    await expect(preview).toContainText('直属领导审批')
    await shot(page, 'flow-188-draft-preview')
    await preview.getByRole('button', { name: '关闭' }).click()

    await draftRow.getByTestId('flow-draft-try').click()
    await expect(page.getByTestId('flow-draft-hint')).toContainText('1134')
    await expect(page.getByTestId('flow-draft-hint')).toContainText('仅已发布模板可发起新实例')
    await shot(page, 'flow-188-draft-1134')

    await tplForm.locator('select').nth(1).selectOption('DISABLED')
    await tplForm.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('flow-template-empty')).toContainText('暂无停用模板')
    await shot(page, 'flow-188-template-disabled-empty')

    await page.getByRole('button', { name: '超时督办' }).click()
    await page.getByTestId('flow-timeout-template').fill('不存在的模板XYZ')
    await page.locator('form.qbar').getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('flow-timeout-empty')).toContainText('没有符合条件的超时待办')
    await shot(page, 'flow-188-timeout-empty')

    await page.locator('form.qbar').getByRole('button', { name: '重置' }).click()
    const timeoutTable = page.locator('.tbl-wrap table').filter({ has: page.locator('th', { hasText: '提醒次数' }) })
    const firstRow = timeoutTable.locator('tbody tr').first()
    await expect(firstRow).not.toContainText('暂无', { timeout: 15_000 })
    await firstRow.getByText('督办', { exact: true }).click()
    const urge = page.getByTestId('flow-urge-modal')
    await urge.getByTestId('flow-urge-message').fill('E2E 钉钉桩')
    await urge.getByTestId('flow-urge-confirm').click()
    await expect(page.getByTestId('flow-dingtalk-stub')).toContainText('钉钉桩')
    await shot(page, 'flow-188-dingtalk-stub')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
