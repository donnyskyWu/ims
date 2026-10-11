import { test, expect } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.describe('采集与内部分析 BUG-B012–B028', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('阈值表单、非法 cron、重复标识与两边低分 Tab', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)

    await page.goto('/ims/collect/threshold')
    await expect(page.locator('h1')).toContainText('阈值规则')
    await page.getByTestId('threshold-create').click()
    await expect(page.getByTestId('threshold-form')).toBeVisible()
    await page.getByTestId('threshold-save').click()
    await expect(page.getByTestId('field-error').first()).toContainText('必填项，请填写')
    await page.getByTestId('threshold-name').fill('失败率规则')
    await page.getByTestId('threshold-metric').fill('fail_rate')
    await page.getByTestId('threshold-value').fill('abc')
    await page.getByTestId('threshold-save').click()
    await expect(page.getByTestId('field-error').first()).toContainText('数字')

    await page.goto('/ims/collect/task')
    await page.getByRole('button', { name: '新增单账号任务' }).click()
    await expect(page.getByTestId('task-type')).toBeVisible()
    await expect(page.getByTestId('task-form-platform')).not.toContainText('WECHAT_OFFICIAL')
    await expect(page.getByTestId('task-form-platform')).not.toContainText('XIAOHONGSHU')
    await page.getByTestId('task-form-name').fill('E2E非法cron')
    await page.getByTestId('task-form-cron').fill('abc')
    const account = page.getByTestId('task-account')
    if ((await account.locator('option').count()) > 1) {
      await account.selectOption({ index: 1 })
      await page.getByTestId('task-save').click()
      await expect(page.getByTestId('task-form-error')).toContainText('cron')
    } else {
      await page.getByTestId('task-save').click()
      await expect(page.getByTestId('field-error').first()).toContainText('必填项，请填写')
    }

    const stamp = Date.now().toString(36)
    await page.goto('/ims/collect/external/account')
    await page.getByTestId('acct-create').click()
    await page.getByTestId('acct-form-name').fill(`竞品${stamp}`)
    await page.getByTestId('acct-form-id').fill(`tb_comp_${stamp}`)
    await page.getByTestId('acct-save').click()
    await expect(page.getByTestId('app-toast')).toContainText('采集配置已保存')
    await page.getByTestId('acct-create').click()
    await page.getByTestId('acct-form-name').fill(`竞品重复${stamp}`)
    await page.getByTestId('acct-form-id').fill(`tb_comp_${stamp}`)
    await page.getByTestId('acct-save').click()
    await expect(page.getByTestId('acct-form-msg')).toContainText('已存在')

    await page.getByTestId('acct-import-open').click()
    await page.getByTestId('acct-import-submit').click()
    await expect(page.getByTestId('field-error')).toContainText('请先选择文件')

    await page.goto('/ims/int/work')
    const intLow = page.waitForResponse(
      (r) => r.url().includes('/int-analysis/work/page') && r.url().includes('LOW_SCORE'),
    )
    await page.getByRole('button', { name: '低分' }).click()
    expect(((await (await intLow).json()) as { code: number }).code).toBe(0)
    await expect(page.locator('body')).not.toContainText('网络错误')

    await page.goto('/ims/comp/work')
    const compLow = page.waitForResponse(
      (r) => r.url().includes('/comp-analysis/work/page') && r.url().includes('LOW_SCORE'),
    )
    await page.getByRole('button', { name: '低分' }).click()
    expect(((await (await compLow).json()) as { code: number }).code).toBe(0)
    await expect(page.locator('body')).not.toContainText('网络错误')
    const empty = page.locator('.empty .et')
    if (await empty.count()) {
      await expect(empty.first()).toHaveText('暂无竞品作品')
    }
  })
})
