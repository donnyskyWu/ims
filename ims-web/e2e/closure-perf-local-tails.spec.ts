import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin, loginAs } from './closure-helpers'

/**
 * #208 绩效本地尾巴（纯 UI）
 * 计算列表按状态筛出空态；指标、方案、题库、试卷、成绩在筛选无匹配时给出空态；
 * 成绩表露出开始/交卷时间；无记录月份说明入离职折算。
 * 不重建 #187 排名红榜。
 */
const shotDir = '/opt/cursor/artifacts/e2e-208-screenshots'
const EMPTY_PERIOD = '2099-12'

test.describe('perf local tails #208', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('calc status empty, list filter empties, score times, mine tenure copy', async ({ page }) => {
    test.setTimeout(120_000)
    fs.mkdirSync(shotDir, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    await loginAdmin(page)
    await page.goto('/ims/perf/calc')
    await expect(page.locator('h1')).toHaveText('绩效计算与核准', { timeout: 15_000 })
    await page.getByTestId('perf-period').fill(EMPTY_PERIOD)
    await page.getByTestId('perf-period').press('Tab')
    await expect(page.getByTestId('perf-calc-empty')).toContainText('本周期还没有计算结果', { timeout: 15_000 })
    await page.getByTestId('perf-calc-status').selectOption('PUBLISHED')
    await expect(page.getByTestId('perf-calc-empty')).toContainText('当前状态没有计算结果')
    await page.screenshot({ path: `${shotDir}/01-calc-status-empty.png`, fullPage: true })
    await page.getByTestId('perf-calc-reset').click()
    await expect(page.getByTestId('perf-calc-empty')).toContainText('本周期还没有计算结果')

    await page.goto('/ims/perf/metric')
    await expect(page.locator('h1')).toHaveText('指标配置', { timeout: 15_000 })
    await page.getByTestId('perf-metric-name').fill('没有这个指标208')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('perf-metric-empty')).toContainText('当前筛选下暂无指标', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/02-metric-filter-empty.png`, fullPage: true })

    await page.goto('/ims/perf/scheme')
    await expect(page.locator('h1')).toHaveText('考核方案', { timeout: 15_000 })
    await page.getByTestId('perf-scheme-name').fill('没有这个方案208')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('perf-scheme-empty')).toContainText('当前筛选下暂无考核方案', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/03-scheme-filter-empty.png`, fullPage: true })

    await page.goto('/ims/perf/exam')
    await expect(page.locator('h1')).toHaveText('在线考试', { timeout: 15_000 })
    await page.getByTestId('exam-bank-no').fill('NO-SUCH-208')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-bank-empty')).toContainText('当前筛选下暂无题目', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/04-bank-filter-empty.png`, fullPage: true })

    await page.getByRole('button', { name: '试卷管理' }).click()
    await page.getByTestId('exam-paper-name').fill('没有这份试卷208')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-paper-empty')).toContainText('当前筛选下暂无试卷', { timeout: 15_000 })

    await page.getByRole('button', { name: '成绩管理' }).click()
    await expect(page.getByRole('columnheader', { name: '开始' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: '交卷' })).toBeVisible()
    await page.getByTestId('exam-score-user').fill('没有这个人208')
    await page.getByRole('button', { name: '查询' }).click()
    await expect(page.getByTestId('exam-score-empty')).toContainText('当前筛选下暂无成绩', { timeout: 15_000 })
    await page.screenshot({ path: `${shotDir}/05-score-filter-empty.png`, fullPage: true })

    await loginAs(page, 'e2e_perf_staff')
    await page.goto('/ims/perf/mine')
    await expect(page.locator('h1')).toHaveText('我的绩效', { timeout: 15_000 })
    await page.getByTestId('perf-mine-period').fill(EMPTY_PERIOD)
    await page.getByTestId('perf-mine-period').press('Tab')
    await expect(page.getByTestId('perf-mine-empty')).toContainText('入职/离职当月按在职天数折算', { timeout: 15_000 })
    await expect(page.getByTestId('perf-mine-empty')).toContainText('PER-C-R2')
    await page.screenshot({ path: `${shotDir}/06-mine-tenure-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
