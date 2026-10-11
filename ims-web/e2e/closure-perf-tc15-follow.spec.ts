import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * TC-15 续：C004 岗位名、C007 同周期拦截、C008 按指标调整、C013 结果页卡片。
 * C011 确认弹窗与三档分档在此一并核对（规格禁止 S～D）。
 */
test.describe('perf TC-15 follow-up', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('position name, duplicate period, line adjust, result board', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    const stamp = Date.now()
    const month = String((stamp % 12) + 1).padStart(2, '0')
    const year = 2036 + (stamp % 3)
    const periodStart = `${year}-${month}-01`
    const periodEnd = `${year}-${month}-28`
    const schemeName = `TC15续${stamp}`

    await loginAdmin(page)
    await page.goto('/ims/perf/scheme')
    await expect(page.locator('h1')).toHaveText('考核方案', { timeout: 15_000 })
    await page.getByRole('button', { name: '新建方案' }).click()
    const schemeModal = page.locator('.modal.card').filter({ hasText: '新建考核方案' })
    await expect(schemeModal.getByText('适用部门')).toHaveCount(0)
    await expect(schemeModal.locator('option', { hasText: '短视频运营 R6' })).toHaveCount(1)
    await schemeModal.locator('input').first().fill(schemeName)
    const schemeResp = page.waitForResponse(
      (r) => r.url().includes('/perf/scheme') && r.request().method() === 'POST' && r.status() === 200,
    )
    await schemeModal.getByRole('button', { name: '保存' }).click()
    const schemeBody = (await (await schemeResp).json()) as { code: number; data?: { id: number } }
    expect(schemeBody.code).toBe(0)
    const schemeId = schemeBody.data!.id

    await page.goto(`/ims/perf/execution?schemeId=${schemeId}`)
    const execModal = page.locator('.modal.card').filter({ hasText: '创建考核' })

    async function fillCreate() {
      await expect(execModal).toBeVisible({ timeout: 15_000 })
      await execModal.locator('input[type="number"]').first().fill(String(schemeId))
      await execModal.locator('input[type="number"]').nth(1).fill('1')
      await execModal.locator('select').first().selectOption('MONTHLY')
      await execModal.locator('.fld').filter({ hasText: '周期开始' }).locator('input').fill(periodStart)
      await execModal.locator('.fld').filter({ hasText: '周期结束' }).locator('input').fill(periodEnd)
    }

    await fillCreate()
    const createdResp = page.waitForResponse(
      (r) => r.url().includes('/perf/execution') && r.request().method() === 'POST' && r.status() === 200,
    )
    await execModal.getByRole('button', { name: '保存' }).click()
    const created = (await (await createdResp).json()) as { code: number; data?: { recordNo: string } }
    expect(created.code).toBe(0)
    const recordNo = created.data!.recordNo

    await page.getByRole('button', { name: '创建考核' }).click()
    await fillCreate()
    await execModal.getByRole('button', { name: '保存' }).click()
    await expect(page.getByTestId('perf-exec-error')).toContainText('该周期已有进行中的考核记录（BR-031）')
    await execModal.getByRole('button', { name: '取消' }).click()

    const execRow = page.locator('tbody tr').filter({ hasText: recordNo }).first()
    await execRow.getByText('算分').click()
    await expect(execRow.locator('.tag')).toContainText('已计算', { timeout: 15_000 })
    await execRow.getByText('调整').click()
    const adjustModal = page.locator('.modal.card').filter({ hasText: '人工调整' })
    const tableHead = adjustModal.locator('thead')
    await expect(tableHead).toContainText('指标')
    await expect(tableHead).toContainText('权重')
    await expect(tableHead).toContainText('原始值')
    await expect(tableHead).toContainText('自动得分')
    await expect(tableHead).toContainText('人工调整')
    await expect(tableHead).toContainText('最终得分')
    const lineInputs = adjustModal.getByTestId('perf-adjust-line')
    const lineCount = await lineInputs.count()
    expect(lineCount).toBeGreaterThan(0)
    for (let index = 0; index < lineCount; index += 1) {
      await lineInputs.nth(index).fill('80')
    }
    await adjustModal.getByRole('button', { name: '保存' }).click()
    await expect(page.getByTestId('perf-adjust-error')).toContainText('调整幅度不能超过 ±20%')
    await expect(page.getByTestId('perf-adjust-error')).toContainText('基础分')
    await adjustModal.getByRole('button', { name: '取消' }).click()

    await execRow.getByTestId('perf-exec-confirm').click()
    await expect(page.getByTestId('perf-confirm-score')).toContainText('综合得分')
    await expect(page.getByTestId('perf-confirm-grade')).toContainText('分档')
    await expect(page.getByTestId('perf-confirm-dialog')).not.toContainText('S≥')
    await page.getByTestId('perf-confirm-submit').click()
    await expect(execRow.locator('.tag')).toContainText('已确认', { timeout: 15_000 })

    await page.goto('/ims/perf/result')
    await expect(page.locator('h1')).toContainText('考核结果')
    await expect(page.getByTestId('perf-result-top3')).toContainText('红榜 TOP3')
    await expect(page.getByTestId('perf-result-tail')).toContainText('末位预警')
    await expect(page.getByTestId('perf-result-avg')).toContainText('部门均分')
    await expect(page.getByTestId('perf-result-dept')).toBeVisible()
    await expect(page.locator('thead').last()).toContainText('评级')
    await page.getByTestId('perf-result-no').fill(recordNo)
    await page.getByTestId('perf-result-query').click()
    const resultRow = page.getByTestId('perf-result-row').filter({ hasText: recordNo })
    await expect(resultRow).toBeVisible({ timeout: 15_000 })
    await expect(resultRow.getByTestId('perf-result-grade')).not.toHaveText(/^[SABCD]/)
    await resultRow.getByTestId('perf-result-view').click()
    await expect(page.getByTestId('perf-result-detail')).toBeVisible()
    const downloadPromise = page.waitForEvent('download')
    await page.getByTestId('perf-result-detail-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toContain(recordNo)
    await page.locator('.modal-mask').getByRole('button', { name: '关闭' }).click()
    await resultRow.getByTestId('perf-result-alert').click()
    await expect(page.getByTestId('perf-result-alert-dialog')).toBeVisible()

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
