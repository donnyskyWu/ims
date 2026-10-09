import { expect, test, type Page } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * S10 资料列表筛选（#157 · 纯 UI）
 * 标题 / 类型 / 状态 / 岗位 / 分类筛选，无命中时给出空状态并可清除。
 */
test.describe('train material list filters', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filter by title type status position and show empty state', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    const token = `flt${Date.now()}`
    const docTitle = `筛选文档 ${token}`
    const linkTitle = `筛选外链 ${token}`

    await loginAdmin(page)
    await page.goto('/ims/train/material')
    await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })

    await pickCate(page, '开播手册')
    await uploadMaterial(page, { title: docTitle, publish: true })
    const docRow = page.locator('tr', { hasText: docTitle })
    await expect(docRow).toBeVisible({ timeout: 15_000 })
    await expect(docRow.getByTestId('train-material-position')).toHaveText('R5')
    await expect(docRow.getByTestId('train-material-status')).toContainText('已发布')

    await pickCate(page, 'SOP与规范')
    await uploadMaterial(page, {
      title: linkTitle,
      materialType: 'LINK',
      linkUrl: 'https://example.com/train-filter',
      publish: false,
    })
    const linkRow = page.locator('tr', { hasText: linkTitle })
    await expect(linkRow).toBeVisible({ timeout: 15_000 })
    await expect(linkRow.getByTestId('train-material-status')).toContainText('草稿')
    await expect(linkRow.getByTestId('train-material-position')).toHaveText('R6')

    await queryWith(page, async () => {
      await page.getByTestId('train-filter-reset').click()
    })
    await page.getByTestId('train-filter-title').fill(token)
    await queryWith(page, async () => {
      await page.getByRole('button', { name: '查询' }).click()
    })
    await expect(page.locator('tr', { hasText: docTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: linkTitle })).toBeVisible()
    await expect(page.getByTestId('train-filter-summary')).toContainText(`标题「${token}」`)
    await expect(page.getByTestId('train-material-total')).toHaveText('共 2 条')
    await page.screenshot({
      path: '/opt/cursor/artifacts/train-material-filters-matched.png',
      fullPage: true,
    })

    await page.getByTestId('train-filter-type').selectOption('LINK')
    await queryWith(page, async () => {
      await page.getByRole('button', { name: '查询' }).click()
    })
    await expect(page.locator('tr', { hasText: linkTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: docTitle })).toHaveCount(0)
    await expect(page.getByTestId('train-filter-summary')).toContainText('外链')

    await queryWith(page, async () => {
      await page.getByTestId('train-filter-reset').click()
    })
    await page.getByTestId('train-filter-title').fill(token)
    await page.getByTestId('train-filter-status').selectOption('DRAFT')
    await queryWith(page, async () => {
      await page.getByRole('button', { name: '查询' }).click()
    })
    await expect(page.locator('tr', { hasText: linkTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: docTitle })).toHaveCount(0)
    await expect(page.locator('tr', { hasText: linkTitle }).getByTestId('train-material-status')).toContainText('草稿')

    await page.getByTestId('train-filter-status').selectOption('')
    await page.getByTestId('train-filter-position').selectOption('R5')
    await queryWith(page, async () => {
      await page.getByRole('button', { name: '查询' }).click()
    })
    await expect(page.locator('tr', { hasText: docTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: linkTitle })).toHaveCount(0)
    await expect(page.getByTestId('train-filter-summary')).toContainText('岗位 R5')

    await page.getByTestId('train-filter-title').fill(`不存在${token}`)
    await queryWith(page, async () => {
      await page.getByRole('button', { name: '查询' }).click()
    })
    await expect(page.getByTestId('train-material-empty')).toContainText('没有符合筛选的资料')
    await expect(page.getByTestId('train-material-total')).toHaveText('共 0 条')
    await page.screenshot({
      path: '/opt/cursor/artifacts/train-material-filters-empty.png',
      fullPage: true,
    })

    await queryWith(page, async () => {
      await page.getByTestId('train-filter-clear-empty').click()
    })
    await expect(page.getByTestId('train-filter-summary')).toHaveCount(0)
    await expect(page.locator('tr', { hasText: docTitle })).toBeVisible()

    await pickCate(page, '开播手册')
    await expect(page.getByTestId('train-filter-summary')).toContainText('分类 开播手册')
    await expect(page.locator('[data-testid="train-cate-node"].on')).toContainText('开播手册')
    await page.screenshot({
      path: '/opt/cursor/artifacts/train-material-filters-cate.png',
      fullPage: true,
    })
    await queryWith(page, async () => {
      await page.getByTestId('train-filter-reset').click()
    })
    await expect(page.getByTestId('train-filter-summary')).toHaveCount(0)
    await expect(page.locator('[data-testid="train-cate-node"].on')).toHaveCount(0)

    expect(pageErrors).toEqual([])
  })
})

async function pickCate(page: Page, name: string) {
  const node = page.getByTestId('train-cate-node').filter({ hasText: name })
  await expect(node).toBeVisible({ timeout: 15_000 })
  const resp = page.waitForResponse(
    (r) => r.url().includes('/train/material/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await node.click()
  await resp
}

async function uploadMaterial(
  page: Page,
  opts: { title: string; materialType?: string; linkUrl?: string; publish: boolean },
) {
  await page.getByRole('button', { name: '上传资料' }).click()
  const modal = page.locator('.modal-mask .card').filter({ hasText: '上传资料' })
  await expect(modal).toBeVisible()
  await modal
    .locator('label.fld', { hasText: '标题' })
    .locator('xpath=following-sibling::input[1]')
    .fill(opts.title)
  if (opts.materialType === 'LINK') {
    await modal.getByTestId('train-form-type').selectOption('LINK')
    await modal.getByTestId('train-form-link').fill(opts.linkUrl || 'https://example.com/train-filter')
  }
  const createResp = page.waitForResponse(
    (r) => r.url().includes('/train/material') && r.request().method() === 'POST' && r.status() === 200,
  )
  await modal.getByRole('button', { name: opts.publish ? '发布' : '草稿' }).click()
  const body = (await (await createResp).json()) as { code: number }
  expect(body.code).toBe(0)
  await expect(modal).toBeHidden()
}

async function queryWith(page: Page, action: () => Promise<void>) {
  const resp = page.waitForResponse(
    (r) => r.url().includes('/train/material/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await action()
  await resp
}
