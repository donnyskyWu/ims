import { expect, test } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test('竞品库录入、对比与监测页导出', async ({ page }) => {
  await loginAdmin(page)
  await page.goto('/ims/comp/library')
  await expect(page.getByRole('heading', { name: '竞品库' })).toBeVisible()

  await page.getByTestId('comp-add').click()
  await expect(page.getByTestId('comp-name')).toBeVisible()
  await page.getByTestId('comp-submit').click()
  await expect(page.getByText('必填项，请填写').first()).toBeVisible()
  await expect(page.getByText('1171 数据来源必填')).toBeVisible()

  const name = `E2E竞品${Date.now().toString().slice(-6)}`
  await page.getByTestId('comp-name').fill(name)
  await page.getByTestId('comp-platform').selectOption('DOUYIN')
  await page.getByTestId('comp-period').fill('2026-10')
  await page.getByTestId('comp-source').fill('公开主页')
  await page.getByTestId('comp-conclusion').fill('可借鉴选题节奏')
  await page.getByTestId('comp-submit').click()
  await expect(page.getByTestId('comp-lib-note')).toContainText('待初审')
  await expect(page.locator('.drawer.on').filter({ hasText: '仅可采集公开数据' })).toHaveCount(0)
  await expect(page.locator('.comp-card', { hasText: name })).toBeVisible()
  await page.getByTestId('comp-add').click()
  await expect(page.getByTestId('comp-name')).toHaveValue('')
  await expect(page.getByTestId('comp-source')).toHaveValue('')
  await expect(page.getByTestId('comp-conclusion')).toHaveValue('')
  await page.locator('.drawer.on').getByRole('button', { name: '取消' }).click()

  const seeded = ['悦跑圈', '咕咚运动', '刘畊宏', 'Keep 官方']
  const assetNos: string[] = []
  for (const seededName of seeded) {
    const text = await page.locator('.comp-card', { hasText: seededName }).innerText()
    const matched = text.match(/CP\d+/)
    assetNos.push(matched?.[0] || '')
  }
  expect(new Set(assetNos).size).toBe(seeded.length)

  await page.getByText('悦跑圈').click()
  await expect(page.getByTestId('comp-monitor-chip')).toBeVisible()
  await expect(page.getByTestId('comp-add-compare')).toBeVisible()
  await page.getByTestId('comp-add-compare').click()
  await expect(page.getByTestId('comp-lib-note')).toContainText('对比篮 1')
  await expect(page.getByTestId('comp-export-compare')).toBeEnabled()

  await page.goto('/ims/comp/work')
  await expect(page.getByTestId('comp-work-export')).toBeVisible()
  await expect(page.getByTestId('comp-work-type')).toBeVisible()
  await expect(page.getByTestId('comp-work-threshold')).toContainText('播放量')
  await expect(page.getByText('爆款总数')).toBeVisible()

  await page.goto('/ims/comp/account')
  await expect(page.getByTestId('comp-account-export')).toBeVisible()
  await expect(page.getByTestId('comp-account-platform').locator('option', { hasText: '公众号' })).toHaveCount(1)
  await expect(page.getByTestId('comp-account-platform').locator('option', { hasText: '视频号' })).toHaveCount(1)

  await page.goto('/ims/monitor/theme')
  await expect(page.getByTestId('mon-export')).toBeVisible()
  await expect(page.getByTestId('mon-ip-group')).toBeVisible()
  await page.getByTestId('mon-source-INTERNAL').click()
  await expect(page).toHaveURL(/\/ims\/monitor\/theme/)
  await expect(page.getByTestId('mon-source-INTERNAL')).toHaveClass(/on/)
})
