import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-116-screenshots'

/**
 * Checklist **E2E-S7** 切片（acceptance · **纯 UI** · #116）
 * Given: e2e_author 新建带正文的内容并提审
 * When: admin 打开审核抽屉
 * Then: 正文预览在结论区之上 · 审核 steps 可见 · 无意见驳回被拦住 · 填写意见后驳回成功
 */
test.describe('content review drawer read-then-conclude', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('preview and steps before reject opinion', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-rv-drawer-${Date.now()}`
    const title = `E2E 审核抽屉 ${label}`
    const bodyText = `先看正文再下结论 ${label}`
    const opinion = `驳回意见 ${label}`

    await loginAs(page, 'e2e_author')
    await page.goto('/ims/content/list')
    await page.getByRole('button', { name: '新增内容' }).click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await contentDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(bodyText)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await createResp).json()) as { code: number }).code).toBe(0)

    const contentRow = page.locator('tr', { hasText: title })
    await expect(contentRow).toBeVisible({ timeout: 15_000 })
    await contentRow.getByRole('button', { name: '提审' }).click()
    await expect(contentRow).not.toContainText('DRAFT', { timeout: 15_000 })

    await loginAdmin(page)
    await page.goto('/ims/content/review')
    await page.locator('.tab', { hasText: '一级审核' }).click()
    await page.locator('input[placeholder="标题"]').fill(title)
    const listResp = page.waitForResponse(
      (r) => r.url().includes('/content/review') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listResp
    const reviewRow = page.locator('tr', { hasText: title }).first()
    await expect(reviewRow).toBeVisible({ timeout: 15_000 })
    await reviewRow.getByRole('button', { name: '审核' }).click()

    const drawer = page.locator('.drawer.on').filter({ hasText: '审核' })
    const preview = drawer.getByTestId('content-review-preview')
    const conclusion = drawer.getByTestId('content-review-conclusion')
    await expect(preview).toContainText(bodyText)
    await expect(drawer.getByTestId('content-layout-preview')).toContainText(bodyText)
    await expect(drawer.getByTestId('content-review-steps')).toContainText('运营组长：')
    await expect(drawer.getByTestId('content-review-steps')).toContainText('运营总监：')
    await expect(conclusion).toBeVisible()
    const previewBox = await preview.boundingBox()
    const conclusionBox = await conclusion.boundingBox()
    expect(previewBox).toBeTruthy()
    expect(conclusionBox).toBeTruthy()
    expect(previewBox!.y).toBeLessThan(conclusionBox!.y)

    await drawer.screenshot({ path: `${shotDir}/01-review-drawer-body-first.png` })

    await drawer.getByTestId('content-review-reject').click()
    await expect(drawer).toBeVisible()
    await expect(drawer.getByTestId('content-review-reject-opinion')).toBeVisible()

    await drawer.getByTestId('content-review-reject-opinion').fill(opinion)
    await drawer.screenshot({ path: `${shotDir}/02-review-reject-opinion.png` })
    const concludeResp = page.waitForResponse(
      (r) =>
        r.url().includes('/content/review/') &&
        r.url().includes('/conclusion') &&
        r.request().method() === 'PUT' &&
        r.status() === 200,
    )
    await drawer.getByTestId('content-review-reject').click()
    const concludeResult = await concludeResp
    const concluded = (await concludeResult.json()) as { code: number }
    expect(concluded.code).toBe(0)
    const posted = concludeResult.request().postDataJSON() as { conclusion?: string; remark?: string }
    expect(posted.conclusion).toBe('REJECT_BACK')
    expect(posted.remark).toBe(opinion)
    await expect(drawer).not.toBeVisible({ timeout: 10_000 })
    await expect(page.locator('.tbl-wrap tbody tr', { hasText: title })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-review-queue-after-reject.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
