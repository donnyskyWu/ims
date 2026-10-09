import fs from 'node:fs'
import path from 'node:path'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/content-232'

/**
 * #232 CONTENT 本地尾巴（纯 UI）
 * 场次缺字段就地提示；文案提示为空不能生成；无场次时面板说明桩也不会出稿。
 * 计划、SOP、发布单缺必填就地说明，不再只弹「请填写必填项」。
 * 提审后编辑：非草稿不能新提交文案或视频。
 * 不重建 #171 空态、#183 桩预览、#201 列表/审核、#214 发布筛选与视频抽屉。
 */
test.describe('content local tails 232', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('match fields, empty AI prompt, and copy panel without a match', async ({ page }) => {
    test.setTimeout(90_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const marker = `E2E232-${Date.now()}`
    const title = `E2E232 无场次 ${marker}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await expect(createDrawer.getByTestId('match-scheme-empty')).toContainText('尚未添加场次')
    await createDrawer.getByRole('button', { name: '添加场次' }).click()
    await expect(createDrawer.getByTestId('match-scheme-error')).toHaveText('请填写 matchId、主队、客队')
    await page.screenshot({ path: path.join(SHOTS, '01-match-fields-empty.png'), fullPage: true })

    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const createResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number }
    expect(createBody.code).toBe(0)

    const row = page.locator('tr', { hasText: title }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('ai-panel-need-match')).toContainText('本地桩也不会出稿')
    await expect(editDrawer.getByTestId('ai-copy-btn')).toBeDisabled()
    await expect(editDrawer.getByTestId('ai-panel-locked')).toHaveCount(0)
    await page.screenshot({ path: path.join(SHOTS, '02-ai-panel-need-match.png'), fullPage: true })

    await editDrawer.getByRole('button', { name: 'AI 文案' }).click()
    const aiDrawer = page.locator('.drawer.on').filter({ hasText: '选择模型并输入提示' })
    await expect(aiDrawer.getByTestId('ai-copy-prompt-empty')).toContainText('提示为空时不能生成')
    await expect(aiDrawer.locator('select option').first()).toContainText(/qwen|gpt|模型/i, { timeout: 15_000 })
    await expect(aiDrawer.getByTestId('ai-copy-generate')).toBeDisabled()
    await page.screenshot({ path: path.join(SHOTS, '03-ai-prompt-empty.png'), fullPage: true })

    await aiDrawer.getByTestId('ai-copy-prompt').fill(`${marker} 写一段赛后复盘`)
    await expect(aiDrawer.getByTestId('ai-copy-prompt-empty')).toHaveCount(0)
    await expect(aiDrawer.getByTestId('ai-copy-generate')).toBeEnabled()
    const genResp = page.waitForResponse(
      (r) => r.url().includes('/content/ai-content/generate') && r.request().method() === 'POST' && r.status() === 200,
    )
    await aiDrawer.getByTestId('ai-copy-generate').click()
    const genBody = (await (await genResp).json()) as { code: number; data?: { mock?: boolean } }
    expect(genBody.code).toBe(0)
    expect(genBody.data?.mock).toBe(true)
    await expect(aiDrawer.getByTestId('ai-copy-stub')).toContainText('桩预览')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('plan, SOP, and publish forms name the missing field', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    await loginAdmin(page)
    await page.goto('/ims/content/plan')
    await expect(page.locator('h1')).toHaveText('计划管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增计划' }).click()
    const planDrawer = page.locator('.drawer.on').filter({ hasText: '新增计划（草稿）' })
    await planDrawer.getByRole('button', { name: '保存草稿' }).click()
    await expect(planDrawer.getByTestId('plan-form-error')).toHaveText('请填写计划名称')
    await planDrawer.getByTestId('plan-create-name').fill('E2E232 缺模板')
    await planDrawer.getByRole('button', { name: '保存草稿' }).click()
    await expect(planDrawer.getByTestId('plan-form-error')).toHaveText('请选择已启用的 SOP 模板')
    await page.screenshot({ path: path.join(SHOTS, '04-plan-form-error.png'), fullPage: true })

    await page.goto('/ims/content/sop')
    await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增模板' }).click()
    const sopDrawer = page.locator('.drawer.on').filter({ hasText: '新增 SOP 模板' })
    await sopDrawer.getByTestId('sop-content-type').fill('')
    await sopDrawer.getByRole('button', { name: '保存', exact: true }).click()
    await expect(sopDrawer.getByTestId('sop-name-error')).toHaveText('请填写模板名称')
    await expect(sopDrawer.getByTestId('sop-type-error')).toHaveText('请填写内容类型')
    await expect(sopDrawer.getByTestId('sop-dag-error')).toHaveText('请填写模板名称与内容类型')
    await page.screenshot({ path: path.join(SHOTS, '05-sop-name-type-empty.png'), fullPage: true })

    await page.goto('/ims/content/publish')
    await expect(page.locator('h1')).toHaveText('发布管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建发布单' }).click()
    const pubDrawer = page.locator('.drawer.on').filter({ hasText: '新建发布单' })
    await pubDrawer.getByRole('button', { name: '保存' }).click()
    await expect(pubDrawer.getByTestId('publish-create-error')).toHaveText('请填写内容项目 id')
    await pubDrawer.locator('input[type="number"]').first().fill('1')
    await pubDrawer.locator('input[type="number"]').nth(1).fill('1')
    await pubDrawer.locator('input[placeholder="2026-10-08T20:00:00+08:00"]').fill('明天')
    await pubDrawer.getByRole('button', { name: '保存' }).click()
    await expect(pubDrawer.getByTestId('publish-create-error')).toContainText('计划发布时间需包含日期和时间')
    await page.screenshot({ path: path.join(SHOTS, '06-publish-create-error.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('submitted content cannot start a new stub job', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    const title = `E2E232 已提审 ${Date.now()}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    const createResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await createResp).json()) as { code: number }).code).toBe(0)

    const row = page.locator('tr', { hasText: title }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    const reviewResp = page.waitForResponse(
      (r) => r.url().includes('/submit-review') && r.request().method() === 'POST' && r.status() === 200,
    )
    await row.getByRole('button', { name: '提审' }).click()
    expect(((await (await reviewResp).json()) as { code: number }).code).toBe(0)
    await expect(row).toContainText('PENDING_REVIEW', { timeout: 15_000 })
    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await expect(editDrawer.getByTestId('ai-panel-locked')).toContainText('本地桩也不会出新任务')
    await expect(editDrawer.getByTestId('ai-copy-btn')).toBeDisabled()
    await expect(editDrawer.getByTestId('ai-video-btn')).toBeDisabled()
    await page.screenshot({ path: path.join(SHOTS, '07-ai-panel-locked.png'), fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
