import { expect, test } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

test('会议预约空表单提示必填，日报填写页有类型且正文可直接提交', async ({ page }) => {
  const pageErrors = attachClosurePageHooks(page)
  await loginAdmin(page)
  await expect(page.locator('.nc', { hasText: '03 MEET' })).toHaveCount(0)

  await page.goto('/ims/meet/minutes')
  await expect(page.getByTestId('meet-book')).toBeVisible()
  await expect(page.getByTestId('meet-timeline')).toBeVisible()
  await page.getByTestId('meet-book').click()
  await page.getByTestId('meet-submit').click()
  await expect(page.getByTestId('meet-book-form')).toContainText('必填项，请填写')

  await page.goto('/ims/meet/daily')
  await expect(page.getByRole('option', { name: '已退回' })).toHaveCount(0)
  await page.goto('/ims/meet/daily/team')
  await expect(page.getByRole('option', { name: '已退回' })).toHaveCount(0)

  await page.goto('/ims/meet/daily/submit')
  await expect(page.getByTestId('daily-type')).toBeVisible()
  await expect(page.getByText('今日完成 *')).toBeVisible()
  await expect(page.getByText('明日计划 *')).toHaveCount(0)
  await page.getByTestId('daily-submit').click()
  await expect(page.getByTestId('daily-msg')).toContainText('必填项，请填写')

  expect(pageErrors).toEqual([])
})
