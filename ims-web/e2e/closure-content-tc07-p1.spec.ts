import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * TC-07 P1：B001/B002 SOP 画布与启停，B004/B005 公推导入与复制删除，B007/B008 内容批量与提审。
 * 纯 UI。不覆盖 B003/B006/B009/B010。
 */
test.describe('content TC-07 P1', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('sop editor, status switch, layout import, and content batch', async ({ page }) => {
    test.setTimeout(180_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const sopName = `TC07-SOP-${stamp}`
    const layoutName = `TC07-版式-${stamp}`
    const contentTitle = `TC07-内容-${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/content/sop')
    await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })
    await page.getByRole('button', { name: '新增模板' }).click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '新增 SOP 模板' })
    await expect(drawer.getByTestId('sop-platform').locator('option')).toHaveText([
      '抖音',
      '快手',
      '视频号',
      '微信公众号',
      '全平台',
    ])
    await expect(drawer.getByTestId('sop-node-doc-type')).toBeVisible()
    await expect(drawer.getByTestId('sop-auto-layout')).toBeVisible()
    await expect(drawer.getByTestId('sop-fit-view')).toBeVisible()
    await expect(drawer.getByTestId('sop-validate-dag')).toBeVisible()
    await expect(drawer.getByTestId('sop-save')).toHaveText('保存为新版本')
    await expect(drawer.getByTestId('sop-content-type')).toHaveValue('')
    await expect(drawer.getByTestId('sop-content-type').locator('option:not([value=""])')).toHaveText([
      '文章',
      '短视频',
      '视频',
    ])

    await drawer.getByTestId('sop-save').click()
    await expect(drawer.getByTestId('sop-name-error')).toHaveText('请填写 SOP 名称')
    await expect(drawer.getByTestId('sop-type-error')).toHaveText('必填')

    await drawer.getByTestId('sop-name').fill(sopName)
    await expect(drawer.getByTestId('sop-name-error')).toHaveCount(0)
    await expect(drawer.getByTestId('sop-dag-error')).toHaveCount(0)
    await drawer.getByTestId('sop-save').click()
    await expect(drawer.getByTestId('sop-type-error')).toHaveText('必填')
    await drawer.getByTestId('sop-content-type').selectOption('SHORT_VIDEO')
    await drawer.locator('.fld').filter({ hasText: '首节点类型' }).locator('select').selectOption('CONTENT_GENERATION')
    await drawer.getByTestId('sop-node-doc-type').selectOption('')
    await drawer.getByTestId('sop-validate-dag').click()
    await expect(drawer.getByTestId('sop-dag-toast')).toContainText('文档类型')
    await expect(drawer.getByTestId('sop-save')).toBeDisabled()

    await drawer.getByTestId('sop-node-doc-type').selectOption('COPY')
    await drawer.getByTestId('sop-validate-dag').click()
    await expect(drawer.getByTestId('sop-dag-toast')).toHaveText('DAG 校验通过（无环 · 岗位/文档类型完备）')
    await drawer.getByTestId('sop-auto-layout').click()
    await expect(drawer.getByTestId('sop-dag-toast')).toHaveText('已按依赖层级自动布局')
    await drawer.getByTestId('sop-fit-view').click()
    await expect(drawer.getByTestId('sop-dag-toast')).toHaveText('已适配视图')

    const createResp = page.waitForResponse(
      (r) => r.url().includes('/content/sop') && r.request().method() === 'POST' && r.status() === 200,
    )
    await drawer.getByTestId('sop-save').click()
    expect(((await (await createResp).json()) as { code: number }).code).toBe(0)

    const sopRow = page.locator('tr', { hasText: sopName }).first()
    await expect(sopRow).toBeVisible({ timeout: 15_000 })
    await sopRow.getByRole('button', { name: '编辑' }).click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑 SOP 模板' })
    await expect(editDrawer.getByTestId('sop-content-type')).toHaveValue('SHORT_VIDEO')
    await expect(editDrawer.getByTestId('sop-content-type').locator('option:checked')).toHaveText('短视频')
    await editDrawer.getByRole('button', { name: '取消' }).click()
    await expect(sopRow.getByTestId('sop-status-text')).toHaveText('ENABLED', { timeout: 15_000 })
    const offResp = page.waitForResponse(
      (r) => r.url().includes('/status') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await sopRow.getByTestId('sop-status-switch').click()
    expect(((await (await offResp).json()) as { code: number }).code).toBe(0)
    await expect(sopRow.getByTestId('sop-status-text')).toHaveText('DISABLED')

    await page.goto('/ims/content/plan')
    await expect(page.locator('h1')).toHaveText('计划管理', { timeout: 15_000 })
    const sopList = page.waitForResponse(
      (r) => r.url().includes('/content/sop/list') && r.url().includes('ENABLED') && r.status() === 200,
    )
    await page.getByRole('button', { name: '新增计划' }).click()
    await sopList
    const planDrawer = page.locator('.drawer.on').filter({ hasText: '新增计划' })
    await expect(planDrawer.getByText('SOP 模板（启用）')).toBeVisible()
    await expect(planDrawer.getByTestId('plan-sop-enabled')).not.toContainText(sopName)
    await planDrawer.getByRole('button', { name: '取消' }).click()

    await page.goto('/ims/content/layout-template')
    await expect(page.locator('h1')).toHaveText('公推模板库', { timeout: 15_000 })
    await page.getByTestId('layout-import-open').click()
    const wizard = page.getByTestId('layout-import')
    await wizard.getByTestId('layout-import-submit').click()
    await expect(wizard.getByTestId('layout-import-error')).toHaveText('必填项，请填写')
    await wizard.getByTestId('layout-import-url').fill('https://mp.weixin.qq.com/s/tc07')
    const urlResp = page.waitForResponse((r) => r.url().includes('/import-url') && r.request().method() === 'POST')
    await wizard.getByTestId('layout-import-submit').click()
    await urlResp
    await expect(wizard.getByTestId('layout-import-error')).toContainText('MHTML')

    await wizard.getByTestId('layout-import-tab-mhtml').click()
    await wizard.getByTestId('layout-import-submit').click()
    await expect(wizard.getByTestId('layout-import-error')).toHaveText('必填项，请填写')

    await wizard.getByTestId('layout-import-tab-html').click()
    await wizard.getByTestId('layout-import-submit').click()
    await expect(wizard.getByTestId('layout-import-error')).toHaveText('必填项，请填写')
    await wizard.getByTestId('layout-import-name').fill(layoutName)
    await wizard.getByTestId('layout-import-html').fill('<p>TC07 导入</p>')
    const pasteResp = page.waitForResponse(
      (r) => r.url().includes('/import-paste') && r.request().method() === 'POST' && r.status() === 200,
    )
    await wizard.getByTestId('layout-import-submit').click()
    const pasted = (await (await pasteResp).json()) as { code: number; data?: { template?: { status?: string } } }
    expect(pasted.code).toBe(0)
    expect(pasted.data?.template?.status).toBe('DRAFT')
    const templateTable = page.getByTestId('layout-template-table')
    const imported = templateTable.locator('tr', { hasText: layoutName }).first()
    await expect(imported).toContainText('DRAFT')
    await expect(imported).toContainText('IMPORT')
    await expect(page.getByTestId('layout-toast')).toHaveText('导入成功')
    await expect(page.getByTestId('layout-import-jobs')).toContainText(layoutName)

    const preset = templateTable.locator('tr', { hasText: 'PRESET' }).first()
    await expect(preset.getByRole('button', { name: '编辑' })).toHaveCount(0)
    await expect(preset.getByTestId('layout-delete')).toHaveCount(0)
    const presetName = (await preset.getByTestId('layout-name').innerText()).trim()
    await preset.getByTestId('layout-view').click()
    await expect(page.getByTestId('layout-view-dialog')).toContainText('只读')
    await page.getByTestId('layout-view-dialog').getByRole('button', { name: '关闭' }).click()
    await preset.getByTestId('layout-copy').click()
    const copyRow = page.locator('tr', { hasText: `${presetName}（副本）` }).first()
    await expect(copyRow).toBeVisible({ timeout: 15_000 })
    await expect(copyRow).toContainText('DRAFT')

    await imported.getByTestId('layout-delete').click()
    await page.getByTestId('layout-delete-ok').click()
    await expect(page.getByTestId('layout-toast')).toHaveText('删除成功')
    await expect(templateTable.locator('tr', { hasText: layoutName })).toHaveCount(0)

    await page.goto('/ims/content/list')
    await expect(page.locator('h1')).toHaveText('内容管理', { timeout: 15_000 })
    await expect(page.getByTestId('content-export')).toBeVisible()
    await expect(page.getByTestId('content-create')).toBeVisible()
    await expect(page.getByRole('button', { name: '新增内容' })).toBeVisible()
    await page.getByTestId('content-batch-delete').click()
    await expect(page.getByTestId('content-batch-msg')).toHaveText('请先勾选要删除的内容')
    await page.getByTestId('content-batch-submit').click()
    await expect(page.getByTestId('content-batch-msg')).toHaveText('请先勾选要提交的内容')
    await page.getByTestId('content-batch-kb').click()
    await expect(page.getByTestId('content-batch-msg')).toHaveText('请先勾选要转入知识库的内容')

    await page.getByTestId('content-create').click()
    const contentDrawer = page.locator('.drawer.on').filter({ hasText: '新增内容' })
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    await expect(contentDrawer.getByTestId('content-title-error')).toHaveText('必填项，请填写')
    await contentDrawer.getByTestId('content-submit-review').click()
    await expect(contentDrawer.getByTestId('content-submit-hint')).toHaveText('请先保存内容')

    await contentDrawer.getByTestId('content-edit-title').fill(contentTitle)
    const saveResp = page.waitForResponse(
      (r) => r.url().endsWith('/content') && r.request().method() === 'POST' && r.status() === 200,
    )
    await contentDrawer.getByRole('button', { name: '保存' }).click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    const contentRow = page.locator('tr', { hasText: contentTitle }).first()
    await expect(contentRow).toBeVisible({ timeout: 15_000 })

    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('content-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain('content.csv')
    await expect(page.getByTestId('content-export-note')).toContainText('已导出')

    await contentRow.getByTestId('content-row-check').check()
    await page.getByTestId('content-batch-delete').click()
    await expect(page.locator('tr', { hasText: contentTitle })).toHaveCount(0)

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })

  test('content nav hides topic and publish but routes stay', async ({ page }) => {
    test.setTimeout(60_000)
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)
    await page.goto('/ims/content/sop')
    await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })
    const contentNav = page.locator('.nav-sub-g', { hasText: '内容生产' })
    await expect(contentNav.locator('.nav-item.sub')).toHaveText([
      'SOP管理',
      '计划管理',
      '工作任务登记',
      '我的任务',
      '内容管理',
      '公推模板库',
      '内容审核',
    ])
    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })
    await page.goto('/ims/content/publish')
    await expect(page.locator('h1')).toHaveText('发布管理', { timeout: 15_000 })
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
