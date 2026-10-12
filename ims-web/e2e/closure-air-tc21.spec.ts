import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * TC-21 AIR-SKL / AIR-KB / AIR-CFG 页面侧（BUG-C061～C068）。
 * 数据经表单创建，不经 page.evaluate 调 admin-api。
 */
test.describe('air tc21 form closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('skill form, kb upload, model stub and prompt dropdowns', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/air/skill')
    await expect(page.locator('h1')).toHaveText('技能库', { timeout: 15_000 })
    await expect(page.getByTestId('air-skill-stats')).toContainText('技能 / 专家 / 知识库')
    await expect(page.getByTestId('air-skill-stats')).toContainText('知识文档')
    await expect(page.getByTestId('air-skill-category-filter')).toBeVisible()
    await expect(page.getByRole('columnheader', { name: '累计调用' })).toBeVisible()

    await page.getByTestId('air-skill-create').click()
    const skillForm = page.getByTestId('air-skill-form')
    await expect(skillForm.getByText('技能名称')).toContainText('*')
    await expect(skillForm.getByText('能力说明')).toContainText('*')
    let skillPosts = 0
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/air/skill')) skillPosts += 1
    })
    await skillForm.getByTestId('air-skill-save').click()
    await expect(skillForm.getByText('必填项，请填写').first()).toBeVisible()
    expect(skillPosts).toBe(0)

    const skillName = `TC21技能${Date.now()}`
    await skillForm.getByTestId('air-skill-name').fill(skillName)
    await skillForm.getByTestId('air-skill-category').selectOption('内容生产')
    await expect(skillForm.getByTestId('air-skill-owner')).not.toHaveValue('')
    await skillForm.getByTestId('air-skill-capability').fill('输出卖点清单')
    await skillForm.getByTestId('air-skill-prompt').fill('请提炼 {product}')
    const submitted = page.waitForResponse((response) => response.url().includes('/submit-audit'))
    await skillForm.getByTestId('air-skill-save').click()
    expect((await (await submitted).json()).code).toBe(0)
    await expect(page.getByTestId('air-skill-toast')).toContainText('技能已提交')

    await page.locator('input[placeholder="技能名称"]').fill(skillName)
    const listed = page.waitForResponse((response) => response.url().includes('/air/skill/list'))
    await page.getByRole('button', { name: '查询' }).click()
    await listed
    const row = page.locator('tbody tr').filter({ hasText: skillName })
    await expect(row.getByTestId('air-skill-audit')).toHaveCount(0)
    await row.getByTestId('air-skill-no').click()
    const detail = page.getByTestId('air-skill-detail')
    await expect(detail).toBeVisible()
    await expect(detail).toContainText('技能 ID')
    await expect(detail).toContainText('安全审核')
    await expect(detail).toContainText('授权范围')
    await detail.getByRole('button', { name: '关闭' }).click()

    await page.goto('/ims/air/kb')
    await expect(page.locator('h1')).toHaveText('知识库', { timeout: 15_000 })
    await expect(page.getByTestId('air-kb-note')).toContainText('仅文件管理')
    await page.getByTestId('air-kb-upload').click()
    const upload = page.getByTestId('air-kb-upload-form')
    await expect(upload.getByTestId('air-kb-upload-mode-file')).toBeVisible()
    await expect(upload.getByTestId('air-kb-upload-mode-url')).toBeVisible()
    await expect(upload.getByTestId('air-kb-upload-mode-text')).toBeVisible()
    await expect(upload.locator('input[type="file"]')).toBeVisible()
    let uploadPosts = 0
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/air/kb/doc/')) uploadPosts += 1
    })
    await upload.getByTestId('air-kb-upload-save').click()
    await expect(upload.getByText('必填项，请填写').first()).toBeVisible()
    await expect(upload.getByText('网络错误')).toHaveCount(0)
    expect(uploadPosts).toBe(0)

    await upload.getByTestId('air-kb-upload-mode-text').click()
    const kbSelect = upload.getByTestId('air-kb-upload-kb')
    const kbValue = await kbSelect.locator('option').nth(1).getAttribute('value')
    await kbSelect.selectOption(kbValue || '')
    await upload.getByTestId('air-kb-upload-title').fill(`TC21文本${Date.now()}`)
    await upload.getByTestId('air-kb-upload-content').fill('粘贴正文')
    const imported = page.waitForResponse((response) => response.url().includes('/import-text'))
    await upload.getByTestId('air-kb-upload-save').click()
    expect((await (await imported).json()).code).toBe(0)
    await expect(page.getByTestId('air-kb-toast')).toContainText('已提交 文本入库')

    await page.goto('/ims/air/cfg')
    await expect(page.locator('h1')).toHaveText('模型与提示词', { timeout: 15_000 })
    await expect(page.getByRole('button', { name: 'Key 管理' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '审计监控' })).toHaveCount(0)
    await page.getByRole('button', { name: '新增模型' }).click()
    const modelForm = page.getByTestId('air-model-form')
    await modelForm.getByTestId('air-model-save').click()
    await expect(modelForm.getByText('必填项，请填写').first()).toBeVisible()
    await modelForm.getByTestId('air-model-name').fill(`TC21模型${Date.now()}`)
    await modelForm.getByTestId('air-model-vendor').selectOption('自建网关')
    await modelForm.getByTestId('air-model-id').fill('stub-mini')
    const savedModel = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/model') && response.request().method() === 'POST',
    )
    await modelForm.getByTestId('air-model-save').click()
    const modelBody = await (await savedModel).json()
    expect(modelBody.code).toBe(0)
    expect(modelBody.data.status).toBe('DISCONNECTED')
    await expect(page.getByTestId('air-cfg-toast')).toContainText('模型已保存')
    const modelRow = page.locator('tbody tr').filter({ hasText: 'stub-mini' })
    await modelRow.getByTestId('air-model-test').click()
    await expect(page.getByTestId('air-cfg-toast')).toContainText('未配置密钥')

    await page.getByRole('button', { name: '提示词' }).click()
    await page.getByRole('button', { name: '新增提示词' }).click()
    const promptForm = page.getByTestId('air-prompt-form')
    await expect(promptForm.getByTestId('air-prompt-scene').locator('option', { hasText: '内容生成' })).toHaveCount(1)
    await expect(promptForm.getByTestId('air-prompt-doc').locator('option', { hasText: '正式方案' })).toHaveCount(1)
    await promptForm.getByTestId('air-prompt-save').click()
    await expect(promptForm.getByText('必填项，请填写').first()).toBeVisible()
    await promptForm.getByTestId('air-prompt-name').fill(`TC21提示词${Date.now()}`)
    await promptForm.getByTestId('air-prompt-scene').selectOption('内容生成')
    await promptForm.getByTestId('air-prompt-doc').selectOption('正式方案')
    await promptForm.getByTestId('air-prompt-content').fill('你好 {{topic}}')
    const savedPrompt = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/prompt') && response.request().method() === 'POST',
    )
    await promptForm.getByTestId('air-prompt-save').click()
    expect((await (await savedPrompt).json()).code).toBe(0)
    await expect(page.getByTestId('air-cfg-toast')).toContainText('提示词已保存')

    await page.goto('/ims/air/expert')
    await expect(page.getByTestId('air-expert-export')).toBeVisible()
    await page.getByTestId('air-expert-export').click()
    await expect(page.getByTestId('air-expert-export-note')).toContainText('已导出')

    expect(pageErrors).toEqual([])
  })
})
