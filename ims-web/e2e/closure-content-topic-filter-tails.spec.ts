import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/s7-topic-tails-223'

/**
 * S7 选题列表筛选空态与状态边角（#223 · acceptance · 纯 UI）
 * Given: 不重建状态看板，不改甘特主路径 / 账号空态 / 提报计划日
 * When: 用不会命中的编号、关键词、来源、落选和提报人筛选；落选与取消不填意见；编辑计划发布日后取消
 * Then: 空态写明当前筛选；缺意见不提交；甘特打点带状态，已取消显示日期留痕
 */
test.describe('content topic filter tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter misses name the empty state, and cancelled dates stay as gantt traces', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-tail223-${Date.now()}`
    const title = `E2E 筛选尾巴 ${label}`
    const planDate = '2026-11-21'

    await loginAdmin(page)
    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })

    await page.getByTestId('topic-create-open').click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await expect(createDrawer).toBeVisible()
    await createDrawer.getByTestId('topic-title').fill(title)
    await createDrawer.getByTestId('topic-description').fill(`内容要求：筛选尾巴 ${label}`)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic') && !r.url().includes('/list') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByTestId('topic-submit').click()
    const created = (await (await createResp).json()) as { code: number }
    expect(created.code).toBe(0)
    await expect(createDrawer).not.toBeVisible({ timeout: 10_000 })
    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.getByTestId('topic-task-gate')).toHaveText('未立项不可出任务')

    await page.getByTestId('topic-filter-no').fill(`TP-MISS-${label}`)
    const missNo = page.waitForResponse(
      (r) => r.url().includes('/content/topic/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-filter-search').click()
    const missNoBody = (await (await missNo).json()) as { code: number; data?: { total?: number } }
    expect(missNoBody.code).toBe(0)
    expect(missNoBody.data?.total).toBe(0)
    const listEmpty = page.getByTestId('topic-list-empty')
    await expect(listEmpty).toHaveAttribute('data-filtered', '1')
    await expect(listEmpty).toContainText('没有符合编号的选题')
    await expect(listEmpty).toContainText('需完整匹配')
    await page.screenshot({ path: `${SHOTS}/01-filter-no-empty.png`, fullPage: true })

    await page.getByTestId('topic-filter-reset').click()
    await expect(row).toBeVisible({ timeout: 15_000 })

    await page.getByTestId('topic-filter-keyword').fill(`no-kw-${label}`)
    await page.getByTestId('topic-filter-search').click()
    await expect(listEmpty).toContainText('没有符合关键词的选题')

    await page.getByTestId('topic-filter-reset').click()
    await page.getByTestId('topic-filter-source').selectOption('BRAND')
    await page.getByTestId('topic-filter-keyword').fill(`no-brand-${label}`)
    await page.getByTestId('topic-filter-search').click()
    await expect(listEmpty).toContainText('暂无符合当前筛选的选题')
    await expect(listEmpty).toContainText('来源 品牌')

    await page.getByTestId('topic-filter-reset').click()
    await page.getByTestId('topic-filter-status').selectOption('REJECTED')
    await page.getByTestId('topic-filter-keyword').fill(`no-status-${label}`)
    await page.getByTestId('topic-filter-search').click()
    await expect(listEmpty).toContainText('暂无符合当前筛选的选题')
    await expect(listEmpty).toContainText('状态 落选')
    await page.screenshot({ path: `${SHOTS}/02-filter-rejected-empty.png`, fullPage: true })

    await page.getByTestId('topic-filter-reset').click()
    await page.getByTestId('topic-filter-submitter').selectOption({ label: 'E2E内容作者（e2e_author）' })
    const ownerResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/list') && r.url().includes('submitterUserId') && r.status() === 200,
    )
    await page.getByTestId('topic-filter-search').click()
    const ownerBody = (await (await ownerResp).json()) as { code: number; data?: { total?: number } }
    expect(ownerBody.code).toBe(0)
    expect(ownerBody.data?.total).toBe(0)
    await expect(listEmpty).toContainText('该提报人暂无选题')

    await page.getByTestId('topic-filter-reset').click()
    await expect(row).toBeVisible({ timeout: 15_000 })

    await row.getByRole('button', { name: '评审' }).click()
    const review = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await expect(review).toBeVisible()
    await review.getByRole('button', { name: '落选' }).click()
    await expect(review.getByTestId('topic-review-error')).toHaveText('请填写落选意见')
    await expect(review).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/03-reject-opinion.png`, fullPage: true })
    await review.locator('.dr-x').click()
    await expect(review).not.toBeVisible({ timeout: 10_000 })
    await expect(row).toContainText('待评审')

    await row.getByTestId('topic-cancel').click()
    const cancelModal = page.getByTestId('topic-cancel-modal')
    await cancelModal.getByTestId('topic-cancel-confirm').click()
    await expect(cancelModal).toContainText('请填写取消原因')
    await expect(row).toContainText('待评审')
    await page.screenshot({ path: `${SHOTS}/04-cancel-opinion.png`, fullPage: true })
    await cancelModal.getByRole('button', { name: '关闭' }).click()
    await expect(cancelModal).toHaveCount(0)

    await row.getByTestId('topic-edit').click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑选题' })
    await editDrawer.getByTestId('topic-edit-plan-date').fill(planDate)
    const editResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.request().method() === 'PUT' && !r.url().includes('/review') && r.status() === 200,
    )
    await editDrawer.getByTestId('topic-submit').click()
    expect((await (await editResp).json() as { code: number }).code).toBe(0)
    await expect(row).toContainText(planDate, { timeout: 15_000 })

    await page.getByTestId('topic-view-gantt').click()
    await expect(page.getByTestId('topic-gantt-scope')).toContainText('只显示已填写计划发布日的选题')
    await page.getByTestId('topic-gantt-from').fill(planDate)
    await page.getByTestId('topic-gantt-to').fill(planDate)
    const ganttResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    const ganttBody = (await (await ganttResp).json()) as {
      code: number
      data?: { items?: Array<{ title: string; topicStatus: string }> }
    }
    expect(ganttBody.code).toBe(0)
    const pendingHit = (ganttBody.data?.items || []).find((item) => item.title === title)
    expect(pendingHit?.topicStatus).toBe('PENDING_REVIEW')
    const ganttRow = page.getByTestId('topic-gantt-row').filter({ hasText: title })
    await expect(ganttRow).toHaveAttribute('data-status', 'PENDING_REVIEW')
    await expect(ganttRow.locator('[data-testid="topic-gantt-mark"]')).toHaveAttribute('title', `${title} · 待评审`)
    await expect(ganttRow.getByTestId('topic-gantt-trace')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/05-gantt-pending-status.png`, fullPage: true })

    await page.getByTestId('topic-view-list').click()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByTestId('topic-cancel').click()
    const cancelAgain = page.getByTestId('topic-cancel-modal')
    await cancelAgain.getByTestId('topic-cancel-opinion').fill('筛选尾巴取消')
    const cancelResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await cancelAgain.getByTestId('topic-cancel-confirm').click()
    expect((await (await cancelResp).json() as { code: number }).code).toBe(0)
    await expect(row.getByTestId('topic-task-gate')).toHaveText('已取消不可出任务', { timeout: 15_000 })
    await expect(row).toContainText('已取消')
    await page.screenshot({ path: `${SHOTS}/06-cancelled-gate.png`, fullPage: true })

    await page.getByTestId('topic-view-gantt').click()
    await page.getByTestId('topic-gantt-from').fill(planDate)
    await page.getByTestId('topic-gantt-to').fill(planDate)
    const traceResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    await traceResp
    const traced = page.getByTestId('topic-gantt-row').filter({ hasText: title })
    await expect(traced).toHaveAttribute('data-status', 'CANCELLED')
    await expect(traced.getByTestId('topic-gantt-trace')).toContainText('日期留痕')
    await expect(traced.locator('[data-testid="topic-gantt-mark"]')).toHaveAttribute('title', `${title} · 已取消`)
    await page.screenshot({ path: `${SHOTS}/07-gantt-cancelled-trace.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
