import fs from 'fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

/**
 * #224 AIR/S8 本地尾巴（acceptance · 纯 UI）。
 * 白名单筛选空态、吊销原因、审计超 180 天、用量倒置日期与按人空态。
 * 不重做 #160 的停用/解冻，也不重做 #182 的用量汇总与详情抽屉。
 */
const shotDir = '/opt/cursor/artifacts/air-s8-224'

function ymd(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

test.describe('air s8 filter tails closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('whitelist filter, revoke reason, audit span, and usage date edges', async ({ page }) => {
    test.setTimeout(120_000)
    const pageErrors = attachClosurePageHooks(page)
    fs.mkdirSync(shotDir, { recursive: true })
    await loginAdmin(page)

    const listed = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.goto('/ims/air/cfg?tab=key')
    expect((await (await listed).json()).code).toBe(0)
    await expect(page.getByTestId('air-key-whitelist-hint')).toContainText('仅预存')

    for (let i = 0; i < 6; i++) {
      const revoke = page.locator('tbody tr', { hasText: 'e2e_author' }).getByTestId('air-key-revoke').first()
      if ((await revoke.count()) === 0) break
      const done = page.waitForResponse(
        (response) => response.url().includes('/revoke') && response.request().method() === 'POST',
      )
      const refreshed = page.waitForResponse(
        (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
      )
      await revoke.click()
      await expect(page.getByTestId('air-key-revoke-hint')).toContainText('401')
      await page.getByTestId('air-key-revoke-ok').click()
      expect((await (await done).json()).code).toBe(0)
      await refreshed
    }

    await page.getByTestId('air-key-generate').click()
    const form = page.getByTestId('air-key-form')
    await form.getByTestId('air-key-user-search').fill('e2e_author')
    const users = page.waitForResponse((response) => response.url().includes('/system/user/page'))
    await form.getByRole('button', { name: '查找' }).click()
    await users
    await expect(form.getByTestId('air-key-user')).not.toHaveValue('')
    await form.getByTestId('air-key-save').click()
    const plain = page.getByTestId('air-key-plain')
    await expect(plain).toBeVisible({ timeout: 15_000 })
    const keyCode = ((await page.getByTestId('air-key-code').innerText()) || '').trim()
    await page.getByTestId('air-key-plain-close').click()

    const opened = page.waitForResponse(
      (response) => response.url().includes('whitelistOn=true') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-whitelist').selectOption('true')
    await page.getByTestId('air-key-search').click()
    expect((await (await opened).json()).code).toBe(0)
    const seedRow = page.locator('tbody tr').filter({ hasText: 'KEY-0001' })
    await expect(seedRow).toBeVisible()
    await expect(seedRow.getByTestId('air-key-whitelist-cell')).toHaveText('已开启')
    await expect(page.locator('tbody tr').filter({ hasText: keyCode })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/01-whitelist-on.png`, fullPage: true })

    const closed = page.waitForResponse(
      (response) => response.url().includes('whitelistOn=false') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-whitelist').selectOption('false')
    await page.getByTestId('air-key-user-filter').fill('e2e_author')
    await page.getByTestId('air-key-search').click()
    expect((await (await closed).json()).code).toBe(0)
    const created = page.locator('tbody tr').filter({ hasText: keyCode })
    await expect(created).toBeVisible()
    await expect(created.getByTestId('air-key-whitelist-cell')).toHaveText('未开启')
    await expect(page.locator('tbody tr').filter({ hasText: 'KEY-0001' })).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/02-whitelist-off.png`, fullPage: true })

    await created.getByTestId('air-key-revoke').click()
    await expect(page.getByTestId('air-key-revoke-hint')).toContainText('离职联动')
    await page.screenshot({ path: `${shotDir}/03-revoke-confirm.png`, fullPage: true })
    const revoked = page.waitForResponse(
      (response) => response.url().includes('/revoke') && response.request().method() === 'POST',
    )
    const revokedList = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-revoke-ok').click()
    expect((await (await revoked).json()).code).toBe(0)
    await revokedList
    await expect(created.getByTestId('air-key-status-cell')).toContainText('已吊销·管理员手工')
    await expect(created.getByTestId('air-key-revoke')).toHaveCount(0)
    await page.screenshot({ path: `${shotDir}/04-revoke-reason.png`, fullPage: true })

    const emptyKeys = page.waitForResponse(
      (response) => response.url().includes('/air/cfg/key/page') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-key-user-filter').fill(`no-such-air-224-${Date.now()}`)
    await page.getByTestId('air-key-whitelist').selectOption('true')
    await page.getByTestId('air-key-search').click()
    expect((await (await emptyKeys).json()).data.total).toBe(0)
    await expect(page.getByTestId('air-key-empty')).toContainText('暂无 Key')
    await expect(page.getByTestId('air-key-filter-empty')).toContainText('当前筛选下没有 Key')
    await page.screenshot({ path: `${shotDir}/05-key-filter-empty.png`, fullPage: true })

    await page.goto('/ims/air/cfg?tab=audit')
    await expect(page.getByTestId('air-mcp-audit')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('air-mcp-from').fill('2020-01-01')
    await page.getByTestId('air-mcp-to').fill(ymd(0))
    await page.getByTestId('air-mcp-search').click()
    await expect(page.getByTestId('air-mcp-filter-error')).toContainText('查询区间不能超过 180 天')
    await page.screenshot({ path: `${shotDir}/06-audit-span.png`, fullPage: true })

    const emptyAudit = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-reset').click()
    await emptyAudit
    await page.getByTestId('air-mcp-keyword').fill(`zzz-no-tool-224-${Date.now()}`)
    const missed = page.waitForResponse(
      (response) => response.url().includes('/air/mcp/audit-log') && response.request().method() === 'GET',
    )
    await page.getByTestId('air-mcp-search').click()
    expect((await (await missed).json()).data.total).toBe(0)
    await expect(page.getByTestId('air-mcp-empty')).toContainText('暂无调用日志')
    await expect(page.getByTestId('air-mcp-filter-empty')).toContainText('当前筛选下没有调用日志')
    await page.screenshot({ path: `${shotDir}/07-audit-filter-empty.png`, fullPage: true })

    await page.getByTestId('air-usage-start').fill(ymd(8))
    await page.getByTestId('air-usage-end').fill(ymd(1))
    await page.getByTestId('air-usage-search').click()
    await expect(page.getByTestId('air-usage-error')).toContainText('结束日不能早于开始日')
    await page.screenshot({ path: `${shotDir}/08-usage-inverted.png`, fullPage: true })

    const restored = page.waitForResponse(
      (response) => response.url().includes('/air/usage/stat') && response.url().includes('by=DAY'),
    )
    await page.getByTestId('air-usage-reset').click()
    const restoredBody = await (await restored).json()
    expect(restoredBody.code).toBe(0)
    expect(restoredBody.data).toHaveLength(7)
    await expect(page.getByTestId('air-usage-day')).toHaveCount(7)

    await page.getByTestId('air-usage-start').fill(ymd(3))
    await page.getByTestId('air-usage-end').fill(ymd(9))
    const people = page.waitForResponse(
      (response) => response.url().includes('/air/usage/stat') && response.url().includes('by=PERSON'),
    )
    await page.getByTestId('air-usage-by-person').click()
    const peopleBody = await (await people).json()
    expect(peopleBody.code).toBe(0)
    expect(peopleBody.data).toEqual([])
    await expect(page.getByTestId('air-usage-person-empty')).toContainText('该区间没有调用人')
    await expect(page.getByTestId('air-usage-empty')).toContainText('该区间暂无调用')
    await page.screenshot({ path: `${shotDir}/09-usage-person-empty.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})