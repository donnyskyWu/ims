import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

const shotDir = '/opt/cursor/artifacts/e2e-237-screenshots'

/** #237 · 登记预校验、采购文件空态、未填规格、反查零命中文案 */
test.describe('corp asset register form edges and lookup empty copy', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('blocks blank name, long fields and bad session, then shows empty spec and unbound account', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)
    await page.goto('/ims/corp/device/office')
    await expect(page.locator('h1')).toHaveText('办公设备管理', { timeout: 15_000 })

    let ledgerPosts = 0
    page.on('request', (req) => {
      const url = req.url()
      if (req.method() === 'POST' && url.includes('/asset/ledger') && !url.includes('/import')) ledgerPosts += 1
    })

    await page.getByTestId('corp-asset-create-btn').click()
    const create = page.locator('.drawer.on').filter({ hasText: '资产登记' })
    await expect(create).toBeVisible()
    await expect(create.getByTestId('corp-asset-code-hint')).toHaveText('编号可留空，保存时自动生成。')
    await create.getByTestId('corp-asset-save').click()
    await expect(create.getByTestId('corp-asset-form-error')).toHaveText('资产名称必填')
    await page.screenshot({ path: `${shotDir}/01-name-required.png`, fullPage: true })

    const stamp = Date.now()
    await create.getByTestId('corp-asset-name').fill('名'.repeat(129))
    await create.getByTestId('corp-asset-save').click()
    await expect(create.getByTestId('corp-asset-form-error')).toHaveText('资产名称过长')

    await create.getByTestId('corp-asset-name').fill(`边角显示器-${stamp}`)
    await create.getByTestId('corp-asset-code').fill('C'.repeat(65))
    await create.getByTestId('corp-asset-save').click()
    await expect(create.getByTestId('corp-asset-form-error')).toHaveText('资产编号过长')

    await create.getByTestId('corp-asset-code').fill('')
    await create.getByTestId('corp-asset-spec').fill('规'.repeat(129))
    await create.getByTestId('corp-asset-save').click()
    await expect(create.getByTestId('corp-asset-form-error')).toHaveText('规格过长')
    await page.screenshot({ path: `${shotDir}/02-spec-too-long.png`, fullPage: true })

    await create.getByTestId('corp-asset-spec').fill('')
    await create.getByTestId('corp-asset-bind-session').fill('not-a-session')
    await create.getByTestId('corp-asset-save').click()
    await expect(create.getByTestId('corp-asset-form-error')).toHaveText('场次编号格式不正确')
    expect(ledgerPosts).toBe(0)
    await page.screenshot({ path: `${shotDir}/03-session-format.png`, fullPage: true })

    const person = create.getByTestId('corp-asset-realname')
    await expect.poll(async () => person.locator('option').count()).toBeGreaterThan(1)
    await person.selectOption({ index: 1 })
    await create.getByTestId('corp-asset-parent').fill('AS-PARENT-237')
    await expect(create.getByTestId('corp-asset-parent-note')).toHaveText('已填上级资产，实名人以上级资产为准。')
    await page.screenshot({ path: `${shotDir}/04-parent-overrides-person.png`, fullPage: true })
    await create.getByTestId('corp-asset-parent').fill('')
    await expect(create.getByTestId('corp-asset-parent-note')).toHaveCount(0)
    await person.selectOption('')
    await create.getByTestId('corp-asset-bind-session').fill('')

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/asset/ledger') && r.request().method() === 'POST' && !r.url().includes('/import') && r.status() === 200,
    )
    await create.getByTestId('corp-asset-save').click()
    const saved = (await (await saveResp).json()) as { code: number; data?: { assetCode?: string; spec?: string } }
    expect(saved.code).toBe(0)
    const code = saved.data?.assetCode || ''
    expect(code).toMatch(/^AS\d+/)
    expect(saved.data?.spec || '').toBe('')
    await expect(create).toBeHidden()
    expect(ledgerPosts).toBe(1)

    const row = page.locator('.tbl-wrap').first().locator('tbody tr', { hasText: code })
    await expect(row).toBeVisible()
    await row.getByTestId('corp-asset-detail-btn').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '资产详情' })
    await expect(detail.getByTestId('corp-asset-detail-spec-empty')).toHaveText('未填规格')
    await page.screenshot({ path: `${shotDir}/05-detail-spec-empty.png`, fullPage: true })
    await detail.getByRole('button', { name: '关闭' }).click()
    await expect(detail).toBeHidden()

    await page.getByTestId('corp-asset-import-btn').click()
    const importer = page.locator('.drawer.on').filter({ hasText: '采购导入' })
    await expect(importer.getByTestId('corp-asset-import-empty')).toHaveText('尚未选择 CSV 文件')
    await page.screenshot({ path: `${shotDir}/06-import-empty.png`, fullPage: true })
    await importer.getByTestId('corp-asset-import-file').setInputFiles({
      name: 'notes.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('hello'),
    })
    await importer.getByTestId('corp-asset-import-save').click()
    await expect(importer.getByTestId('corp-asset-import-form-error')).toHaveText('请上传 CSV 文件')
    await importer.getByTestId('corp-asset-import-file').setInputFiles({
      name: 'empty.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(''),
    })
    await importer.getByTestId('corp-asset-import-save').click()
    await expect(importer.getByTestId('corp-asset-import-form-error')).toHaveText('文件为空')
    await page.screenshot({ path: `${shotDir}/07-import-empty-file.png`, fullPage: true })
    await importer.getByRole('button', { name: '关闭' }).click()
    await expect(importer).toBeHidden()

    await page.getByTestId('corp-asset-entry-open').click()
    const entry = page.locator('.drawer.on').filter({ hasText: '账号/场次反查' })
    await entry.getByTestId('asset-entry-account-no').fill('AC-E2E-ASSET-OFF')
    const emptyQuery = page.waitForResponse(
      (r) => r.url().includes('/asset/reverse/by-account/0') && r.request().method() === 'GET' && r.status() === 200,
    )
    await entry.getByTestId('asset-entry-query').click()
    expect((await (await emptyQuery).json() as { code: number }).code).toBe(0)
    await expect(entry.getByTestId('asset-entry-empty')).toHaveText('该账号没有绑定资产')
    await page.screenshot({ path: `${shotDir}/08-account-unbound.png`, fullPage: true })
    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
