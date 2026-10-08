import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import {
  attachClosurePageHooks,
  E2E_FIN_PHONE_CODE,
  loginAdmin,
  openDcSessionDetailViaUi,
  openDcTypedEntryTraceViaUi,
  registerLiveSessionConfirmedReportViaUi,
  resolveLiveFinRegisterIdsViaUi,
  submitAndConfirmFinCostViaUi,
} from './closure-helpers'

const SHOTS = '/opt/cursor/artifacts/e2e-88-screenshots'

/**
 * Checklist **E2E-S12-01 其余入口切片 / DC-001**（#88 · 纯 UI）
 * 实名人、责任人、资产、IP 组各自搜入口 → 关系图/明细表 → 场次明细抽屉。
 * 实名人结果里再点账号节点，按该账号重查（仍落到同一场次）。
 */
test.describe('dc remaining entry trace closure', () => {
  test.skip(!!process.env.SKIP_E2E, 'SKIP_E2E set — 跳过 Playwright')

  test('person responsible asset and ip group entries drill into session detail', async ({ page }) => {
    test.setTimeout(180_000)
    fs.mkdirSync(SHOTS, { recursive: true })
    const pageErrors = attachClosurePageHooks(page)
    await loginAdmin(page)

    const ids = await resolveLiveFinRegisterIdsViaUi(page)
    expect(ids.ipGroupId).toBeTruthy()
    expect(ids.ipGroupName).toBeTruthy()

    const registered = await registerLiveSessionConfirmedReportViaUi(page, ids, {
      gmv: 100_000,
      refundAmount: 2_000,
    })
    expect(registered.realnameName).toBeTruthy()
    expect(registered.responsibleUserName).toBeTruthy()
    expect(registered.responsibleUserId).toBeTruthy()
    await submitAndConfirmFinCostViaUi(page, registered.sessionCode)

    const person = await openDcTypedEntryTraceViaUi(
      page,
      'PERSON',
      registered.realnameName,
      registered.sessionCode,
      { entryId: String(ids.realnamePersonId) },
    )
    expect(
      person.data?.nodes?.some(
        (node) => node.nodeType === 'PERSON' && node.nodeLabel?.includes(registered.realnameName),
      ),
    ).toBe(true)
    expect(person.data?.nodes?.some((node) => node.nodeType === 'ASSET')).toBe(true)

    const accountNode = page.locator(
      `[data-testid="dc-trace-node-drill"][data-node-type="ACCOUNT"][data-node-id="${ids.accountId}"]`,
    )
    await expect(accountNode).toBeVisible()
    const drillResp = page.waitForResponse(
      (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
    )
    await accountNode.click()
    const drillBody = (await (await drillResp).json()) as {
      code: number
      data?: { detailList?: { list?: Array<{ sessionCode?: string }> } }
    }
    expect(drillBody.code).toBe(0)
    expect(drillBody.data?.detailList?.list?.some((row) => row.sessionCode === registered.sessionCode)).toBe(true)
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('账号')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/01-person-then-account-node.png`, fullPage: true })

    const { drawer } = await openDcSessionDetailViaUi(page, registered.sessionCode)
    await expect(drawer).toContainText('100,000.00')
    await expect(drawer).toContainText('81,400.00')
    await expect(drawer).toContainText(`责任人：${registered.responsibleUserName}`)
    await expect(drawer).toContainText(`实名人：${registered.realnameName}`)
    await expect(drawer).toContainText('投流成本')
    await page.screenshot({ path: `${SHOTS}/02-session-detail-drawer.png`, fullPage: true })
    await drawer.getByRole('button', { name: '关闭' }).click()
    await expect(drawer).toBeHidden()

    await openDcTypedEntryTraceViaUi(page, 'RESPONSIBLE', registered.responsibleUserName, registered.sessionCode, {
      entryId: String(registered.responsibleUserId),
    })
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('责任人')
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText(registered.responsibleUserName)
    await page.screenshot({ path: `${SHOTS}/03-responsible-entry.png`, fullPage: true })

    const asset = await openDcTypedEntryTraceViaUi(page, 'ASSET', E2E_FIN_PHONE_CODE, registered.sessionCode, {
      entryId: String(ids.deviceId),
    })
    expect(asset.data?.nodes?.some((node) => node.nodeType === 'ASSET' && node.nodeId === String(ids.deviceId))).toBe(
      true,
    )
    await expect(page.getByTestId('dc-trace-graph')).toContainText('ASSET')
    await expect(page.getByTestId('dc-trace-graph')).toContainText(E2E_FIN_PHONE_CODE)
    await page.screenshot({ path: `${SHOTS}/04-asset-entry.png`, fullPage: true })

    await openDcTypedEntryTraceViaUi(page, 'IP_GROUP', ids.ipGroupName || '', registered.sessionCode, {
      entryId: String(ids.ipGroupId),
    })
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText('IP组')
    await expect(page.getByTestId('dc-trace-current-entry')).toContainText(ids.ipGroupName || '')
    await expect(page.getByTestId('dc-trace-detail-table')).toContainText(registered.sessionCode)
    await page.screenshot({ path: `${SHOTS}/05-ip-group-entry.png`, fullPage: true })

    const again = await openDcSessionDetailViaUi(page, registered.sessionCode)
    await expect(again.drawer).toContainText(registered.sessionCode)
    await expect(again.drawer).toContainText(`责任人：${registered.responsibleUserName}`)
    await page.screenshot({ path: `${SHOTS}/06-ip-group-session-detail.png`, fullPage: true })

    expect(pageErrors, pageErrors.join('\n')).toEqual([])
  })
})
