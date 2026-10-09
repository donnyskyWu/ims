import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { execFileSync } from 'child_process'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-194-screenshots'
const PARENT = '19410'
const CHILD = '19411'
const R2 = 'e2e_org_r2'

function deliver() {
  const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../ims-backend')
  const env = { ...process.env }
  delete env.IMS_USE_CLOUD_DB
  env.IMS_MYSQL_HOST = '127.0.0.1'
  const bin = process.env.PYTHON || 'python3'
  execFileSync(bin, ['-m', 'app.org_dept_edge_seed'], { cwd: backend, env, encoding: 'utf8' })
}

async function shot(page: Page, name: string) {
  fs.mkdirSync(shotDir, { recursive: true })
  await page.screenshot({ path: path.join(shotDir, name), fullPage: true })
}

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

async function openOrg(page: Page) {
  await page.goto('/ims/auth/org')
  await expect(page.locator('h1')).toHaveText('组织架构同步', { timeout: 15_000 })
  await expect(page.getByTestId('org-report')).toBeVisible()
}

async function searchDept(page: Page, deptId: string) {
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/auth/org/users') && r.request().method() === 'GET' && r.ok(),
  )
  await page.getByTestId('org-dept-id').fill(deptId)
  await page.getByTestId('org-user-keyword').fill('')
  await page.getByTestId('org-user-search').click()
  await listResp
}

test.describe('org dept scope and local stubs', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('exact dept, empty states, and local replay', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    deliver()
    await loginAdmin(page)
    await openOrg(page)
    await expect(page.getByTestId('org-report-empty')).toBeVisible()
    await expect(page.getByTestId('org-dept-exact')).toHaveText('精确匹配该部门，不含下级')
    await shot(page, '01-report-empty.png')

    await searchDept(page, PARENT)
    await expect(page.getByTestId('org-user-row').filter({ hasText: '部门边父' })).toBeVisible()
    await expect(page.getByTestId('org-user-row').filter({ hasText: '部门边子' })).toHaveCount(0)
    await shot(page, '02-parent-dept-exact.png')

    await searchDept(page, '19499')
    await expect(page.getByTestId('org-user-empty')).toContainText('该部门没有已同步人员')
    await expect(page.getByTestId('org-user-empty')).toContainText('不含下级')
    await shot(page, '03-dept-empty.png')

    await page.locator('.tab', { hasText: '同步事件' }).click()
    const blank = page.getByTestId('org-event-row').filter({ hasText: 'e2e-org-194-blank' })
    await expect(blank).toBeVisible()
    await blank.getByTestId('org-event-open').click()
    await expect(page.getByTestId('org-event-payload-empty')).toContainText('这条事件没有原文')
    await expect(page.getByTestId('org-event-timeline')).toContainText('入队')
    await shot(page, '04-event-payload-empty.png')
    await page.locator('.drawer.on').getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('org-replay-open').click()
    await page.getByTestId('org-replay-start').fill('2020-01-01T00:00')
    await page.getByTestId('org-replay-end').fill('2020-01-02T00:00')
    const replayResp = page.waitForResponse(
      (r) => r.url().includes('/callback/dingtalk/retry-queue/replay') && r.request().method() === 'POST' && r.ok(),
    )
    await page.getByTestId('org-replay-submit').click()
    await replayResp
    await expect(page.getByTestId('org-replay-empty')).toContainText('该时段没有失败或死信事件')
    await shot(page, '05-replay-empty.png')
    await page.locator('.drawer.on').getByRole('button', { name: '取消' }).click()

    await page.getByTestId('org-local-reconcile').click()
    const reportResp = page.waitForResponse(
      (r) => r.url().includes('/callback/dingtalk/reconcile/report') && r.ok(),
    )
    await page.getByTestId('org-local-confirm').click()
    await reportResp
    await expect(page.getByTestId('org-report-body')).toContainText('差异 0')
    await expect(page.getByTestId('org-report-failures-empty')).toBeVisible()
    await shot(page, '06-local-report.png')

    await logout(page)
    await loginAs(page, R2)
    await openOrg(page)
    await expect(page.getByTestId('org-report-denied')).toContainText('无操作权限')
    await expect(page.getByTestId('org-local-reconcile')).toBeDisabled()
    await expect(page.getByTestId('org-replay-open')).toBeDisabled()
    await expect(page.getByTestId('org-dingtalk-sync')).toBeDisabled()
    await expect(page.getByTestId('org-user-row').filter({ hasText: '部门边父' })).toBeVisible()
    await expect(page.getByTestId('org-user-row').filter({ hasText: '部门边子' })).toHaveCount(0)
    await searchDept(page, CHILD)
    await expect(page.getByTestId('org-user-empty')).toContainText('该部门没有已同步人员')
    await shot(page, '07-r2-dept-denied.png')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
