import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { attachClosurePageHooks, createSopViaUi, loginAdmin } from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-136-screenshots'

/**
 * 选题库剩余缺口（#136 · acceptance · 纯 UI）
 * 筛选（来源 / 编号 / 提报人 / 重置）、详情抽屉、待评审编辑、
 * 落选复活（意见保留）后立项可见草稿链、待评审取消。
 */
test.describe('content topic library closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('filters, detail, edit, revive and cancel stay on the topic page', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)

    const label = `e2e-lib-${Date.now()}`
    const sopName = `E2E 选题库 SOP ${label}`
    const hotspotTitle = `E2E 热点 ${label}`
    const talentTitle = `E2E 达人 ${label}`
    const editedTitle = `${hotspotTitle} 改`
    const requirement = `内容要求：筛选详情 ${label}`

    await loginAdmin(page)
    await createSopViaUi(page, { sopName, nodeName: '脚本' })

    await page.goto('/ims/content/topic')
    await expect(page.locator('h1')).toHaveText('选题计划', { timeout: 15_000 })

    async function submitTopic(title: string, sourceLabel: string) {
      await page.getByTestId('topic-create-open').click()
      const drawer = page.locator('.drawer.on').filter({ hasText: '提报选题' })
      await expect(drawer).toBeVisible()
      await drawer.getByTestId('topic-title').fill(title)
      await drawer.getByTestId('topic-description').fill(requirement)
      await drawer.getByTestId('topic-source').selectOption({ label: sourceLabel })
      const resp = page.waitForResponse(
        (r) => r.url().includes('/content/topic') && !r.url().includes('/list') && r.request().method() === 'POST' && r.status() === 200,
      )
      await drawer.getByTestId('topic-submit').click()
      const body = (await (await resp).json()) as { code: number }
      expect(body.code).toBe(0)
      await expect(drawer).not.toBeVisible({ timeout: 10_000 })
      const row = page.locator('tr', { hasText: title })
      await expect(row).toBeVisible({ timeout: 15_000 })
      return row
    }

    const hotspotRow = await submitTopic(hotspotTitle, '热点')
    const topicNo = ((await hotspotRow.locator('.mono').first().textContent()) || '').trim()
    expect(topicNo.startsWith('TP')).toBe(true)
    await submitTopic(talentTitle, '达人')

    await page.getByTestId('topic-filter-source').selectOption('TALENT')
    const sourceResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/list') && r.request().method() === 'GET' && r.status() === 200,
    )
    await page.getByTestId('topic-filter-search').click()
    await sourceResp
    await expect(page.locator('tr', { hasText: talentTitle })).toBeVisible()
    await expect(page.locator('tr', { hasText: hotspotTitle })).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/01-filter-source.png`, fullPage: true })

    await page.getByTestId('topic-filter-reset').click()
    await expect(page.locator('tr', { hasText: hotspotTitle })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('tr', { hasText: talentTitle })).toBeVisible()

    await page.getByTestId('topic-filter-no').fill(topicNo)
    await page.getByTestId('topic-filter-search').click()
    await expect(page.locator('tr', { hasText: hotspotTitle })).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('tr', { hasText: talentTitle })).toHaveCount(0)

    await page.getByTestId('topic-filter-reset').click()
    await expect(page.locator('tr', { hasText: talentTitle })).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('topic-filter-submitter').selectOption({ label: 'E2E内容作者（e2e_author）' })
    const ownerResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/list') && r.url().includes('submitterUserId') && r.status() === 200,
    )
    await page.getByTestId('topic-filter-search').click()
    await ownerResp
    await expect(page.locator('tr', { hasText: hotspotTitle })).toHaveCount(0)
    await expect(page.getByText('暂无选题')).toBeVisible()
    await page.getByTestId('topic-filter-reset').click()
    const pendingRow = page.locator('tr', { hasText: hotspotTitle })
    await expect(pendingRow).toBeVisible({ timeout: 15_000 })

    await pendingRow.getByTestId('topic-detail').click()
    const detail = page.locator('.drawer.on').filter({ hasText: '选题详情' })
    await expect(detail.getByTestId('topic-detail-title')).toHaveText(hotspotTitle)
    await expect(detail.getByTestId('topic-detail-requirement')).toContainText(requirement)
    await expect(detail.getByTestId('topic-detail-status')).toHaveText('待评审')
    await expect(detail.getByTestId('topic-detail-project')).toContainText('尚未立项，无内容项目')
    await page.screenshot({ path: `${SHOTS}/02-detail-pending.png`, fullPage: true })
    await detail.locator('.dr-x').click()
    await expect(detail).not.toBeVisible()

    await pendingRow.getByTestId('topic-edit').click()
    const editDrawer = page.locator('.drawer.on').filter({ hasText: '编辑选题' })
    await expect(editDrawer).toBeVisible()
    await editDrawer.getByTestId('topic-title').fill(editedTitle)
    await editDrawer.getByTestId('topic-edit-plan-date').fill('2026-12-18')
    const editResp = page.waitForResponse(
      (r) => r.url().includes('/content/topic/') && r.request().method() === 'PUT' && !r.url().includes('/review') && r.status() === 200,
    )
    await editDrawer.getByTestId('topic-submit').click()
    const editBody = (await (await editResp).json()) as { code: number }
    expect(editBody.code).toBe(0)
    const editedRow = page.locator('tr', { hasText: editedTitle })
    await expect(editedRow).toBeVisible({ timeout: 15_000 })
    await expect(editedRow).toContainText('2026-12-18')
    await expect(editedRow).toContainText('待评审')
    await page.screenshot({ path: `${SHOTS}/03-edited.png`, fullPage: true })

    const talentRow = page.locator('tr', { hasText: talentTitle })
    await talentRow.getByRole('button', { name: '评审' }).click()
    const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await reviewDrawer.getByTestId('topic-opinion').fill('与选题库要求不符')
    await reviewDrawer.getByRole('button', { name: '落选' }).click()
    await expect(talentRow).toContainText('落选', { timeout: 15_000 })
    await expect(talentRow.getByTestId('topic-opinion-cell')).toContainText('与选题库要求不符')
    await talentRow.getByTestId('topic-detail').click()
    const rejectedDetail = page.locator('.drawer.on').filter({ hasText: '选题详情' })
    await expect(rejectedDetail.getByTestId('topic-detail-opinion')).toHaveText('与选题库要求不符')
    await rejectedDetail.locator('.dr-x').click()

    await talentRow.getByTestId('topic-revive').click()
    const reviveModal = page.getByTestId('topic-revive-modal')
    await expect(reviveModal).toContainText('复活回待评审')
    await page.screenshot({ path: `${SHOTS}/04-revive-confirm.png`, fullPage: true })
    const reviveResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await reviveModal.getByTestId('topic-revive-confirm').click()
    const reviveBody = (await (await reviveResp).json()) as { code: number }
    expect(reviveBody.code).toBe(0)
    await expect(talentRow).toContainText('待评审', { timeout: 15_000 })
    await talentRow.getByTestId('topic-detail').click()
    const revivedDetail = page.locator('.drawer.on').filter({ hasText: '选题详情' })
    await expect(revivedDetail.getByTestId('topic-detail-opinion')).toHaveText('与选题库要求不符')
    await revivedDetail.locator('.dr-x').click()

    await talentRow.getByRole('button', { name: '评审' }).click()
    const approveDrawer = page.locator('.drawer.on').filter({ hasText: '评审立项' })
    await approveDrawer.getByTestId('topic-sop').selectOption({ label: sopName })
    await approveDrawer.getByTestId('topic-plan-date').fill('2026-12-02')
    await approveDrawer.getByTestId('topic-approve').click()
    await expect(talentRow).toContainText('已立项', { timeout: 15_000 })
    await expect(talentRow).toContainText('可出任务')
    await expect(talentRow.getByTestId('topic-edit')).toHaveCount(0)
    await expect(talentRow.getByTestId('topic-revive')).toHaveCount(0)
    await expect(talentRow.getByTestId('topic-cancel')).toHaveCount(0)
    await talentRow.getByTestId('topic-detail').click()
    const approvedDetail = page.locator('.drawer.on').filter({ hasText: '选题详情' })
    await expect(approvedDetail.getByTestId('topic-detail-project')).toContainText('草稿')
    await expect(approvedDetail.getByTestId('topic-detail-chain').locator('span.on')).toHaveText('草稿')
    await page.screenshot({ path: `${SHOTS}/05-detail-approved.png`, fullPage: true })
    await approvedDetail.locator('.dr-x').click()

    await editedRow.getByTestId('topic-cancel').click()
    const cancelModal = page.getByTestId('topic-cancel-modal')
    await cancelModal.getByTestId('topic-cancel-opinion').fill('本期选题不做')
    await page.screenshot({ path: `${SHOTS}/06-cancel-confirm.png`, fullPage: true })
    const cancelResp = page.waitForResponse(
      (r) => r.url().includes('/review') && r.request().method() === 'PUT',
    )
    await cancelModal.getByTestId('topic-cancel-confirm').click()
    const cancelBody = (await (await cancelResp).json()) as { code: number }
    expect(cancelBody.code).toBe(0)
    await expect(editedRow).toContainText('已取消', { timeout: 15_000 })
    await expect(editedRow).toContainText('已取消不可出任务')
    await expect(editedRow).toContainText('本期选题不做')
    await expect(editedRow.getByTestId('topic-edit')).toHaveCount(0)
    await page.screenshot({ path: `${SHOTS}/07-cancelled.png`, fullPage: true })

    expect(pageErrors).toEqual([])
  })
})
