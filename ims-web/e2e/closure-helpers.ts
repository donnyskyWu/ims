import { expect, type Page } from '@playwright/test'

export const ADMIN_USER = 'admin'
export const ADMIN_PASS = 'Admin@123'
/** BR-212 closure · DEPT(11) · 与 `bi_br212_seed.ensure_bi_r4_viewer` 一致 */
export const BI_R4_VIEWER = 'bi_r4_viewer'
export const BR212_PREFIX = 'BR212-'
/** 与 ims-backend `main.E2E_OPS_AUTHOR_ID` 种子一致 · 工作任务登记纯 UI 绑定 */
export const E2E_OPS_AUTHOR_ID = 900_001
export const E2E_OPS_AUTHOR_NAME = 'E2EClosureAuthor'

/** 登录后进 IMS（纯 UI · 非 API 造数） */
export async function loginAs(page: Page, username: string, password = ADMIN_PASS) {
  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill(username)
  await page.locator('input[type="password"]').fill(password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL(/\/ims\//, { timeout: 30_000 })
}

export async function loginAdmin(page: Page) {
  await loginAs(page, ADMIN_USER, ADMIN_PASS)
}

/** closure 通用：吞 confirm/alert · 收集 pageerror */
function idFromOkPayload(data: unknown): number | undefined {
  if (typeof data === 'number') return data
  if (data && typeof data === 'object' && 'id' in data) {
    const id = (data as { id: unknown }).id
    return typeof id === 'number' ? id : undefined
  }
  return undefined
}

export function attachClosurePageHooks(page: Page): string[] {
  const pageErrors: string[] = []
  page.on('pageerror', (err) => pageErrors.push(err.message))
  page.on('dialog', (d) => d.accept())
  return pageErrors
}

/** 内容审核队列 · 指定 Tab 打开抽屉并通过（ADR-017 二级审核链） */
export async function passContentReviewViaUi(
  page: Page,
  opts: { title: string; stageTab?: '一级审核' | '二级审核' },
) {
  await page.goto('/ims/content/review')
  if (opts.stageTab) {
    await page.locator('.tab', { hasText: opts.stageTab }).click()
  }
  await page.locator('input[placeholder="标题"]').fill(opts.title)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/content/review') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const reviewRow = page.locator('tr', { hasText: opts.title }).first()
  await expect(reviewRow).toBeVisible({ timeout: 15_000 })
  await reviewRow.getByRole('button', { name: '审核' }).click()
  const reviewDrawer = page.locator('.drawer.on').filter({ hasText: '审核' })
  const boxes = reviewDrawer.locator('input[type="checkbox"]')
  const n = await boxes.count()
  for (let i = 0; i < n; i++) {
    await boxes.nth(i).check()
  }
  const concludeResp = page.waitForResponse(
    (r) =>
      r.url().includes('/content/review/') &&
      r.url().includes('/conclusion') &&
      r.request().method() === 'PUT' &&
      r.status() === 200,
  )
  await reviewDrawer.getByRole('button', { name: '通过' }).click()
  const concludeBody = (await (await concludeResp).json()) as { code: number }
  expect(concludeBody.code).toBe(0)
  await expect(reviewDrawer).not.toBeVisible({ timeout: 10_000 })
}

/** SOP 管理 · 新增模板（经 UI 保存 · id 取自保存请求的响应） */
export async function createSopViaUi(
  page: Page,
  opts: { sopName: string; nodeName?: string },
): Promise<{ sopId: number }> {
  await page.goto('/ims/content/sop')
  await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })

  await page.getByRole('button', { name: '新增模板' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新增 SOP 模板' })
  await expect(drawer).toBeVisible()

  const nameInput = drawer.locator('.fld').filter({ hasText: '模板名称' }).locator('input')
  await nameInput.fill(opts.sopName)
  if (opts.nodeName) {
    await drawer.getByPlaceholder('脚本').fill(opts.nodeName)
  }

  const createResp = page.waitForResponse(
    (r) => r.url().includes('/content/sop') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存' }).click()
  const body = (await (await createResp).json()) as { code: number; data?: unknown }
  expect(body.code).toBe(0)
  const sopId = idFromOkPayload(body.data)
  expect(sopId).toBeTruthy()

  await expect(page.locator('tr', { hasText: opts.sopName })).toBeVisible({ timeout: 15_000 })
  return { sopId: sopId! }
}

async function ipGroupIdFromMembersRequest(page: Page, clickSelect: () => Promise<void>): Promise<number> {
  const membersResp = page.waitForResponse((r) => /\/ip-group\/\d+\/members/.test(r.url()) && r.status() === 200)
  await clickSelect()
  const url = (await membersResp).url()
  const m = url.match(/ip-group\/(\d+)\/members/)
  expect(m).toBeTruthy()
  return parseInt(m![1], 10)
}

async function waitIpGroupMembersLoaded(page: Page) {
  await page.waitForResponse(
    (r) => /\/ip-group\/\d+\/members/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
    { timeout: 15_000 },
  )
}

async function ensureAdminMemberOnSelectedGroup(page: Page) {
  await page.locator('.tab', { hasText: '成员管理' }).click()
  await waitIpGroupMembersLoaded(page).catch(() => {})
  const memberRows = page.locator('.ipg-detail-body .tbl-wrap tbody tr').filter({ hasNotText: '暂无成员' })
  if ((await memberRows.count()) > 0) return
  const addBtn = page.getByRole('button', { name: '+ 添加成员（管理员 id=1）' })
  if (!(await addBtn.isVisible())) return
  const addResp = page.waitForResponse(
    (r) => r.url().includes('/ip-group/') && r.url().includes('/members') && r.request().method() === 'POST',
  )
  await addBtn.click()
  const addBody = (await (await addResp).json()) as { code: number; msg?: string }
  if (addBody.code !== 0 && !String(addBody.msg || '').includes('成员已存在')) {
    expect(addBody.code).toBe(0)
  }
  const selectedNode = page.locator('.ipg-node.on')
  const peerNode = page.locator('.ipg-node.child').filter({ hasNot: page.locator('.on') }).first()
  if (await peerNode.count()) {
    await peerNode.click()
    await waitIpGroupMembersLoaded(page).catch(() => {})
  }
  const membersReload = waitIpGroupMembersLoaded(page)
  await selectedNode.click()
  await membersReload.catch(() => {})
  await page.locator('.tab', { hasText: '成员管理' }).click()
  if ((await memberRows.count()) > 0) return
  const cnt = (await selectedNode.locator('.cnt').textContent()) || ''
  const memberCount = parseInt(cnt.replace(/^\(/, '').split('/')[0] || '0', 10)
  expect(memberCount, `IP 组成员未就绪 · ${cnt}`).toBeGreaterThan(0)
}

/**
 * 准备带 admin 成员的小组 IP 组 id（新建大组+小组或复用已有小组）
 * 供计划启动后「我的任务」可见。
 */
export async function prepareIpGroupWithAdminMember(
  page: Page,
  label: string,
  forceNew = false,
  bindAuthorId?: number,
): Promise<{ ipGroupId: number; groupName?: string }> {
  const treeReady = page.waitForResponse((r) => r.url().includes('/ip-group/tree') && r.status() === 200)
  await page.goto('/ims/ip-group')
  await expect(page.locator('h1')).toHaveText('IP 组运营', { timeout: 15_000 })
  await treeReady
  const pickNode = page.locator('.ipg-node.child').first()
  if (!forceNew && (await pickNode.count())) {
    const ipGroupId = await ipGroupIdFromMembersRequest(page, () => pickNode.click())
    await ensureAdminMemberOnSelectedGroup(page)
    return { ipGroupId }
  }

  const bigName = `E2E大组-${label}`
  await page.getByRole('button', { name: '+ 新建大组' }).click()
  const bigDrawer = page.locator('.drawer.on').filter({ hasText: '新建大组' })
  await bigDrawer.locator('input').first().fill(bigName)
  const bigResp = page.waitForResponse(
    (r) => r.url().includes('/ip-group/create') && r.request().method() === 'POST' && r.status() === 200,
  )
  await bigDrawer.getByRole('button', { name: '确定' }).click()
  const bigBody = (await (await bigResp).json()) as { code: number; data?: unknown }
  expect(bigBody.code).toBe(0)
  const bigId = idFromOkPayload(bigBody.data)
  expect(bigId).toBeTruthy()

  await page.locator('.ipg-node', { hasText: bigName }).click()
  await page.getByRole('button', { name: '+ 新建小组' }).click()
  const smallDrawer = page.locator('.drawer.on').filter({ hasText: '新建小组' })
  const smallName = `E2E小组-${label}`
  await smallDrawer.locator('input').first().fill(smallName)
  const parentFld = smallDrawer.locator('.fld').filter({ hasText: '上级大组 id' })
  if (await parentFld.count()) {
    await parentFld.locator('input').fill(String(bigId))
  }
  const smallResp = page.waitForResponse(
    (r) => r.url().includes('/ip-group/create') && r.request().method() === 'POST' && r.status() === 200,
  )
  await smallDrawer.getByRole('button', { name: '确定' }).click()
  const smallBody = (await (await smallResp).json()) as { code: number; data?: unknown }
  expect(smallBody.code).toBe(0)
  const ipGroupId = idFromOkPayload(smallBody.data)
  expect(ipGroupId).toBeTruthy()

  const smallNode = page.locator('.ipg-node', { hasText: smallName })
  await ipGroupIdFromMembersRequest(page, () => smallNode.click())
  await ensureAdminMemberOnSelectedGroup(page)
  if (bindAuthorId) {
    await bindOpsAuthorToIpGroup(page, ipGroupId!, bindAuthorId, smallName)
  }
  return { ipGroupId: ipGroupId!, groupName: smallName }
}

/** 计划管理 · 保存草稿 */
export async function createDraftPlanViaUi(
  page: Page,
  opts: { planName: string; sopId: number; ipGroupId: number; startDate?: string; endDate?: string },
) {
  await page.goto('/ims/content/plan')
  await expect(page.locator('h1')).toHaveText('计划管理', { timeout: 15_000 })

  await page.getByRole('button', { name: '新增计划' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新增计划（草稿）' })
  await drawer.locator('.fld').filter({ hasText: '计划名称' }).locator('input').fill(opts.planName)
  await drawer.locator('input[type="number"]').first().fill(String(opts.sopId))
  await drawer.locator('input[placeholder="例如 1 或 1,2"]').fill(String(opts.ipGroupId))
  await drawer.locator('input[type="date"]').first().fill(opts.startDate ?? '2026-10-01')
  await drawer.locator('input[type="date"]').nth(1).fill(opts.endDate ?? '2026-10-31')

  const planResp = page.waitForResponse(
    (r) => r.url().includes('/content/plan') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存草稿' }).click()
  const planBody = (await (await planResp).json()) as { code: number }
  expect(planBody.code).toBe(0)

  await expect(page.locator('tr', { hasText: opts.planName })).toBeVisible({ timeout: 15_000 })
}

/** 计划列表行内「启动」 */
export async function startPlanRowViaUi(page: Page, planName: string) {
  const row = page.locator('tr', { hasText: planName })
  await expect(row).toContainText('DRAFT')
  const startResp = page.waitForResponse(
    (r) => r.url().includes('/content/plan/') && r.url().includes('/start') && r.request().method() === 'POST',
  )
  await row.getByRole('button', { name: '启动' }).click()
  const startBody = (await (await startResp).json()) as { code: number; data?: { status?: string } }
  expect(startBody.code).toBe(0)
  await expect(row).toContainText('IN_PROGRESS', { timeout: 15_000 })
}

/** 计划 · 申请终止 → TERMINATE_PENDING */
export async function requestPlanTerminateViaUi(page: Page, planName: string, _reason?: string) {
  const row = page.locator('tr', { hasText: planName })
  await expect(row).toContainText('IN_PROGRESS')
  const termResp = page.waitForResponse(
    (r) =>
      r.url().includes('/content/plan/') &&
      r.url().includes('/terminate') &&
      !r.url().includes('/approve') &&
      !r.url().includes('/reject') &&
      r.request().method() === 'POST',
  )
  await row.getByRole('button', { name: '申请终止' }).click()
  const termBody = (await (await termResp).json()) as { code: number; data?: { status?: string } }
  expect(termBody.code).toBe(0)
  await expect(row).toContainText('TERMINATE_PENDING', { timeout: 15_000 })
}

/** 计划 · 批准终止 → TERMINATED */
export async function approvePlanTerminateViaUi(page: Page, planName: string) {
  const row = page.locator('tr', { hasText: planName })
  await expect(row).toContainText('TERMINATE_PENDING')
  const apprResp = page.waitForResponse(
    (r) => r.url().includes('/terminate/approve') && r.request().method() === 'POST',
  )
  await row.getByRole('button', { name: '批准终止' }).click()
  const apprBody = (await (await apprResp).json()) as { code: number; data?: { status?: string } }
  expect(apprBody.code).toBe(0)
  await expect(row).toContainText('TERMINATED', { timeout: 15_000 })
}

/** SOP · 工作任务链（营销计划 + CONTENT_GENERATION 节点） */
export async function createWorkTaskSopViaUi(
  page: Page,
  opts: { sopName: string; nodeName: string; marketingPlan?: string },
): Promise<{ sopId: number }> {
  await page.goto('/ims/content/sop')
  await expect(page.locator('h1')).toHaveText('SOP 管理', { timeout: 15_000 })

  await page.getByRole('button', { name: '新增模板' }).click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '新增 SOP 模板' })
  await expect(drawer).toBeVisible()

  await drawer.locator('.fld').filter({ hasText: '模板名称' }).locator('input').fill(opts.sopName)
  await drawer.locator('.fld').filter({ hasText: '营销计划' }).locator('select').selectOption(opts.marketingPlan ?? 'LIVE_PUBLIC')
  await drawer.locator('.fld').filter({ hasText: '首节点名称' }).locator('input').fill(opts.nodeName)
  await drawer.locator('.fld').filter({ hasText: '首节点类型' }).locator('select').selectOption('CONTENT_GENERATION')
  await drawer.locator('.fld').filter({ hasText: '文档类型' }).locator('select').selectOption('COPY')

  const createResp = page.waitForResponse(
    (r) => r.url().includes('/content/sop') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '保存' }).click()
  const body = (await (await createResp).json()) as { code: number; data?: unknown }
  expect(body.code).toBe(0)
  const sopId = idFromOkPayload(body.data)
  expect(sopId).toBeTruthy()

  await expect(page.locator('tr', { hasText: opts.sopName })).toBeVisible({ timeout: 15_000 })
  return { sopId: sopId! }
}

async function selectIpGroupInTree(page: Page, ipGroupId: number, groupNameHint?: string) {
  const treeReady = page.waitForResponse((r) => r.url().includes('/ip-group/tree') && r.status() === 200)
  await page.goto('/ims/ip-group')
  await expect(page.locator('h1')).toHaveText('IP 组运营', { timeout: 15_000 })
  await treeReady

  if (groupNameHint) {
    await page.locator('.ipg-tree-search input').fill(groupNameHint)
    const named = page.locator('.ipg-node', { hasText: groupNameHint })
    if (await named.count()) {
      const membersResp = page.waitForResponse(
        (r) => r.url().includes(`/ip-group/${ipGroupId}/members`) && r.status() === 200,
      )
      await named.first().click()
      await membersResp
      return
    }
  }

  const nodes = page.locator('.ipg-node.child')
  const count = await nodes.count()
  for (let i = 0; i < count; i++) {
    const membersResp = page
      .waitForResponse((r) => r.url().includes(`/ip-group/${ipGroupId}/members`) && r.status() === 200, {
        timeout: 8000,
      })
      .catch(() => null)
    await nodes.nth(i).click()
    if (await membersResp) return
  }
  throw new Error(`未在树中找到 IP 组 id=${ipGroupId}`)
}

/** IP 组 · 关联作者（种子 E2EClosureAuthor） */
export async function bindOpsAuthorToIpGroup(
  page: Page,
  ipGroupId: number,
  authorId = E2E_OPS_AUTHOR_ID,
  groupNameHint?: string,
) {
  await selectIpGroupInTree(page, ipGroupId, groupNameHint)
  const anchorsGet = page.waitForResponse(
    (r) => r.url().includes(`/ip-group/${ipGroupId}/anchors`) && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.locator('.tab', { hasText: '关联作者' }).click()
  await anchorsGet
  const anchorRow = page.locator('.ipg-detail-body tbody tr').filter({ hasText: E2E_OPS_AUTHOR_NAME })
  if ((await anchorRow.count()) === 0) {
    await page.locator('input[placeholder="作者 id"]').fill(String(authorId))
    const bindResp = page.waitForResponse(
      (r) => r.url().includes('/ip-group/') && r.url().includes('/anchors') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '绑定作者' }).click()
    const bindBody = (await (await bindResp).json()) as { code: number }
    expect(bindBody.code).toBe(0)
    const anchorsReload = page.waitForResponse(
      (r) => r.url().includes(`/ip-group/${ipGroupId}/anchors`) && r.request().method() === 'GET' && r.status() === 200,
    )
    await anchorsReload
  }
  await expect(anchorRow.first()).toBeVisible({ timeout: 15_000 })
}

/** 工作任务登记 · 保存一行并确认出任务 */
export async function registerWorkTaskRowViaUi(
  page: Page,
  opts: {
    ipGroupId: number
    workDate: string
    authorId: number
    competitionId: string
    competitionName: string
    groupNameHint?: string
  },
) {
  await bindOpsAuthorToIpGroup(page, opts.ipGroupId, opts.authorId, opts.groupNameHint)
  await page.goto('/ims/content/work-task')
  await expect(page.locator('h1')).toHaveText('工作任务登记', { timeout: 15_000 })

  await page.locator('input[placeholder="IP 组 id"]').fill(String(opts.ipGroupId))
  await page.locator('input[type="date"]').fill(opts.workDate)
  const sheetResp = page.waitForResponse((r) => r.url().includes('/work-task/sheet') && r.request().method() === 'GET')
  await page.getByRole('button', { name: '查询' }).click()
  await sheetResp

  const dataRows = page.locator('tbody tr').filter({ has: page.locator('input[type="checkbox"]') })
  await expect(dataRows.first()).toBeVisible({ timeout: 15_000 })

  const confirmedForComp = dataRows
    .filter({ hasText: opts.competitionId })
    .filter({ has: page.locator('td', { hasText: 'CONFIRMED' }) })
  if (await confirmedForComp.count()) {
    return
  }

  let targetRow = dataRows.filter({ has: page.locator('input[type="number"]:not([disabled])') }).first()
  if (!(await targetRow.count())) {
    const confirmedAny = dataRows.filter({ has: page.locator('td', { hasText: 'CONFIRMED' }) })
    if (await confirmedAny.count()) {
      await confirmedAny.first().locator('input[type="checkbox"]').check()
      const withdrawResp = page.waitForResponse(
        (r) => r.url().includes('/work-task/') && r.url().includes('/withdraw') && r.request().method() === 'POST',
      )
      await page.getByRole('button', { name: '撤回' }).click()
      await withdrawResp
      const reloadResp = page.waitForResponse(
        (r) => r.url().includes('/work-task/sheet') && r.request().method() === 'GET' && r.status() === 200,
      )
      await page.getByRole('button', { name: '查询' }).click()
      await reloadResp
      targetRow = dataRows.filter({ has: page.locator('input[type="number"]:not([disabled])') }).first()
    }
  }
  await expect(targetRow).toBeVisible({ timeout: 15_000 })
  await targetRow.locator('input[type="number"]').fill(String(opts.authorId))
  await targetRow.locator('input[placeholder="赛事 id"]').fill(opts.competitionId)
  await targetRow.locator('input[placeholder="名称"]').fill(opts.competitionName)

  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/work-task/sheet') && r.request().method() === 'POST' && r.status() === 200,
  )
  await page.getByRole('button', { name: '保存' }).click()
  const saveBody = (await (await saveResp).json()) as { code: number; data?: { assignments?: { id: number }[] } }
  expect(saveBody.code).toBe(0)
  const assignmentId = saveBody.data?.assignments?.[0]?.id
  expect(assignmentId).toBeTruthy()

  await targetRow.locator('input[type="checkbox"]').check()
  const confirmResp = page.waitForResponse(
    (r) => r.url().includes('/work-task/') && r.url().includes('/confirm') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '确认出任务' }).click()
  const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { generatedTaskCount?: number } }
  expect(confirmBody.code).toBe(0)
  expect((confirmBody.data?.generatedTaskCount ?? 0) >= 1).toBeTruthy()
}
