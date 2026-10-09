import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test, expect, type Page } from '@playwright/test'
import { loginAdmin } from './closure-helpers'

test.use({ channel: 'chrome' })

const RECYCLE_NO = 'AC-E2E-RECYCLE'
const SHOTS = '/opt/cursor/artifacts/slice-138'

async function openDouyin(page: Page) {
  const accountReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  const poolReady = page.waitForResponse(
    (r) => r.url().includes('/corp/account/status/summary') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.goto('/ims/corp/account/douyin')
  await accountReady
  await poolReady
  await expect(page.locator('h1')).toContainText('抖音')
  await expect(page.getByTestId('acct-pool-status')).toContainText('池状态')
}

async function searchAccount(page: Page) {
  await page.locator('input[placeholder="账号编号/昵称"]').fill(RECYCLE_NO)
  const searchResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await searchResp
  const row = page.locator('.tbl-wrap tbody tr').filter({ hasText: RECYCLE_NO })
  await expect(row).toBeVisible()
  return row
}

test.describe('account pool recycle and cert original stub #138', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test.beforeAll(() => {
    fs.mkdirSync(SHOTS, { recursive: true })
  })

  test('returned account recycles to the pool and exports a handover voucher', async ({ page }) => {
    test.setTimeout(120_000)
    await loginAdmin(page)
    await openDouyin(page)
    const poolRow = await searchAccount(page)
    await expect(poolRow).toContainText('池可领用')
    await page.screenshot({ path: `${SHOTS}/01-pool-status.png`, fullPage: true })

    await poolRow.getByTestId('acct-checkout-open').click()
    await expect(page.locator('.drawer.on').getByText('发起账号领用')).toBeVisible()
    const applyResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply') && r.request().method() === 'POST' && r.status() === 200,
    )
    await page.getByRole('button', { name: '提交申请' }).click()
    expect(((await (await applyResp).json()) as { code: number }).code).toBe(0)

    const approveResp = page.waitForResponse(
      (r) => r.url().includes('/approve') && r.request().method() === 'PUT' && r.status() === 200,
    )
    await page.getByRole('button', { name: '审批通过' }).click()
    await approveResp

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/account/apply/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
    )
    await page.getByRole('button', { name: '确认领用生效' }).click()
    expect(((await (await confirmResp).json()) as { code: number }).code).toBe(0)

    const inUseRow = await searchAccount(page)
    await expect(inUseRow).toContainText('在用')
    await inUseRow.getByTestId('acct-return-open').click()
    const returnResp = page.waitForResponse(
      (r) => r.url().includes('/account/return/submit') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '确认归还' }).click()
    expect(((await (await returnResp).json()) as { code: number }).code).toBe(0)

    const returnedRow = await searchAccount(page)
    await expect(returnedRow).toContainText('已归还')
    await page.screenshot({ path: `${SHOTS}/02-returned.png`, fullPage: true })

    await returnedRow.getByTestId('acct-recycle-open').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '回收回账号池' })
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('acct-recycle-remark').fill('E2E 管理员回收回池')
    const recycleResp = page.waitForResponse(
      (r) => r.url().includes('/recycle') && r.request().method() === 'POST',
    )
    await drawer.getByTestId('acct-recycle-submit').click()
    const recycleBody = (await (await recycleResp).json()) as { code: number; data?: { status?: string } }
    expect(recycleBody.code).toBe(0)
    expect(recycleBody.data?.status).toBe('IN_POOL')
    await expect(drawer.getByTestId('acct-recycle-status')).toContainText('IN_POOL')
    await page.screenshot({ path: `${SHOTS}/03-recycled.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()

    const pooled = await searchAccount(page)
    await expect(pooled).toContainText('池可领用')
    await expect(page.getByTestId('acct-pool-events')).toContainText('回收回池')

    await pooled.getByRole('button', { name: '详情' }).click()
    const detail = page.locator('.drawer.on').filter({ hasText: '领用时间线' })
    await detail.getByRole('button', { name: '领用时间线' }).click()
    const exportResp = page.waitForResponse(
      (r) => r.url().includes('/timeline/') && r.url().includes('/export') && !r.url().includes('/export/file'),
    )
    await detail.getByTestId('acct-timeline-export').click()
    const exportBody = (await (await exportResp).json()) as { code: number; data?: { message?: string } }
    expect(exportBody.code).toBe(0)
    expect(exportBody.data?.message).toBe('交接凭证已生成')
    await expect(detail.getByTestId('acct-timeline-export-note')).toContainText('交接凭证已生成')
    await page.screenshot({ path: `${SHOTS}/04-handover-export.png`, fullPage: true })
  })

  test('certificate original upload stub confirms OCR and archives version 1', async ({ page }) => {
    test.setTimeout(90_000)
    await loginAdmin(page)
    await page.goto('/ims/corp/resource/certificate')
    await expect(page.locator('h1')).toContainText('证件')
    await page.getByTestId('corp-cert-create-btn').click()
    const drawer = page.locator('.drawer.on').filter({ hasText: '录入证件' })
    await expect(drawer).toBeVisible()

    const holder = `E2E原件${Date.now().toString().slice(-6)}`
    const stub = path.join(os.tmpdir(), `cert-original-${holder}.txt`)
    fs.writeFileSync(
      stub,
      [`holderName=${holder}`, 'certNo=110101199001011388', 'issueDate=2021-06-01', 'expireDate=2031-06-01'].join('\n'),
    )
    const uploadResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/original') && !r.url().includes('/confirm') && r.request().method() === 'POST',
    )
    await drawer.getByTestId('corp-cert-original-file').setInputFiles(stub)
    const uploadBody = (await (await uploadResp).json()) as {
      code: number
      data?: { ocrResult?: { recognizeStatus?: string } }
    }
    expect(uploadBody.code).toBe(0)
    expect(uploadBody.data?.ocrResult?.recognizeStatus).toBe('PENDING_CONFIRM')
    await expect(drawer.getByTestId('corp-cert-ocr')).toContainText('OCR 待确认')
    await expect(drawer.getByTestId('corp-cert-holder')).toHaveValue(holder)
    await page.screenshot({ path: `${SHOTS}/05-ocr-pending.png`, fullPage: true })

    const confirmResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/original/confirm') && r.request().method() === 'POST',
    )
    await drawer.getByTestId('corp-cert-ocr-confirm').click()
    expect(((await (await confirmResp).json()) as { code: number }).code).toBe(0)
    await expect(drawer.getByTestId('corp-cert-ocr')).toContainText('已确认')

    const saveResp = page.waitForResponse(
      (r) => r.url().includes('/cert/archive/upload') && r.request().method() === 'POST',
    )
    await drawer.getByTestId('corp-cert-save').click()
    expect(((await (await saveResp).json()) as { code: number }).code).toBe(0)
    await expect(page.getByTestId('corp-cert-original-note')).toContainText('原件 v1 已归档')
    await page.screenshot({ path: `${SHOTS}/06-original-archived.png`, fullPage: true })
  })
})
