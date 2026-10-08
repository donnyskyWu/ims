import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * Checklist E2E-S8-03 / E2E-S8-11 的页面侧（acceptance · 纯 UI）。
 * experts.assemble 网关产物与连续认证失败冻结在 pytest（test_air_expert_assemble.py）。
 * 审计行来自启动种子写入的 ims_mcp_log，不经 admin-api 造数。
 */
const shotDir = '/opt/cursor/artifacts/e2e-92-screenshots'

test.describe('air expert assemble and audit closure S8', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('assemble preview, persist grants, show mcp audit columns', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)

    const skillName = `E2E组装技能${Date.now()}`
    await page.goto('/ims/air/skill')
    await expect(page.locator('h1')).toHaveText('技能库', { timeout: 15_000 })
    await page.getByTestId('air-skill-create').click()
    const skillForm = page.getByTestId('air-skill-form')
    await skillForm.getByTestId('air-skill-name').fill(skillName)
    const createdSkill = page.waitForResponse(
      (response) => response.url().includes('/air/skill') && response.request().method() === 'POST',
    )
    await skillForm.getByTestId('air-skill-save').click()
    const skillBody = await (await createdSkill).json()
    expect(skillBody.code).toBe(0)
    const skillNo = skillBody.data.skillNo as string

    await page.locator('input[placeholder="技能名称"]').fill(skillName)
    const listed = page.waitForResponse(
      (response) => response.url().includes('/air/skill/list') && response.request().method() === 'GET',
    )
    await page.getByRole('button', { name: '查询' }).click()
    await listed
    const skillRow = page.locator('tbody tr').filter({ hasText: skillName })
    const submitted = page.waitForResponse((response) => response.url().includes('/submit-audit'))
    await skillRow.getByTestId('air-skill-submit').click()
    expect((await (await submitted).json()).code).toBe(0)
    await expect(skillRow.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'PENDING')
    const approved = page.waitForResponse(
      (response) => response.url().includes('/audit') && response.request().method() === 'PUT',
    )
    await skillRow.getByTestId('air-skill-approve').click()
    expect((await (await approved).json()).code).toBe(0)
    await expect(skillRow.getByTestId('air-skill-status')).toHaveAttribute('data-status', 'PUBLISHED')

    const expertName = `E2E组装专家${Date.now()}`
    const prompt = '你是直播复盘专家，只下发组装包。'
    await page.goto('/ims/air/expert')
    await expect(page.locator('h1')).toHaveText('专家库', { timeout: 15_000 })
    await page.getByTestId('air-expert-create').click()
    const form = page.getByTestId('air-expert-form')
    await form.getByTestId('air-expert-name').fill(expertName)
    await form.getByTestId('air-expert-scene').fill('直播复盘')
    await form.getByTestId('air-expert-prompt').fill(prompt)
    const skillOption = form.getByTestId('air-expert-skill').locator('option', { hasText: skillName })
    await expect(skillOption).toHaveCount(1)
    await form.getByTestId('air-expert-skill').selectOption({ label: `${skillName} (${skillNo})` })
    const createdExpert = page.waitForResponse(
      (response) => response.url().includes('/air/expert') && response.request().method() === 'POST',
    )
    await form.getByTestId('air-expert-save').click()
    expect((await (await createdExpert).json()).code).toBe(0)

    await page.getByTestId('air-expert-filter').fill(expertName)
    const expertListed = page.waitForResponse(
      (response) => response.url().includes('/air/expert/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-expert-search').click()
    await expertListed
    const card = page.getByTestId('air-expert-card').filter({ hasText: expertName })
    await expect(card).toHaveAttribute('data-status', 'DRAFT')
    await page.screenshot({ path: `${shotDir}/01-expert-draft.png`, fullPage: true })

    const published = page.waitForResponse(
      (response) => response.url().includes('/publish') && response.request().method() === 'PUT',
    )
    await card.getByTestId('air-expert-publish').click()
    expect((await (await published).json()).code).toBe(0)
    await expect(card).toHaveAttribute('data-status', 'PUBLISHED')
    await page.screenshot({ path: `${shotDir}/02-expert-published.png`, fullPage: true })

    const previewed = page.waitForResponse(
      (response) => response.url().includes('/air/expert/') && response.request().method() === 'GET',
    )
    await card.getByTestId('air-expert-preview-open').click()
    const previewBody = await (await previewed).json()
    expect(previewBody.code).toBe(0)
    expect(previewBody.data.assemblePreview.systemPrompt).toBe(prompt)
    expect(previewBody.data.assemblePreview.skillRefs[0].code).toBe(skillNo)
    expect(previewBody.data.assemblePreview.skillRefs[0].md).toBe('')
    expect(previewBody.data.assemblePreview.guidelines).toContain('网关不执行模型')
    expect(previewBody.data.assemblePreview.knowledgeContext).toBeUndefined()
    const preview = page.getByTestId('air-expert-preview')
    await expect(preview.getByTestId('air-expert-preview-prompt')).toContainText(prompt)
    await expect(preview.getByTestId('air-expert-skill-ref')).toContainText(skillNo)
    await expect(preview.getByTestId('air-expert-guidelines')).toContainText('网关不执行模型')
    await expect(preview.getByTestId('air-expert-no-knowledge')).toContainText('不返回 knowledgeContext')
    await expect(preview.getByTestId('air-expert-knowledge-context')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-assemble-preview.png`, fullPage: true })
    await preview.getByTestId('air-expert-preview-close').click()

    await card.getByTestId('air-expert-grant').click()
    const drawer = page.getByTestId('air-expert-grant-form')
    await expect(drawer).toBeVisible()

    await drawer.getByTestId('air-expert-grant-type').selectOption('PERSON')
    await drawer.getByTestId('air-expert-grant-user-search').fill('admin')
    const users = page.waitForResponse((response) => response.url().includes('/system/user/page'))
    await drawer.getByTestId('air-expert-grant-user-find').click()
    await users
    await expect(drawer.getByTestId('air-expert-grant-target')).not.toHaveValue('')
    const personSaved = page.waitForResponse(
      (response) => response.url().includes('/air/expert/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-expert-grant-save').click()
    expect((await (await personSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-expert-grant-row').filter({ hasText: '人员' })).toContainText('管理员')

    await drawer.getByTestId('air-expert-grant-type').selectOption('ROLE')
    await expect(drawer.getByTestId('air-expert-grant-target').locator('option', { hasText: '系统管理员' })).toHaveCount(1)
    await drawer.getByTestId('air-expert-grant-target').selectOption({ label: '系统管理员' })
    const roleSaved = page.waitForResponse(
      (response) => response.url().includes('/air/expert/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-expert-grant-save').click()
    expect((await (await roleSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-expert-grant-row').filter({ hasText: '角色' })).toContainText('系统管理员')

    await drawer.getByTestId('air-expert-grant-type').selectOption('DEPT')
    await drawer.getByTestId('air-expert-grant-dept-search').fill('E2E内容作者')
    const orgUsers = page.waitForResponse((response) => response.url().includes('/auth/org/users'))
    await drawer.getByTestId('air-expert-grant-dept-find').click()
    await orgUsers
    await drawer.getByTestId('air-expert-grant-target').selectOption({ label: '部门#7301' })
    const deptSaved = page.waitForResponse(
      (response) => response.url().includes('/air/expert/grant') && response.request().method() === 'POST',
    )
    await drawer.getByTestId('air-expert-grant-save').click()
    expect((await (await deptSaved).json()).code).toBe(0)
    await expect(drawer.getByTestId('air-expert-grant-row').filter({ hasText: '部门' })).toContainText('部门#7301')
    await page.screenshot({ path: `${shotDir}/04-expert-grants.png`, fullPage: true })
    await drawer.getByTestId('air-expert-grant-close').click()
    await expect(card.getByTestId('air-expert-grant-count')).toHaveText('3')

    await page.goto('/ims/air/cfg?tab=audit')
    await expect(page.getByTestId('air-mcp-audit')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('air-mcp-tool').selectOption('experts.assemble')
    const audited = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await audited).json()).code).toBe(0)
    const logRow = page.locator('[data-testid="air-mcp-row"][data-tool="experts.assemble"][data-filter="1"]')
    await expect(logRow).toBeVisible()
    await expect(logRow.getByTestId('air-mcp-tool-cell')).toHaveText('experts.assemble')
    await expect(logRow.getByTestId('air-mcp-cost')).toHaveText('128 ms')
    await expect(logRow.getByTestId('air-mcp-token')).toHaveText('0')
    await expect(logRow.getByTestId('air-mcp-filter')).toHaveText('1')
    await expect(page.getByTestId('air-mcp-hint')).toContainText('不返回 knowledgeContext')
    await page.screenshot({ path: `${shotDir}/05-mcp-audit.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
