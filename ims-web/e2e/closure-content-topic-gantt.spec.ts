import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/topic-gantt-140'

/**
 * CONTENT-002 排期甘特（acceptance · #140 · 纯 UI）
 * Given: UI 创建启用 SOP
 * When: 两条选题立项到不同计划发布日 → 选题计划切换「排期甘特」并收窄区间
 * Then: 区间内选题在计划发布日打点；区间外选题不出现
 */
test.describe('content topic gantt closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('approved topics mark their plan publish date on the gantt', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-gantt-${Date.now()}`
    const sopName = `E2E 甘特 SOP ${label}`
    const inTitle = `E2E 甘特内 ${label}`
    const outTitle = `E2E 甘特外 ${label}`

    await loginAdmin(page)
    await createSopViaUi(page, { sopName, nodeName: '脚本' })

    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })
    await expect(page.getByTestId('topic-view-switch')).toBeVisible()

    await submitTopic(page, inTitle, `内容要求：区间内 ${label}`)
    await approveTopic(page, inTitle, sopName, '2026-12-02')
    await submitTopic(page, outTitle, `内容要求：区间外 ${label}`)
    await approveTopic(page, outTitle, sopName, '2026-12-20')
    await page.screenshot({ path: `${SHOTS}/01-topic-list.png`, fullPage: true })

    await page.getByTestId('topic-view-gantt').click()
    await expect(page.getByTestId('topic-gantt')).toBeVisible()
    await page.getByTestId('topic-gantt-from').fill('2026-12-01')
    await page.getByTestId('topic-gantt-to').fill('2026-12-07')
    const ganttResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    const body = (await (await ganttResp).json()) as { code: number; data?: { items?: Array<{ title: string; planPublishDate: string }> } }
    expect(body.code).toBe(0)
    const titles = (body.data?.items || []).map((item) => item.title)
    expect(titles).toContain(inTitle)
    expect(titles).not.toContain(outTitle)

    const row = page.getByTestId('topic-gantt-row').filter({ hasText: inTitle })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('已立项')
    await expect(row).toContainText(sopName)
    const mark = row.locator('[data-testid="topic-gantt-mark"]')
    await expect(mark).toHaveAttribute('data-date', '2026-12-02')
    await expect(page.getByTestId('topic-gantt-row').filter({ hasText: outTitle })).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/02-topic-gantt.png`, fullPage: true })

    await page.getByTestId('topic-view-list').click()
    await expect(page.locator('tr', { hasText: inTitle })).toContainText('已立项')
    await page.screenshot({ path: `${SHOTS}/03-topic-back-to-list.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})

async function submitTopic(page: import('@playwright/test').Page, title: string, requirement: string) {
  await page.getByTestId('topic-create-open').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
  await expect(drawer).toBeVisible()
  await drawer.getByTestId('topic-title').fill(title)
  await drawer.getByTestId('topic-description').fill(requirement)
  const createResp = page.waitForResponse(
    (r) => r.url().includes('/content/topic') && !r.url().includes('/gantt') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByTestId('topic-submit').click()
  const created = (await (await createResp).json()) as { code: number }
  expect(created.code).toBe(0)
  await expect(drawer).not.toBeVisible({ timeout: 10_000 })
  await expect(page.locator('tr', { hasText: title })).toBeVisible({ timeout: 15_000 })
}

async function approveTopic(page: import('@playwright/test').Page, title: string, sopName: string, planDate: string) {
  const row = page.locator('tr', { hasText: title })
  await row.getByRole('button', { name: '评审' }).click()
  const review = page.locator('.drawer.on').filter({ hasText: '评审立项' })
  await expect(review).toBeVisible()
  await review.getByTestId('topic-sop').selectOption({ label: sopName })
  await review.getByTestId('topic-plan-date').fill(planDate)
  const approved = page.waitForResponse(
    (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
  )
  await review.getByTestId('topic-approve').click()
  const body = (await (await approved).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(review).not.toBeVisible({ timeout: 10_000 })
  await expect(row).toContainText('已立项')
  await expect(row).toContainText(planDate)
}
