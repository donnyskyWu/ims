import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, loginAdmin } from './closure-helpers'

const SHOT_DIR = '/opt/cursor/artifacts/train-186'

async function shot(page: import('@playwright/test').Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true })
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true })
}

/**
 * #186 · TRAIN 资料空态 / 版本只读预览 / 问卷边角
 * 不覆盖资料筛选（#157）、问卷重答（#164）、统计看板 Tab（#177）。
 */
test.describe('train material preview and quiz tails', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('link version preview stays read-only and empty category is explicit', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-186-${Date.now()}`
    const titleV1 = `E2E 外链原文 ${label}`
    const titleV2 = `E2E 外链修订 ${label}`
    const urlV1 = 'https://example.com/ims-186-v1'
    const urlV2 = 'https://example.com/ims-186-v2'

    await loginAdmin(page)
    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })
    await expect(page.getByTestId('train-weekly-rate')).toContainText('周更新率')

    const emptyCate = page.locator('.tree button.linkish', { hasText: /· 0$/ })
    if (await emptyCate.count()) {
      await emptyCate.first().click()
      await expect(page.getByTestId('train-list-empty')).toContainText('该分类暂无资料')
      await shot(page, '01-cate-empty')
    }

    await page.locator('.tree button.linkish').first().click()
    await page.getByRole('button', { name: '上传资料' }).click()
    const editor = page.locator('.modal-mask .card').filter({ hasText: '上传资料' })
    await editor.locator('label.fld', { hasText: '标题' }).locator('xpath=following-sibling::input[1]').fill(titleV1)
    await editor.locator('select').selectOption('LINK')
    await editor.getByTestId('train-material-link').fill('notaurl')
    await editor.getByRole('button', { name: '发布' }).click()
    await expect(editor.getByTestId('train-material-form-error')).toContainText('外链须为 http(s) 地址')
    await shot(page, '02-link-rejected')

    await editor.getByTestId('train-material-link').fill(urlV1)
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/train/material') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editor.getByRole('button', { name: '发布' }).click()
    const created = (await (await createResp).json()) as { code: number; data?: { linkUrl?: string; version?: number } }
    expect(created.code).toBe(0)
    expect(created.data?.version).toBe(1)
    expect(created.data?.linkUrl).toBe(urlV1)

    const row = page.locator('tr', { hasText: titleV1 })
    await expect(row.getByTestId('train-material-version')).toHaveText('V1')
    await row.getByTestId('train-material-detail').click()
    const drawer = page.getByTestId('train-material-detail-drawer')
    await expect(drawer.getByTestId('train-material-preview')).toContainText(urlV1)
    await expect(drawer.getByTestId('train-material-preview')).toContainText('只读预览，历史版本不可修改')
    await expect(drawer.getByRole('link', { name: '打开外链' })).toBeVisible()
    await expect(drawer).toContainText('尚无历史版本')
    await expect(drawer.getByRole('button', { name: '编辑' })).toHaveCount(0)
    await shot(page, '03-preview-current')
    await drawer.getByRole('button', { name: '关闭' }).click()

    await row.getByTestId('train-material-edit').click()
    const update = page.locator('.modal-mask .card').filter({ hasText: '更新资料' })
    await expect(update).toContainText('将生成新版本 V2，旧版本留档')
    await update.locator('label.fld', { hasText: '标题' }).locator('xpath=following-sibling::input[1]').fill(titleV2)
    await update.getByTestId('train-material-link').fill(urlV2)
    const updateResp = page.waitForResponse(
      (r) => r.url().includes('/train/material/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await update.getByRole('button', { name: '保存新版本' }).click()
    const updated = (await (await updateResp).json()) as {
      code: number
      data?: { version?: number; versions?: Array<{ version?: number; linkUrl?: string; title?: string }> }
    }
    expect(updated.code).toBe(0)
    expect(updated.data?.version).toBe(2)
    expect(updated.data?.versions?.[0]?.linkUrl).toBe(urlV1)
    expect(updated.data?.versions?.[0]?.title).toBe(titleV1)

    const revised = page.locator('tr', { hasText: titleV2 })
    await revised.getByTestId('train-material-detail').click()
    const again = page.getByTestId('train-material-detail-drawer')
    await expect(again.getByTestId('train-material-preview')).toContainText(urlV2)
    await again.getByTestId('train-version-archive').filter({ hasText: titleV1 }).click()
    await expect(again.getByTestId('train-material-preview')).toContainText(urlV1)
    await expect(again.getByTestId('train-material-preview')).toContainText('历史 V1')
    await expect(again.getByTestId('train-material-preview')).not.toContainText(urlV2)
    await expect(again.getByRole('button', { name: '编辑' })).toHaveCount(0)
    await shot(page, '04-preview-archive')
    await again.getByRole('button', { name: '关闭' }).click()

    await page.getByTestId('train-unupdated-open').click()
    const unupdated = page.getByTestId('train-unupdated-drawer')
    await expect(unupdated).toBeVisible()
    await expect(unupdated).not.toContainText(titleV2)
    await unupdated.getByRole('button', { name: '复制清单' }).click()
    await expect(unupdated.getByTestId('train-unupdated-copy-hint')).toBeVisible()
    await shot(page, '05-unupdated')

    expect(pageErrors).toEqual([])
  })

  test('duplicate quiz options are blocked and unanswered questions stay visible', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-186q-${Date.now()}`
    const materialTitle = `E2E 问卷边角资料 ${label}`
    const taskName = `E2E 问卷边角 ${label}`
    const question = `E2E边角题 ${label}`

    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })

    await page.goto('/ims/train/task')
    await expect(page.locator('h1')).toHaveText('学习任务管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '下达学习任务' }).click()
    const modal = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
    await modal.locator('label.fld', { hasText: '任务名称' }).locator('xpath=following-sibling::input[1]').fill(taskName)
    await modal.locator('label.mat-opt').filter({ hasText: `#${materialId}` }).locator('input[type="checkbox"]').check()
    await modal.locator('input[placeholder="如 1"]').fill('1')
    await modal.locator('select').selectOption('QUIZ')
    const block = modal.locator('.quiz-block').first()
    await block.locator('input[placeholder="请输入题目"]').fill(question)
    await block.locator('input[placeholder="选项内容"]').nth(0).fill('相同')
    await block.locator('input[placeholder="选项内容"]').nth(1).fill('相同')
    await modal.getByRole('button', { name: '保存' }).click()
    await expect(modal.getByTestId('train-task-form-error')).toContainText('选项不能重复')
    await shot(page, '06-quiz-duplicate')

    await block.locator('input[placeholder="选项内容"]').nth(1).fill('不同')
    const createResp = page.waitForResponse(
      (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
    )
    await modal.getByRole('button', { name: '保存' }).click()
    const created = (await (await createResp).json()) as { code: number; data?: { id?: number } }
    expect(created.code).toBe(0)
    const taskId = created.data?.id
    expect(taskId).toBeTruthy()

    await page.goto(`/ims/train/study/${taskId}`)
    await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
    await expect(page.getByText(question)).toBeVisible()
    await expect(page.getByText('文件留档 demo/file.pdf')).toBeVisible()
    await expect(page.getByTestId('train-quiz-unanswered')).toContainText('还有 1 题未作答')
    await expect(page.getByRole('button', { name: '提交问卷' })).toBeDisabled()
    await expect(page.getByRole('button', { name: '重新作答' })).toHaveCount(0)
    await shot(page, '07-quiz-unanswered')

    await page.locator('.quiz-q').first().locator('label.opt', { hasText: '不同' }).locator('input').check()
    await expect(page.getByTestId('train-quiz-unanswered')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '提交问卷' })).toBeEnabled()

    expect(pageErrors).toEqual([])
  })
})
