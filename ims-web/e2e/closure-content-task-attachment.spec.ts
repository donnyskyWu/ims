import fs from 'fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createDraftPlanViaUi,
  createSopViaUi,
  loginAdmin,
  prepareIpGroupWithAdminMember,
  startPlanRowViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-108-screenshots'

/**
 * Checklist **E2E-S7** 切片（acceptance · 执行页附件上传 · **纯 UI**）
 * Given: UI 创建 SOP/IP 组/计划并启动
 * When: 执行页上传附件 → 保存 → 返回后再打开
 * Then: 执行人上传列表可见文件名；节点参考附件与之分开
 */
test.describe('content task attachment upload closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('upload attachment save then reopen shows userAttachments', async ({ page }) => {
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-task-file-${Date.now()}`
    const nodeName = `附件节点-${label}`
    const planName = `E2E 附件任务 ${label}`
    const fileName = `note-${label}.txt`

    await loginAdmin(page)
    const { sopId } = await createSopViaUi(page, { sopName: `E2E 附件 SOP ${label}`, nodeName })
    const { ipGroupId } = await prepareIpGroupWithAdminMember(page, label)
    await createDraftPlanViaUi(page, { planName, sopId, ipGroupId })

    await page.goto('/ims/content/plan')
    await startPlanRowViaUi(page, planName)

    await page.goto('/ims/content/task')
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const row = page.locator('tr', { hasText: nodeName }).first()
    await expect(row).toBeVisible({ timeout: 15_000 })
    await row.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    await expect(page.getByText('无参考附件')).toBeVisible()

    await page.getByTestId('task-attachment-file').setInputFiles({
      name: 'bad.exe',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('nope'),
    })
    await expect(page.getByTestId('task-attachment-error')).toHaveText('不支持的文件类型')
    await page.screenshot({ path: `${SHOTS}/01-reject-type.png`, fullPage: true })

    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/content/file/upload') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByTestId('task-attachment-file').setInputFiles({
      name: fileName,
      mimeType: 'text/plain',
      buffer: Buffer.from(`e2e attachment ${label}`),
    })
    const uploaded = (await (await uploadResp).json()) as { code: number; data?: { fileName?: string } }
    expect(uploaded.code).toBe(0)
    expect(uploaded.data?.fileName).toBe(fileName)
    await expect(page.getByTestId('task-user-attachments')).toContainText(fileName)
    await expect(page.getByTestId('task-ref-attachments')).not.toContainText(fileName)
    await page.screenshot({ path: `${SHOTS}/02-uploaded-before-save.png`, fullPage: true })

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/execute/save') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '保存' }).click()
    const saved = (await (await saveResp).json()) as {
      code: number
      data?: { userAttachments?: Array<{ fileName?: string }> }
    }
    expect(saved.code).toBe(0)
    expect(saved.data?.userAttachments?.[0]?.fileName).toBe(fileName)
    await expect(page.getByTestId('task-save-hint')).toHaveText('已保存')

    await page.getByRole('button', { name: '返回我的任务' }).click()
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const again = page.locator('tr', { hasText: nodeName }).first()
    await again.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    await expect(page.getByTestId('task-user-attachments')).toContainText(fileName, { timeout: 15_000 })
    await expect(page.getByText('无参考附件')).toBeVisible()
    await page.screenshot({ path: `${SHOTS}/03-reopen-visible.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
