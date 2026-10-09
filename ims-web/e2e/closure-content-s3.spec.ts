import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  createWorkTaskSopViaUi,
  E2E_OPS_AUTHOR_ID,
  fillMatchSchemeViaUi,
  loginAdmin,
  loginAs,
  passContentReviewViaUi,
  prepareIpGroupWithAdminMember,
  registerWorkTaskRowViaUi,
} from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-105-screenshots'

test.describe('content S3 task and list closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(shotDir, { recursive: true })
  })

  test('content list create edit submit and delete', async ({ page }) => {
    test.setTimeout(90_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-s3-list-${Date.now()}`
    const title = `E2E 内容 ${label}`
    const edited = `${title} 改`
    const dropTitle = `E2E 待删 ${label}`

    await loginAdmin(page)
    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })

    await page.getByRole('button', { name: '新增内容' }).click()
    const createDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await createDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(title)
    await createDrawer.locator('.fld').filter({ hasText: '正文' }).locator('textarea').fill(`正文 ${label}`)
    await fillMatchSchemeViaUi(createDrawer, { matchId: '9001', homeName: '主队', awayName: '客队' })
    await page.screenshot({ path: `${shotDir}/02-content-edit-scheme.png`, fullPage: true })
    const createResp = page.waitForResponse(
      (r) => /\/content$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST' && r.status() === 200,
    )
    await createDrawer.getByRole('button', { name: '保存' }).click()
    const createBody = (await (await createResp).json()) as { code: number }
    expect(createBody.code).toBe(0)

    const row = page.locator('tr', { hasText: title })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('主队 VS 客队')
    await expect(row).toContainText('DRAFT')
    await page.screenshot({ path: `${shotDir}/01-content-list-created.png`, fullPage: true })

    await row.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑内容' })
    await editDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(edited)
    const updateResp = page.waitForResponse(
      (r) => /\/content\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await updateResp).json()) as { code: number }).code).toBe(0)
    const editedRow = page.locator('tr', { hasText: edited })
    await expect(editedRow).toBeVisible({ timeout: 15_000 })
    await expect(editedRow).toContainText('主队 VS 客队')

    const submitResp = page.waitForResponse(
      (r) => r.url().includes('/submit-review') && r.request().method() === 'POST' && r.status() === 200,
    )
    await editedRow.getByRole('button', { name: '提审' }).click()
    expect(((await (await submitResp).json()) as { code: number }).code).toBe(0)
    await expect(editedRow).toContainText('PENDING_REVIEW', { timeout: 15_000 })
    await expect(editedRow.getByRole('button', { name: '删除' })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/03-content-submitted.png`, fullPage: true })

    await page.getByRole('button', { name: '新增内容' }).click()
    const dropDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await dropDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input').fill(dropTitle)
    const dropResp = page.waitForResponse(
      (r) => /\/content$/.test(new URL(r.url()).pathname) && r.request().method() === 'POST' && r.status() === 200,
    )
    await dropDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await dropResp).json()) as { code: number }).code).toBe(0)
    const dropRow = page.locator('tr', { hasText: dropTitle })
    await expect(dropRow).toBeVisible({ timeout: 15_000 })
    const deleteResp = page.waitForResponse(
      (r) => /\/content\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'DELETE' && r.status() === 200,
    )
    await dropRow.getByRole('button', { name: '删除' }).click()
    expect(((await (await deleteResp).json()) as { code: number }).code).toBe(0)
    await expect(page.locator('tr', { hasText: dropTitle })).toHaveCount(0)
    await expect(page.locator('tr', { hasText: edited })).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('my task execute submit blocked until review then complete', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-s3-task-${Date.now()}`
    const nodeName = `写文案-${label}`
    const contentTitle = `E2E 任务文案 ${label}`
    const workDate = new Date().toISOString().slice(0, 10)
    const competitionName = `周末赛-${label}`

    await loginAdmin(page)
    await createWorkTaskSopViaUi(page, {
      sopName: `E2E S3 SOP ${label}`,
      nodeName,
      marketingPlan: 'LIVE_PUBLIC',
    })
    const { ipGroupId, groupName } = await prepareIpGroupWithAdminMember(page, label, true, E2E_OPS_AUTHOR_ID)
    await registerWorkTaskRowViaUi(page, {
      ipGroupId,
      workDate,
      authorId: E2E_OPS_AUTHOR_ID,
      competitionId: `M-${label}`,
      competitionName,
      groupNameHint: groupName,
    })

    await page.goto('/ims/content/task')
    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const taskRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(taskRow).toBeVisible({ timeout: 15_000 })
    const listComplete = taskRow.getByRole('button', { name: '完成' })
    await expect(listComplete).toBeDisabled()
    await expect(listComplete).toHaveAttribute('title', '内容须审核通过后方可完成任务')
    await expect(taskRow.getByRole('button', { name: '提交审核' })).toBeVisible()

    await taskRow.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    const completeBtn = page.locator('.acts').getByRole('button', { name: '完成' })
    await expect(completeBtn).toBeDisabled()
    await expect(page.getByText('内容须审核通过后方可完成任务')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/04-task-execute-gate.png`, fullPage: true })

    await page.getByRole('button', { name: '进入内容创作' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '内容编辑' })
    const titleInput = editDrawer.locator('.fld').filter({ hasText: '标题' }).locator('input')
    await expect(titleInput).toHaveValue(/LIVE_PUBLIC/)
    await titleInput.fill(contentTitle)
    await fillMatchSchemeViaUi(editDrawer, { matchId: '1002', homeName: '申花', awayName: '海港' })
    const saveResp = page.waitForResponse(
      (r) => /\/content\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editDrawer.getByRole('button', { name: '保存内容' }).click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    await expect(page.getByText(contentTitle)).toBeVisible({ timeout: 15_000 })

    const submitResp = page.waitForResponse(
      (r) => r.url().includes('/submit-review') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交审核' }).click()
    expect(((await (await submitResp).json()) as { code: number }).code).toBe(0)
    await expect(completeBtn).toBeDisabled()
    await expect(page.getByText('内容须审核通过后方可完成任务')).toBeVisible()

    await loginAs(page, 'e2e_author')
    await passContentReviewViaUi(page, { title: contentTitle, stageTab: '一级审核' })
    await passContentReviewViaUi(page, { title: contentTitle, stageTab: '二级审核' })

    await loginAdmin(page)
    await page.goto('/ims/content/task')
    const readyRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(readyRow).toBeVisible({ timeout: 15_000 })
    await expect(readyRow.getByRole('button', { name: '完成' })).toBeEnabled()
    await readyRow.getByRole('button', { name: '执行' }).click()
    await expect(page.locator('h1')).toHaveText('任务执行', { timeout: 15_000 })
    const doneBtn = page.locator('.acts').getByRole('button', { name: '完成' })
    await expect(doneBtn).toBeEnabled({ timeout: 15_000 })
    await doneBtn.click()

    await expect(page.locator('h1')).toHaveText('我的任务', { timeout: 15_000 })
    const doneRow = page.locator('tr', { hasText: nodeName }).filter({ hasText: competitionName }).first()
    await expect(doneRow).toContainText('DONE', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/05-task-done.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('layout template preview edit and reenable', async ({ page }) => {
    test.setTimeout(60_000)
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-s3-lt-${Date.now()}`
    const name = `S3 模板 ${label}`
    const renamed = `${name} 改`

    await loginAdmin(page)
    await page.goto('/ims/content/layout')
    await expect(page.locator('h1')).toHaveText('公推模板库', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建模板' }).click()
    const createModal = page.locator('.modal-mask').filter({ hasText: '新建公推模板' })
    await createModal.locator('input').fill(name)
    await createModal.locator('textarea').fill(`<p>${label}</p>`)
    await createModal.getByRole('button', { name: '保存' }).click()

    const row = page.locator('tr', { hasText: name })
    await expect(row).toBeVisible({ timeout: 15_000 })
    await expect(row).toContainText('DRAFT')
    await row.getByRole('button', { name: '预览' }).click()
    const preview = page.locator('.modal-mask').filter({ hasText: '预览' })
    await expect(preview.locator('iframe')).toBeVisible()
    await page.screenshot({ path: `${shotDir}/06-layout-preview.png`, fullPage: true })
    await preview.getByRole('button', { name: '关闭' }).click()

    await row.getByRole('button', { name: '编辑' }).click()
    const editModal = page.locator('.modal-mask').filter({ hasText: '编辑公推模板' })
    await editModal.locator('input').fill(renamed)
    await editModal.getByRole('button', { name: '保存' }).click()
    const renamedRow = page.locator('tr', { hasText: renamed })
    await expect(renamedRow).toBeVisible({ timeout: 15_000 })

    await renamedRow.getByRole('button', { name: '发布' }).click()
    await expect(renamedRow).toContainText('ENABLED', { timeout: 15_000 })
    await renamedRow.getByRole('button', { name: '停用' }).click()
    await expect(renamedRow).toContainText('DISABLED', { timeout: 15_000 })
    await renamedRow.getByRole('button', { name: '重新启用' }).click()
    await expect(renamedRow).toContainText('ENABLED', { timeout: 15_000 })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
