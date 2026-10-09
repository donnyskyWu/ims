import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/s7-topic-form-edges-241'

/**
 * S7 选题表单与甘特边角（#241 · acceptance · 纯 UI）
 * Given: 不重建 #190 甘特空态 / 热点参考，也不做 #223 筛选空态与缺意见拦截
 * When: 提报缺字段或计划日早于今天；评审带出已填日期后再缺 SOP/日期立项；甘特填无效账号或加载失败
 * Then: 缺项与过期日不提交；缺 SOP/日期仍返回 1052 并红框定位；无效账号不请求；失败可重试
 */
test.describe('content topic form edges closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('form field copy, past plan date, and gantt account edges stay local', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-edge-${Date.now()}`
    const sopName = `E2E 边角 SOP ${label}`
    const title = `E2E 表单边角 ${label}`
    const planDate = '2026-12-16'

    await loginAdmin(page)
    await createSopViaUi(page, { sopName, nodeName: '脚本' })

    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })

    let posted = false
    page.on('request', (req) => {
      if (req.method() === 'POST' && /\/content\/topic(\?|$)/.test(req.url())) posted = true
    })

    await page.getByTestId('topic-create-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('topic-submit').click()
    await expect(drawer.getByTestId('topic-title-error')).toHaveText('请填写选题标题')
    await expect(drawer.getByTestId('topic-description-error')).toHaveText('请填写内容要求')
    expect(posted).toBe(false)

    await drawer.getByTestId('topic-title').fill(`   ${title}   `)
    await drawer.getByTestId('topic-description').fill(`内容要求：表单边角 ${label}`)
    await drawer.getByTestId('topic-edit-plan-date').fill('2020-01-01')
    await drawer.getByTestId('topic-submit').click()
    await expect(drawer.getByTestId('topic-plan-early-error')).toHaveText('计划发布日不能早于今天')
    await expect(drawer.getByTestId('topic-title-error')).toHaveCount(0)
    expect(posted).toBe(false)
    await page.screenshot({ path: `${SHOTS}/01-create-past-date.png`, fullPage: true })

    await drawer.getByTestId('topic-edit-plan-date').fill(planDate)
    const createResp = page.waitForResponse(
      (r) => /\/content\/topic(\?|$)/.test(r.url()) && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('topic-submit').click()
    const created = (await (await createResp).json()) as { code: number; data?: { planPublishDate?: string; title?: string } }
    expect(created.code).toBe(0)
    expect(created.data?.planPublishDate).toBe(planDate)
    expect(created.data?.title).toBe(title)
    await expect(drawer).not.toBeVisible({ timeout: 10_000 })

    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row.locator('b')).toHaveAttribute('title', title)
    await row.getByTestId('topic-edit').click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑选题' })
    await expect(editDrawer).toBeVisible()
    await expect(editDrawer.getByText('正在加载启用中的 SOP')).toHaveCount(0, { timeout: 15_000 })
    const editSopOptions = await editDrawer.getByTestId('topic-edit-sop').locator('option').count()
    if (editSopOptions <= 1) {
      await expect(editDrawer.getByTestId('topic-edit-sop-empty')).toContainText('暂无启用中的 SOP')
    } else {
      await expect(editDrawer.getByTestId('topic-edit-sop-empty')).toHaveCount(0)
      await expect(editDrawer.getByTestId('topic-edit-sop')).toContainText(sopName)
    }
    await editDrawer.locator('.dr-x').click()
    await expect(editDrawer).not.toBeVisible({ timeout: 10_000 })

    await row.getByRole('button', { name: '评审' }).click()
    const review = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await expect(review).toBeVisible()
    await expect(review.getByTestId('topic-plan-date')).toHaveValue(planDate)
    await expect(review.getByTestId('topic-plan-prefill')).toContainText('已带出提报时的计划发布日')
    await page.screenshot({ path: `${SHOTS}/02-review-prefill.png`, fullPage: true })

    await review.getByTestId('topic-plan-date').fill('')
    const blocked = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await review.getByTestId('topic-approve').click()
    const blockedBody = (await (await blocked).json()) as { code: number }
    expect(blockedBody.code).toBe(1052)
    await expect(review.getByTestId('topic-review-error')).toContainText('1052')
    await expect(review.getByTestId('topic-sop-error')).toHaveText('请选择挂接 SOP')
    await expect(review.getByTestId('topic-plan-date-error')).toHaveText('请填写计划发布日')
    await page.screenshot({ path: `${SHOTS}/03-approve-field-errors.png`, fullPage: true })

    await review.getByTestId('topic-sop').selectOption({ label: sopName })
    await review.getByTestId('topic-plan-date').fill('2020-01-02')
    let reviewPuts = 0
    const onReview = (req: { method: () => string; url: () => string }) => {
      if (req.method() === 'PUT' && req.url().includes('/review')) reviewPuts += 1
    }
    page.on('request', onReview)
    await review.getByTestId('topic-approve').click()
    await expect(review.getByTestId('topic-plan-date-error')).toHaveText('计划发布日不能早于今天')
    await expect(review.getByTestId('topic-sop-error')).toHaveCount(0)
    expect(reviewPuts).toBe(0)
    page.off('request', onReview)
    await page.screenshot({ path: `${SHOTS}/04-review-past-date.png`, fullPage: true })

    await review.getByTestId('topic-plan-date').fill(planDate)
    const approved = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await review.getByTestId('topic-approve').click()
    const approvedBody = (await (await approved).json()) as { code: number }
    expect(approvedBody.code).toBe(0)
    await expect(review).not.toBeVisible({ timeout: 10_000 })
    await expect(row).toContainText('已立项')

    await page.getByTestId('topic-view-gantt').click()
    await expect(page.getByTestId('topic-gantt')).toBeVisible()
    await page.getByTestId('topic-gantt-from').fill(planDate)
    await page.getByTestId('topic-gantt-to').fill(planDate)
    await page.getByTestId('topic-gantt-account').fill('')
    const shown = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-query').click()
    await shown
    const ganttRow = page.getByTestId('topic-gantt-row').filter({ hasText: title })
    await expect(ganttRow).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('topic-gantt-legend')).toContainText('蓝条为计划发布日')
    await page.screenshot({ path: `${SHOTS}/05-gantt-legend.png`, fullPage: true })

    let ganttHits = 0
    const onGantt = (req: { url: () => string }) => {
      if (req.url().includes('/content/topic/gantt')) ganttHits += 1
    }
    page.on('request', onGantt)
    await page.getByTestId('topic-gantt-account').fill('0')
    await page.getByTestId('topic-gantt-query').click()
    await expect(page.getByTestId('topic-gantt-error')).toContainText('请填写有效的发布账号 ID')
    await expect(page.getByTestId('topic-gantt-retry')).toHaveCount(0)
    await expect(page.getByTestId('topic-gantt-row')).toHaveCount(0)
    expect(ganttHits).toBe(0)
    page.off('request', onGantt)
    await page.screenshot({ path: `${SHOTS}/06-gantt-bad-account.png`, fullPage: true })

    await page.getByTestId('topic-gantt-account').fill('')
    await page.route('**/content/topic/gantt**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 1500, msg: '甘特暂时不可用' }),
      })
    })
    await page.getByTestId('topic-gantt-query').click()
    await expect(page.getByTestId('topic-gantt-error')).toContainText('甘特暂时不可用')
    await expect(page.getByTestId('topic-gantt-retry')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/07-gantt-retry.png`, fullPage: true })
    await page.unroute('**/content/topic/gantt**')
    const recovered = page.waitForResponse(
      (r) => r.url().includes('/content/topic/gantt') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-gantt-retry').click()
    const recoveredBody = (await (await recovered).json()) as { code: number }
    expect(recoveredBody.code).toBe(0)
    await expect(ganttRow).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('topic-gantt-error')).toHaveCount(0)

    expect(pageErrors).toEqual([])
  })
})
