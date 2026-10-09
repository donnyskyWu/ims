import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-104-screenshots'

/**
 * Checklist **E2E-S7-01**（acceptance · 选题立项 · **纯 UI**）
 * Given: UI 创建启用 SOP
 * When: 提报选题（内容要求）→ 未选 SOP/计划发布日点立项 → 再选择 SOP + 计划发布日立项
 * Then: 1052 可见；通过后「已立项」且可出任务；落选保持不可出任务
 */
test.describe('content topic project closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('TOP-R1 blocks approve until SOP and plan date, then project can create task', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-topic-${Date.now()}`
    const sopName = `E2E 立项 SOP ${label}`
    const title = `E2E 选题 ${label}`
    const requirement = `内容要求：口播赛程 ${label}`
    const rejectTitle = `E2E 落选 ${label}`

    await loginAdmin(page)
    await createSopViaUi(page, { sopName, nodeName: '脚本' })

    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })

    await page.getByTestId('topic-create-open').click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await expect(createDrawer).toBeVisible()
    await createDrawer.getByTestId('topic-title').fill(title)
    await createDrawer.getByTestId('topic-description').fill(requirement)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByTestId('topic-submit').click()
    const created = (await (await createResp).json()) as { code: number }
    expect(created.code).toBe(0)
    await expect(createDrawer).not.toBeVisible({ timeout: 10_000 })

    const pendingRow = page.locator('tr', { hasText: title })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })
    await expect(pendingRow).toContainText('待评审')
    await expect(pendingRow).toContainText('未立项不可出任务')
    await page.screenshot({ path: `${SHOTS}/01-topic-pending.png`, fullPage: true })

    await pendingRow.getByRole('button', { name: '评审' }).click()
    const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await expect(reviewDrawer).toBeVisible()
    await expect(reviewDrawer.getByTestId('topic-review-requirement')).toContainText(requirement)

    const blocked = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewDrawer.getByTestId('topic-approve').click()
    const blockedBody = (await (await blocked).json()) as { code: number; msg?: string }
    expect(blockedBody.code).toBe(1052)
    await expect(reviewDrawer.getByTestId('topic-review-error')).toContainText('1052')
    await expect(reviewDrawer.getByTestId('topic-review-error')).toContainText('选题立项缺少 SOP 或计划发布日')
    await page.screenshot({ path: `${SHOTS}/02-topic-1052.png`, fullPage: true })

    await reviewDrawer.getByTestId('topic-sop').selectOption({ label: sopName })
    await reviewDrawer.getByTestId('topic-plan-date').fill('2026-12-01')
    const approved = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await reviewDrawer.getByTestId('topic-approve').click()
    const approvedBody = (await (await approved).json()) as { code: number }
    expect(approvedBody.code).toBe(0)
    await expect(reviewDrawer).not.toBeVisible({ timeout: 10_000 })

    const approvedRow = page.locator('tr', { hasText: title })
    await expect(approvedRow).toContainText('已立项')
    await expect(approvedRow).toContainText('可出任务')
    await expect(approvedRow).toContainText(sopName)
    await expect(approvedRow).toContainText('2026-12-01')
    await expect(approvedRow).toContainText('内容项目 #')
    await page.screenshot({ path: `${SHOTS}/03-topic-approved.png`, fullPage: true })

    await page.getByTestId('topic-create-open').click()
    const rejectDrawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await rejectDrawer.getByTestId('topic-title').fill(rejectTitle)
    await rejectDrawer.getByTestId('topic-description').fill(`内容要求：不采用 ${label}`)
    await rejectDrawer.getByTestId('topic-submit').click()
    const rejectRow = page.locator('tr', { hasText: rejectTitle })
    await expect(rejectRow).toBeVisible({ timeout: 15_000 })
    await rejectRow.getByRole('button', { name: '评审' }).click()
    const rejectReview = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await rejectReview.getByTestId('topic-opinion').fill('与内容要求不符')
    const rejectResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await rejectReview.getByRole('button', { name: '落选' }).click()
    const rejectBody = (await (await rejectResp).json()) as { code: number }
    expect(rejectBody.code).toBe(0)
    await expect(rejectRow).toContainText('落选')
    await expect(rejectRow).toContainText('落选不可出任务')
    await page.screenshot({ path: `${SHOTS}/04-topic-rejected.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
