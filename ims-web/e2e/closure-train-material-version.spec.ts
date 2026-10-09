import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createTrainMaterialViaUi, createTrainTaskViaUi, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-126-screenshots'

/**
 * #126 · TRAIN-001/002 纯 UI
 * 资料更新生成 V2 且详情留 V1；新资料不进本周未更新清单；
 * 截止前改任务名，学习记录仍在；把截止改到过去返回 1102。
 */
test.describe('train material version and task edit closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('publish then revise material and keep the previous version', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-mat-${Date.now()}`
    const materialTitle = `E2E 资料原文 ${label}`
    const revisedTitle = `E2E 资料修订 ${label}`

    await loginAdmin(page)
    await createTrainMaterialViaUi(page, { title: materialTitle })

    const rate = page.getByTestId('train-weekly-rate')
    await expect(rate).toBeVisible()
    await expect(rate).toContainText('周更新率')
    await page.getByTestId('train-unupdated-open').click()
    const unupdated = page.getByTestId('train-unupdated-drawer')
    await expect(unupdated).toBeVisible()
    await expect(unupdated).not.toContainText(materialTitle)
    await unupdated.getByRole('button', { name: '关闭' }).click()
    await page.screenshot({ path: `${shotDir}/01-weekly-rate.png`, fullPage: true })

    const row = page.locator('tr', { hasText: materialTitle })
    await expect(row.getByTestId('train-material-version')).toHaveText('V1')
    await row.getByTestId('train-material-edit').click()
    const editor = page.locator('.modal-mask .card').filter({ hasText: '更新资料' })
    await expect(editor).toContainText('将生成新版本 V2，旧版本留档')
    await editor.locator('label.fld', { hasText: '标题' }).locator('xpath=following-sibling::input[1]').fill(revisedTitle)
    const updateResp = page.waitForResponse(
      (r) => r.url().includes('/train/material/') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editor.getByRole('button', { name: '保存新版本' }).click()
    const updated = (await (await updateResp).json()) as { code: number; data?: { version?: number } }
    expect(updated.code).toBe(0)
    expect(updated.data?.version).toBe(2)

    const revised = page.locator('tr', { hasText: revisedTitle })
    await expect(revised.getByTestId('train-material-version')).toHaveText('V2')
    await revised.getByTestId('train-material-detail').click()
    const history = page.getByTestId('train-version-history')
    await expect(history).toContainText('V1')
    await expect(history).toContainText(materialTitle)
    await page.screenshot({ path: `${shotDir}/02-version-history.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })

  test('edit an open task without dropping the study record', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const label = `e2e-task-${Date.now()}`
    const materialTitle = `E2E 任务资料 ${label}`
    const taskName = `E2E 任务原文 ${label}`
    const renamed = `E2E 任务修订 ${label}`

    await loginAdmin(page)
    const { materialId } = await createTrainMaterialViaUi(page, { title: materialTitle })
    await createTrainTaskViaUi(page, {
      taskName,
      materialIds: [materialId],
      assignUserIds: [1],
    })

    const row = page.locator('tr', { hasText: taskName })
    await row.getByTestId('train-task-edit').click()
    const editor = page.locator('.modal-mask .card').filter({ hasText: '编辑学习任务' })
    await expect(editor).toContainText('已产生的学习记录不会回滚')
    await editor.locator('label.fld', { hasText: '任务名称' }).locator('xpath=following-sibling::input[1]').fill(renamed)
    const saveResp = page.waitForResponse(
      (r) => /\/train\/task\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await editor.getByRole('button', { name: '保存' }).click()
    const saved = (await (await saveResp).json()) as { code: number; data?: { taskName?: string } }
    expect(saved.code).toBe(0)
    expect(saved.data?.taskName).toBe(renamed)

    const renamedRow = page.locator('tr', { hasText: renamed })
    await expect(renamedRow).toBeVisible()
    await renamedRow.getByRole('button', { name: '学习记录' }).click()
    await expect(page.getByText('NOT_CONFIRMED')).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: '关闭' }).click()
    await page.screenshot({ path: `${shotDir}/03-task-edited.png`, fullPage: true })

    await renamedRow.getByTestId('train-task-edit').click()
    const again = page.locator('.modal-mask .card').filter({ hasText: '编辑学习任务' })
    await again
      .locator('label.fld', { hasText: '截止时间 ISO' })
      .locator('xpath=following-sibling::input[1]')
      .fill('2020-01-01T00:00:00+08:00')
    const blockedResp = page.waitForResponse(
      (r) => /\/train\/task\/\d+$/.test(new URL(r.url()).pathname) && r.request().method() === 'PUT' && r.status() === 200,
    )
    await again.getByRole('button', { name: '保存' }).click()
    const blocked = (await (await blockedResp).json()) as { code: number; msg?: string }
    expect(blocked.code).toBe(1102)
    await expect(page.getByTestId('train-task-form-error')).toContainText('截止时间早于当前时间')
    await page.screenshot({ path: `${shotDir}/04-deadline-blocked.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
