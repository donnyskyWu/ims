import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { execFileSync } from 'child_process'
import { test, expect, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-144-screenshots'
const NICK = 'E2E主播小周'
const USER = 'e2e_s1_anchor'
const PASS = 'Admin@123'

/** 外部系统事件模拟。随后断言只走页面。 */
function deliver(phase: string) {
  const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../ims-backend')
  const env = { ...process.env }
  delete env.IMS_USE_CLOUD_DB
  env.IMS_MYSQL_HOST = '127.0.0.1'
  const bin = process.env.PYTHON || 'python3'
  const out = execFileSync(bin, ['-m', 'app.s1_lifecycle_seed', phase], {
    cwd: backend,
    env,
    encoding: 'utf8',
  })
  const line = out.trim().split('\n').filter(Boolean).pop() || '{}'
  return JSON.parse(line) as { phase?: string; username?: string; status?: string }
}

async function logout(page: Page) {
  await page.locator('.rolebtn').click()
  await page.getByText('退出登录', { exact: true }).click()
  await page.waitForURL(/\/login/, { timeout: 20_000 })
}

async function searchOrg(page: Page, keyword: string) {
  await page.goto('/ims/auth/org')
  await expect(page.locator('h1')).toHaveText('组织架构同步', { timeout: 15_000 })
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/auth/org/users') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('org-user-keyword').fill(keyword)
  await page.getByTestId('org-user-search').click()
  await listResp
  const row = page.getByTestId('org-user-row').filter({ hasText: keyword })
  await expect(row).toBeVisible({ timeout: 15_000 })
  return row
}

/** ORG-R3：调岗 24h 缓冲保留原角色，到期后切换为新岗位，工作台可见。 */
test.describe('S1 transfer buffer closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('org page and workbench show the buffer, then only the new position after it ends', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })

    const hired = deliver('hire')
    expect(hired.username).toBe(USER)
    expect(hired.status).toBe('ENABLED')
    const moved = deliver('transfer')
    expect(moved.status).toBe('ENABLED')

    await loginAdmin(page)
    const row = await searchOrg(page, NICK)
    await expect(row.getByTestId('org-user-position')).toHaveText('编导')
    await expect(row.getByTestId('org-user-dept')).toContainText('直播部')
    await expect(row.getByTestId('org-user-roles')).toContainText('主播运营')
    await expect(row.getByTestId('org-user-roles')).toContainText('编导')
    await expect(row.getByTestId('org-user-buffer')).toHaveText('缓冲中')
    await row.getByTestId('org-user-open').click()
    const drawer = page.getByTestId('org-user-drawer')
    await expect(drawer.getByTestId('org-buffer-state')).toHaveText('缓冲中')
    await expect(drawer.getByTestId('org-detail-buffer')).not.toHaveText('—')
    await expect(drawer.getByTestId('org-diff-retained')).toContainText('主播运营')
    await expect(drawer.getByTestId('org-diff-added')).toContainText('编导')
    await page.screenshot({ path: `${shotDir}/01-buffer-org.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    await logout(page)
    await loginAs(page, USER, PASS)
    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(NICK, { timeout: 15_000 })
    const bufferMsg = page.locator('.tbl-wrap table').nth(2).locator('tbody tr', { hasText: '调岗权限缓冲' })
    await expect(bufferMsg).toBeVisible({ timeout: 15_000 })
    await expect(bufferMsg).toContainText('否')
    await expect(page.getByText(/未读 [1-9]/)).toBeVisible()
    await page.screenshot({ path: `${shotDir}/02-buffer-workbench.png`, fullPage: true })

    deliver('expire-buffer')
    await logout(page)
    await loginAdmin(page)
    const switched = await searchOrg(page, NICK)
    await expect(switched.getByTestId('org-user-roles')).toHaveText('编导')
    await expect(switched.getByTestId('org-user-buffer')).toHaveText('已切换')
    await switched.getByTestId('org-user-open').click()
    const after = page.getByTestId('org-user-drawer')
    await expect(after.getByTestId('org-buffer-state')).toHaveText('已切换')
    await expect(after.getByTestId('org-detail-buffer')).toHaveText('—')
    await expect(after.getByTestId('org-diff-summary')).toContainText('缓冲结束')
    await expect(after.getByTestId('org-diff-retained')).toHaveText('保留 —')
    await page.screenshot({ path: `${shotDir}/03-buffer-expired.png`, fullPage: true })
    await page.getByRole('button', { name: '关闭' }).click()

    await logout(page)
    await loginAs(page, USER, PASS)
    await page.goto('/ims/workbench')
    const ended = page.locator('.tbl-wrap table').nth(2).locator('tbody tr', { hasText: '调岗缓冲已结束' })
    await expect(ended).toBeVisible({ timeout: 15_000 })
    await expect(ended).toContainText('否')
    await page.screenshot({ path: `${shotDir}/04-buffer-ended-workbench.png`, fullPage: true })
    expect(pageErrors).toEqual([])
  })
})
