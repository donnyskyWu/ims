import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, loginAdmin } from './closure-helpers'

test.describe('HOME IP output empty and workbench mine cards (#189)', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('empty IP group chart and stub mine cards drill to existing pages', async ({ page }) => {
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    await page.goto('/ims/home')
    await expect(page.locator('h1')).toContainText('运营仪表盘')
    const ipCard = page.getByTestId('home-ip-output')
    await expect(ipCard).toContainText('IP 组产出')
    await expect(ipCard).toContainText('不请求 Football')
    await expect(page.getByTestId('home-ip-output-empty')).toContainText('暂无 IP 组产出')
    await page.screenshot({ path: '/opt/cursor/artifacts/home-ip-output-empty.png', fullPage: true })

    await page.goto('/ims/workbench')
    await expect(page.locator('h1')).toContainText(/好，/)
    const cards = page.getByTestId('wb-mine-cards')
    await expect(cards.getByTestId('wb-card-account')).toContainText('暂无')
    await expect(cards.getByTestId('wb-card-asset')).toContainText('暂无')
    await expect(cards.getByTestId('wb-card-cert')).toContainText('暂无预警')
    await expect(cards.getByTestId('wb-card-session')).toContainText('暂无')
    await expect(cards.locator('.wb-card-empty')).toHaveCount(4)
    await expect(cards.getByTestId('wb-cert-warn')).toHaveCount(0)

    const todoRow = page.locator('.tbl-wrap table').nth(1).locator('tbody tr').filter({ hasText: 'E2E-WB-CLOSE' })
    await expect(todoRow).toContainText('否')
    await page.screenshot({ path: '/opt/cursor/artifacts/workbench-mine-cards.png', fullPage: true })

    await cards.getByTestId('wb-card-account').click()
    await page.waitForURL(/\/ims\/corp\/account\/douyin/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('抖音')
    await page.screenshot({ path: '/opt/cursor/artifacts/workbench-account-drill.png', fullPage: true })

    await page.goto('/ims/workbench')
    await page.getByTestId('wb-card-cert').click()
    await page.waitForURL(/\/ims\/corp\/resource\/certificate/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('证件管理')

    await page.goto('/ims/workbench')
    await page.getByTestId('wb-card-asset').click()
    await page.waitForURL(/\/ims\/corp\/device\/office/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('办公设备管理')

    await page.goto('/ims/workbench')
    await page.getByTestId('wb-card-session').click()
    await page.waitForURL(/\/ims\/live\/sessions/, { timeout: 30_000 })
    await expect(page.locator('h1')).toContainText('直播管理')

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
