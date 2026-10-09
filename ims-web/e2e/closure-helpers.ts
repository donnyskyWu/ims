import { expect, type Locator, type Page } from '@playwright/test'

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

/** 内容抽屉内的结构化玩法区（竞足默认 Tab） */
export async function fillMatchSchemeViaUi(
  scope: Locator,
  opts: { matchId: string; homeName: string; awayName: string },
) {
  await scope.getByPlaceholder('matchId').fill(opts.matchId)
  await scope.getByPlaceholder('主队').fill(opts.homeName)
  await scope.getByPlaceholder('客队').fill(opts.awayName)
  await scope.getByRole('button', { name: '添加场次' }).click()
  await scope.getByRole('button', { name: '确定玩法' }).click()
  await expect(scope.getByText('已确定 1 场')).toBeVisible()
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
  // A prior in-flight /tree can satisfy treeReady before this navigation's load finishes.
  await expect(page.locator('.ipg-tree-body')).not.toContainText('加载中', { timeout: 15_000 })

  if (groupNameHint) {
    await page.locator('.ipg-tree-search input').fill(groupNameHint)
    const named = page.locator('.ipg-node', { hasText: groupNameHint })
    await expect(named.first()).toBeVisible({ timeout: 15_000 })
    const membersResp = page.waitForResponse(
      (r) => r.url().includes(`/ip-group/${ipGroupId}/members`) && r.status() === 200,
    )
    await named.first().click()
    await membersResp
    return
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
  const authorTab = page.locator('.tab', { hasText: '关联作者' })
  await authorTab.click()
  // selectGroup already loads anchors; the tab click does not refetch.
  const authorBody = page.locator('.ipg-detail-body')
  await expect(authorBody.getByText(E2E_OPS_AUTHOR_NAME).or(authorBody.getByText('暂无关联作者'))).toBeVisible({
    timeout: 15_000,
  })
  const anchorRow = page.locator('.ipg-detail-body tbody tr').filter({ hasText: E2E_OPS_AUTHOR_NAME })
  if ((await anchorRow.count()) === 0) {
    await page.locator('input[placeholder="作者 id"]').fill(String(authorId))
    const bindResp = page.waitForResponse(
      (r) => r.url().includes('/ip-group/') && r.url().includes('/anchors') && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '绑定作者' }).click()
    const bindBody = (await (await bindResp).json()) as { code: number }
    expect(bindBody.code).toBe(0)
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
    /** 本用例刚建的启用 SOP。多条公推模板并存时必须指定，避免 workers 抢最新一条。 */
    sopId?: number
    /** false：只保存登记行，不出任务（矩阵 Tab 再确认） */
    confirm?: boolean
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
  for (let attempt = 0; attempt < 5 && !(await targetRow.count()); attempt += 1) {
    const confirmedAny = page
      .locator('tbody tr')
      .filter({ has: page.locator('input[type="checkbox"]') })
      .filter({ has: page.locator('td', { hasText: 'CONFIRMED' }) })
    if (!(await confirmedAny.count())) break
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
    targetRow = page
      .locator('tbody tr')
      .filter({ has: page.locator('input[type="checkbox"]') })
      .filter({ has: page.locator('input[type="number"]:not([disabled])') })
      .first()
  }
  await expect(targetRow).toBeVisible({ timeout: 15_000 })
  await targetRow.locator('input[type="number"]').fill(String(opts.authorId))
  await targetRow.locator('input[placeholder="赛事 id"]').fill(opts.competitionId)
  await targetRow.locator('input[placeholder="名称"]').fill(opts.competitionName)
  if (opts.sopId) {
    const sopSelect = targetRow.getByTestId('wt-sop')
    await expect(sopSelect.locator(`option[value="${opts.sopId}"]`)).toHaveCount(1, { timeout: 15_000 })
    await sopSelect.selectOption(String(opts.sopId))
  }

  const saveResp = page.waitForResponse(
    (r) => r.url().includes('/work-task/sheet') && r.request().method() === 'POST' && r.status() === 200,
  )
  await page.getByRole('button', { name: '保存' }).click()
  const saveBody = (await (await saveResp).json()) as { code: number; data?: { assignments?: { id: number }[] } }
  expect(saveBody.code).toBe(0)
  const assignmentId = saveBody.data?.assignments?.[0]?.id
  expect(assignmentId).toBeTruthy()
  if (opts.confirm === false) return

  await targetRow.locator('input[type="checkbox"]').check()
  const confirmResp = page.waitForResponse(
    (r) => r.url().includes('/work-task/') && r.url().includes('/confirm') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '确认出任务' }).click()
  const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { generatedTaskCount?: number } }
  expect(confirmBody.code).toBe(0)
  expect((confirmBody.data?.generatedTaskCount ?? 0) >= 1).toBeTruthy()
}

/** TRAIN 资料库 · 发布 DOC 资料（纯 UI） */
export async function createTrainMaterialViaUi(
  page: Page,
  opts: { title: string },
): Promise<{ materialId: number }> {
  await page.goto('/ims/train/material')
  await expect(page.locator('h1')).toHaveText('培训资料库', { timeout: 15_000 })

  const firstCate = page.locator('.tree button.linkish').first()
  await expect(firstCate).toBeVisible({ timeout: 15_000 })
  await firstCate.click()

  await page.getByRole('button', { name: '上传资料' }).click()
  const modal = page.locator('.modal-mask .card').filter({ hasText: '上传资料' })
  await expect(modal).toBeVisible()
  await modal
    .locator('label.fld', { hasText: '标题' })
    .locator('xpath=following-sibling::input[1]')
    .fill(opts.title)

  const createResp = page.waitForResponse(
    (r) => r.url().includes('/train/material') && r.request().method() === 'POST' && r.status() === 200,
  )
  await modal.getByRole('button', { name: '发布' }).click()
  const body = (await (await createResp).json()) as { code: number; data?: { id?: number } }
  expect(body.code).toBe(0)
  const materialId = body.data?.id
  expect(materialId).toBeTruthy()

  await expect(page.locator('tr', { hasText: opts.title })).toBeVisible({ timeout: 15_000 })
  return { materialId: materialId! }
}

/** TRAIN 学习任务 · 下达任务（纯 UI · 资料多选） */
export async function createTrainTaskViaUi(
  page: Page,
  opts: { taskName: string; materialIds: number[]; assignUserIds: number[] },
): Promise<{ taskId: number }> {
  await page.goto('/ims/train/task')
  await expect(page.locator('h1')).toHaveText('学习任务管理', { timeout: 15_000 })

  await page.getByRole('button', { name: '下达学习任务' }).click()
  const modal = page.locator('.modal-mask .card').filter({ hasText: '下达学习任务' })
  await expect(modal).toBeVisible()
  await modal
    .locator('label.fld', { hasText: '任务名称' })
    .locator('xpath=following-sibling::input[1]')
    .fill(opts.taskName)

  for (const mid of opts.materialIds) {
    await modal.locator('label.mat-opt').filter({ hasText: `#${mid}` }).locator('input[type="checkbox"]').check()
  }
  await modal.locator('input[placeholder="如 1"]').fill(opts.assignUserIds.join(','))

  const createResp = page.waitForResponse(
    (r) => r.url().includes('/train/task') && r.request().method() === 'POST' && r.status() === 200,
  )
  await modal.getByRole('button', { name: '保存' }).click()
  const body = (await (await createResp).json()) as { code: number; data?: { id?: number } }
  expect(body.code).toBe(0)
  const taskId = body.data?.id
  expect(taskId).toBeTruthy()

  await expect(page.locator('tr', { hasText: opts.taskName })).toBeVisible({ timeout: 15_000 })
  return { taskId: taskId! }
}

/** TRAIN 学习中心 · 标记学完并确认（纯 UI） */
export async function completeTrainStudyViaUi(page: Page, taskId: number, taskName: string) {
  await page.goto(`/ims/train/study/${taskId}`)
  await expect(page.locator('h1')).toHaveText('学习中心', { timeout: 15_000 })
  await expect(page.getByText(taskName)).toBeVisible()

  const progressResp = page.waitForResponse(
    (r) =>
      r.url().includes(`/train/task/${taskId}/progress`) &&
      r.request().method() === 'PUT' &&
      r.status() === 200,
  )
  await page.getByRole('button', { name: '标记当前资料已学完' }).click()
  const progBody = (await (await progressResp).json()) as { code: number }
  expect(progBody.code).toBe(0)

  const confirmResp = page.waitForResponse(
    (r) =>
      r.url().includes(`/train/task/${taskId}/confirm`) &&
      r.request().method() === 'POST' &&
      r.status() === 200,
  )
  await page.getByRole('button', { name: '完成确认' }).click()
  const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { confirmStatus?: string } }
  expect(confirmBody.code).toBe(0)
  expect(confirmBody.data?.confirmStatus).toBe('CONFIRMED')
  await expect(page.getByText('学习已完成 · CONFIRMED')).toBeVisible({ timeout: 10_000 })
}

/** S3 FIN closure · 与 `live_fin_e2e_seed` 一致 */
export const E2E_FIN_ACCOUNT_NO = 'AC-E2E-FIN'
export const E2E_FIN_PHONE_CODE = 'E2E-FIN-PHONE'

/** 纯 UI 读取 FIN E2E 种子账号/实名人/手机 id（依赖 run_e2e refresh 种子） */
export async function resolveLiveFinRegisterIdsViaUi(page: Page): Promise<{
  accountId: number
  realnamePersonId: number
  deviceId: number
  ipGroupId?: number
  ipGroupName?: string
}> {
  await page.goto('/ims/corp/account/douyin')
  await page.locator('input[placeholder="账号编号/昵称"]').fill(E2E_FIN_ACCOUNT_NO)
  const accListResp = page.waitForResponse(
    (r) => r.url().includes('/corp/account/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await accListResp
  const accRow = page.locator('tbody tr', { hasText: E2E_FIN_ACCOUNT_NO }).first()
  await expect(accRow).toBeVisible({ timeout: 15_000 })
  const accDetailResp = page.waitForResponse(
    (r) => /\/corp\/account\/\d+/.test(r.url()) && r.request().method() === 'GET' && r.status() === 200,
  )
  await accRow.getByRole('button', { name: '详情' }).click()
  const accDetailBody = (await (await accDetailResp).json()) as {
    code: number
    data?: { id?: number; realnameId?: number; ipGroupId?: number; ipGroupName?: string }
  }
  expect(accDetailBody.code).toBe(0)
  const accountId = accDetailBody.data?.id
  const realnamePersonId = accDetailBody.data?.realnameId
  expect(accountId).toBeTruthy()
  expect(realnamePersonId).toBeTruthy()

  await page.goto('/ims/corp/device/phone')
  await page.locator('input[placeholder="设备编号 / 型号"]').fill(E2E_FIN_PHONE_CODE)
  const phoneListResp = page.waitForResponse(
    (r) => r.url().includes('/corp/device/phone/page') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  const phoneListBody = (await (await phoneListResp).json()) as {
    code: number
    data?: { list?: Array<{ id?: number; phoneCode?: string }> }
  }
  expect(phoneListBody.code).toBe(0)
  const phoneHit = phoneListBody.data?.list?.find(
    (r) => r.phoneCode === E2E_FIN_PHONE_CODE || (r as { deviceNumber?: string }).deviceNumber === E2E_FIN_PHONE_CODE,
  )
  expect(phoneHit?.id).toBeTruthy()

  return {
    accountId: accountId!,
    realnamePersonId: realnamePersonId!,
    deviceId: phoneHit!.id!,
    ipGroupId: accDetailBody.data?.ipGroupId || undefined,
    ipGroupName: accDetailBody.data?.ipGroupName || '',
  }
}

/** LIVE 登记 → 下播提交/核准（纯 UI）· 返回场次 ID */
export async function registerLiveSessionConfirmedReportViaUi(
  page: Page,
  ids: { accountId: number; realnamePersonId: number; deviceId: number },
  opts?: {
    topic?: string
    gmv?: number
    refundAmount?: number
    planStartTime?: string
    actualStart?: string
    actualEnd?: string
  },
): Promise<{
  sessionCode: string
  realnameName: string
  responsibleUserName: string
  responsibleUserId: number
}> {
  const topic = opts?.topic ?? `E2E FIN ${Date.now()}`
  const gmv = opts?.gmv ?? 100_000
  const refundAmount = opts?.refundAmount ?? 2_000

  await page.goto('/ims/live/sessions')
  await expect(page.locator('h1')).toHaveText('直播管理', { timeout: 15_000 })
  await page.getByRole('button', { name: '新建场次登记' }).click()
  const drawer = page.locator('.drawer').filter({ hasText: '开播登记' })
  await expect(drawer).toBeVisible()
  await drawer.locator('label', { hasText: '平台账号 id' }).locator('..').locator('input').fill(String(ids.accountId))
  await drawer
    .locator('label', { hasText: '实名人 id' })
    .locator('..')
    .locator('input')
    .fill(String(ids.realnamePersonId))
  await drawer.locator('label', { hasText: '手机设备 id' }).locator('..').locator('input').fill(String(ids.deviceId))
  await drawer.locator('label', { hasText: '主题' }).locator('..').locator('input').fill(topic)
  if (opts?.planStartTime) {
    await drawer.locator('label', { hasText: '计划开播' }).locator('..').locator('input').fill(opts.planStartTime)
  }

  const regResp = page.waitForResponse(
    (r) => r.url().includes('/live/register') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByRole('button', { name: '提交登记' }).click()
  const regBody = (await (await regResp).json()) as {
    code: number
    data?: {
      sessionCode?: string
      sessionStatus?: string
      realnameName?: string
      responsibleUserName?: string
      responsibleUserId?: number
    }
  }
  expect(regBody.code).toBe(0)
  const sessionCode = regBody.data?.sessionCode
  expect(sessionCode).toBeTruthy()

  const detailDrawer = page.locator('.drawer').filter({ hasText: '场次' })
  await expect(detailDrawer).toBeVisible({ timeout: 15_000 })

  if (regBody.data?.sessionStatus === 'PENDING_RISK_CHECK') {
    await detailDrawer.locator('.tab', { hasText: '风控登记' }).click()
    const riskResp = page.waitForResponse(
      (r) => r.url().includes('/risk-check') && r.request().method() === 'POST' && r.status() === 200,
    )
    await detailDrawer.getByRole('button', { name: '执行风控' }).click()
    await riskResp
  }

  await detailDrawer.locator('.tab', { hasText: '下播与 GMV' }).click()
  if (opts?.actualStart) {
    await detailDrawer.getByTestId('live-report-start').fill(opts.actualStart)
  }
  if (opts?.actualEnd) {
    await detailDrawer.getByTestId('live-report-end').fill(opts.actualEnd)
  }
  await detailDrawer.locator('label', { hasText: 'GMV' }).locator('..').locator('input').fill(String(gmv))
  await detailDrawer
    .locator('label', { hasText: '退款' })
    .locator('..')
    .locator('input')
    .fill(String(refundAmount))

  const reportResp = page.waitForResponse(
    (r) => r.url().includes('/live/report/') && r.request().method() === 'POST' && r.status() === 200,
  )
  await detailDrawer.getByRole('button', { name: '提交下播' }).click()
  await reportResp

  const confirmResp = page.waitForResponse(
    (r) => r.url().includes('/live/report/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
  )
  await detailDrawer.getByTestId('live-report-confirm').click()
  const confirmBody = (await (await confirmResp).json()) as { code: number }
  expect(confirmBody.code).toBe(0)

  return {
    sessionCode: sessionCode!,
    realnameName: regBody.data?.realnameName || '',
    responsibleUserName: regBody.data?.responsibleUserName || '',
    responsibleUserId: regBody.data?.responsibleUserId || 0,
  }
}

/** FIN 成本录入 + 核准（纯 UI）。costs 只覆盖传入项，缺省与 #50 样例一致。 */
export async function submitAndConfirmFinCostViaUi(
  page: Page,
  sessionCode: string,
  costs?: {
    commissionRate?: string
    adCost?: string
    rechargeCost?: string
    fixedCost?: string
    sampleCost?: string
    shareDaren?: string
    shareRealname?: string
  },
) {
  await page.goto('/ims/fin/cost')
  await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const pendingResp = page.waitForResponse(
    (r) => r.url().includes('/fin/cost/pending-sessions') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await pendingResp
  const row = page.locator('tbody tr', { hasText: sessionCode }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.getByRole('button', { name: '录入' }).click()
  const entryDrawer = page.locator('.drawer.on').filter({ hasText: '成本录入' })
  await expect(entryDrawer).toBeVisible()
  await entryDrawer.getByRole('spinbutton', { name: '佣金率' }).fill(costs?.commissionRate ?? '0.05')
  await entryDrawer.getByRole('spinbutton', { name: '投放成本' }).fill(costs?.adCost ?? '5000')
  await entryDrawer.getByRole('spinbutton', { name: '冲话费摊销' }).fill(costs?.rechargeCost ?? '100')
  await entryDrawer.getByRole('spinbutton', { name: '固定成本' }).fill(costs?.fixedCost ?? '2000')
  await entryDrawer.getByRole('spinbutton', { name: '样品成本' }).fill(costs?.sampleCost ?? '500')
  await entryDrawer.getByRole('spinbutton', { name: '达人分成' }).fill(costs?.shareDaren ?? '3000')
  await entryDrawer.getByRole('spinbutton', { name: '实名人分成' }).fill(costs?.shareRealname ?? '1000')

  const submitResp = page.waitForResponse(
    (r) => r.url().includes('/fin/cost/') && r.request().method() === 'POST' && r.status() === 200,
  )
  await entryDrawer.getByRole('button', { name: '提交' }).click()
  await submitResp
  await expect(entryDrawer).not.toBeVisible({ timeout: 10_000 })

  await page.locator('.tab', { hasText: '已录入管理' }).click()
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const enteredRow = page.locator('tbody tr', { hasText: sessionCode }).first()
  await expect(enteredRow).toContainText('已提交')

  const confirmResp = page.waitForResponse(
    (r) => r.url().includes('/fin/cost/') && r.url().includes('/confirm') && r.request().method() === 'PUT',
  )
  await enteredRow.getByRole('button', { name: '核准' }).click()
  const confirmBody = (await (await confirmResp).json()) as { code: number; data?: { entryStatus?: string } }
  expect(confirmBody.code).toBe(0)
  expect(confirmBody.data?.entryStatus).toBe('CONFIRMED')
  await expect(enteredRow).toContainText('已核准', { timeout: 10_000 })
}

/** FIN 成本更正（纯 UI · 须已 CONFIRMED）→ 触发利润重算 */
export async function submitFinCostCorrectionViaUi(
  page: Page,
  sessionCode: string,
  patch: { adCost?: number; shareDaren?: number },
  reason: string,
) {
  await page.goto('/ims/fin/cost')
  await expect(page.locator('h1')).toHaveText('成本核算', { timeout: 15_000 })
  await page.locator('.tab', { hasText: '已录入管理' }).click()
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/fin/cost/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const enteredRow = page.locator('tbody tr', { hasText: sessionCode }).first()
  await expect(enteredRow).toContainText('已核准', { timeout: 15_000 })
  await enteredRow.getByTestId('fin-cost-correction-open').click()
  const drawer = page.locator('.drawer.on').filter({ hasText: '成本更正' })
  await expect(drawer).toBeVisible()
  if (patch.adCost != null) {
    await drawer.getByRole('spinbutton', { name: '投放成本' }).fill(String(patch.adCost))
  }
  if (patch.shareDaren != null) {
    await drawer.getByRole('spinbutton', { name: '达人分成' }).fill(String(patch.shareDaren))
  }
  await drawer.getByTestId('fin-cost-correction-reason').fill(reason)
  const corrResp = page.waitForResponse(
    (r) => r.url().includes('/correction') && r.request().method() === 'POST' && r.status() === 200,
  )
  await drawer.getByTestId('fin-cost-correction-submit').click()
  const corrBody = (await (await corrResp).json()) as {
    code: number
    data?: { recalcTriggered?: boolean; correctionNo?: string }
  }
  expect(corrBody.code).toBe(0)
  expect(corrBody.data?.recalcTriggered).toBe(true)
  expect(corrBody.data?.correctionNo).toBeTruthy()
  await expect(drawer).not.toBeVisible({ timeout: 10_000 })
}

/** FIN 分成单双审 → 发放 PAID_OFF（纯 UI · 须已核准成本） */
export async function approveAndPayoffFinSharesViaUi(page: Page, sessionCode: string) {
  await page.goto('/ims/fin/share/result')
  await expect(page.locator('h1')).toHaveText('分成单管理', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await listResp
  const sum = page.getByTestId('fin-share-split-sum')
  await expect(sum).toContainText('4,000.00')
  await expect(sum).toContainText('总额')

  for (const target of ['达人', '实名人']) {
    const row = () => page.locator('tbody tr', { hasText: sessionCode }).filter({ hasText: target }).first()
    await expect(row()).toContainText('待审', { timeout: 15_000 })

    const finPut = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const finList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await row().getByTestId('fin-share-audit-finance').click()
    const finBody = (await (await finPut).json()) as { code: number; data?: { bothPassed?: boolean; status?: string } }
    expect(finBody.code).toBe(0)
    expect(finBody.data?.bothPassed).toBe(false)
    expect(finBody.data?.status).toBe('PENDING_AUDIT')
    await finList

    const bizPut = page.waitForResponse(
      (r) => r.url().includes('/audit') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const bizList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await row().getByTestId('fin-share-audit-business').click()
    const bizBody = (await (await bizPut).json()) as { code: number; data?: { bothPassed?: boolean; status?: string } }
    expect(bizBody.code).toBe(0)
    expect(bizBody.data?.bothPassed).toBe(true)
    expect(bizBody.data?.status).toBe('AUDITED')
    await bizList
    await expect(row()).toContainText('已审', { timeout: 10_000 })

    await row().getByTestId('fin-share-payoff-open').click()
    const drawer = page.getByTestId('fin-share-payoff-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByTestId('fin-share-payoff-note').fill(`E2E payoff ${target}`)
    const payPut = page.waitForResponse(
      (r) => r.url().includes('/payoff') && r.request().method() === 'PUT' && r.status() === 200,
    )
    const payList = page.waitForResponse(
      (r) => r.url().includes('/fin/share/results') && r.request().method() === 'GET' && r.status() === 200,
    )
    await drawer.getByTestId('fin-share-payoff-submit').click()
    const payBody = (await (await payPut).json()) as { code: number }
    expect(payBody.code).toBe(0)
    await payList
    await expect(row()).toContainText('已发放', { timeout: 10_000 })
  }
}

/** 台账对账：场次 × 成本 × 利润 × 分成 四账一致（纯 UI） */
export async function openFinLedgerReconcileViaUi(page: Page, sessionCode: string) {
  await page.goto('/ims/fin/ledger')
  await expect(page.locator('h1')).toHaveText('台账对账', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const profitResp = page.waitForResponse(
    (r) => r.url().includes('/fin/profit/') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  await profitResp
  await expect(page.getByTestId('fin-ledger-consistent')).toHaveText('四账一致', { timeout: 15_000 })
  await expect(page.getByTestId('fin-ledger-session')).toContainText(sessionCode)
  await expect(page.getByTestId('fin-ledger-cost')).toContainText('16,600.00')
  await expect(page.getByTestId('fin-ledger-profit')).toContainText('81,400.00')
  await expect(page.getByTestId('fin-ledger-share')).toContainText('4,000.00')
  await expect(page.getByTestId('fin-ledger-share')).toContainText('已发放')
}

/** DC-002 利润反查：列表筛选 + 打开 BR-209 链路抽屉（纯 UI） */
export async function openFinProfitTraceChainViaUi(page: Page, sessionCode: string) {
  await page.goto('/ims/fin/profit-trace')
  await expect(page.locator('h1')).toHaveText('利润反查', { timeout: 15_000 })
  await page.locator('input[placeholder="场次 ID"]').fill(sessionCode)
  const listResp = page.waitForResponse(
    (r) => r.url().includes('/dc/profit-trace/list') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByRole('button', { name: '查询' }).click()
  const listBody = (await (await listResp).json()) as {
    code: number
    data?: { list?: Array<{ sessionCode?: string; netProfit?: number }> }
  }
  expect(listBody.code).toBe(0)
  const traceRow = listBody.data?.list?.find((r) => r.sessionCode === sessionCode)
  expect(traceRow?.netProfit).toBe(81_400)

  const uiRow = page.locator('tbody tr', { hasText: sessionCode }).first()
  await expect(uiRow).toBeVisible({ timeout: 15_000 })
  await expect(uiRow).toContainText('81,400.00')

  const chainResp = page.waitForResponse(
    (r) =>
      r.url().includes('/dc/profit-trace/') &&
      !r.url().includes('/list') &&
      !r.url().includes('/share-detail') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
  )
  await uiRow.getByRole('button', { name: '反查' }).click()
  const chainBody = (await (await chainResp).json()) as {
    code: number
    data?: { chain?: { session?: { sessionCode?: string }; costDetail?: unknown[] } }
  }
  expect(chainBody.code).toBe(0)
  expect(chainBody.data?.chain?.session?.sessionCode).toBe(sessionCode)
  expect((chainBody.data?.chain?.costDetail || []).length).toBeGreaterThanOrEqual(5)

  const drawer = page.getByTestId('fin-profit-trace-chain-drawer')
  await expect(drawer).toBeVisible()
  return drawer
}

/** DC-001 账号穿透：入口搜索 + 关系图/明细表（纯 UI） */
export async function openDcAccountTraceViaUi(page: Page, accountNo: string, sessionCode?: string) {
  await page.goto('/ims/dc/trace')
  await expect(page.locator('h1')).toHaveText('穿透查询', { timeout: 15_000 })
  await page.getByTestId('dc-trace-keyword').fill(accountNo)
  const entryResp = page.waitForResponse(
    (r) => r.url().includes('/dc/trace/entry') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('dc-trace-search-entry').click()
  const entryBody = (await (await entryResp).json()) as {
    code: number
    data?: Array<{ entryType?: string; entryId?: string; entryLabel?: string }>
  }
  expect(entryBody.code).toBe(0)
  const hit =
    entryBody.data?.find((e) => e.entryLabel?.includes(accountNo)) ?? entryBody.data?.[0]
  expect(hit?.entryId).toBeTruthy()

  const queryResp = page.waitForResponse(
    (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
  )
  await page
    .locator(`[data-testid="dc-trace-entry-pick"][data-entry-id="${hit!.entryId}"]`)
    .click()
  const queryBody = (await (await queryResp).json()) as {
    code: number
    data?: {
      queryCostMs?: number
      dataAsOf?: string
      nodes?: Array<{ nodeType?: string; nodeLabel?: string }>
      detailList?: { list?: Array<{ sessionCode?: string; accountNo?: string; realnameName?: string }> }
    }
  }
  expect(queryBody.code).toBe(0)
  expect((queryBody.data?.queryCostMs ?? 0) >= 0).toBe(true)
  expect(queryBody.data?.dataAsOf).toBeTruthy()
  const nodeTypes = (queryBody.data?.nodes || []).map((n) => n.nodeType)
  expect(nodeTypes).toContain('ACCOUNT')
  expect(nodeTypes).toContain('SESSION')

  await expect(page.getByTestId('dc-trace-meta')).toBeVisible()
  await expect(page.getByTestId('dc-trace-graph')).toContainText('ACCOUNT')
  await expect(page.getByTestId('dc-trace-graph')).toContainText('SESSION')
  const detailTable = page.getByTestId('dc-trace-detail-table')
  await expect(detailTable).toContainText(accountNo)
  if (sessionCode) {
    await expect(detailTable).toContainText(sessionCode)
    const listed = queryBody.data?.detailList?.list?.some((r) => r.sessionCode === sessionCode)
    expect(listed).toBe(true)
  }
  return queryBody.data
}

/** DC-001 指定入口穿透：选类型 → 搜入口 → 关系图/明细表（纯 UI） */
export async function openDcTypedEntryTraceViaUi(
  page: Page,
  entryType: 'PERSON' | 'ACCOUNT' | 'ASSET' | 'SESSION' | 'RESPONSIBLE' | 'IP_GROUP',
  keyword: string,
  sessionCode: string,
  match: { entryId: string },
) {
  await page.goto('/ims/dc/trace')
  await expect(page.locator('h1')).toHaveText('穿透查询', { timeout: 15_000 })
  await page.getByTestId('dc-trace-entry-type').selectOption(entryType)
  await page.getByTestId('dc-trace-keyword').fill(keyword)
  const entryResp = page.waitForResponse(
    (r) => r.url().includes('/dc/trace/entry') && r.request().method() === 'GET' && r.status() === 200,
  )
  await page.getByTestId('dc-trace-search-entry').click()
  const entryBody = (await (await entryResp).json()) as {
    code: number
    data?: Array<{ entryType?: string; entryId?: string; entryLabel?: string }>
  }
  expect(entryBody.code).toBe(0)
  const hit = entryBody.data?.find((e) => e.entryType === entryType && e.entryId === match.entryId)
  expect(hit?.entryId).toBe(match.entryId)
  expect(hit?.entryLabel).toBeTruthy()

  const queryResp = page.waitForResponse(
    (r) => r.url().includes('/dc/trace/query') && r.request().method() === 'POST' && r.status() === 200,
  )
  await page
    .locator(
      `[data-testid="dc-trace-entry-pick"][data-entry-type="${entryType}"][data-entry-id="${hit!.entryId}"]`,
    )
    .click()
  const queryBody = (await (await queryResp).json()) as {
    code: number
    data?: {
      queryCostMs?: number
      dataAsOf?: string
      nodes?: Array<{ nodeType?: string; nodeId?: string; nodeLabel?: string }>
      detailList?: { list?: Array<{ sessionCode?: string }> }
    }
  }
  expect(queryBody.code).toBe(0)
  expect((queryBody.data?.queryCostMs ?? 0) >= 0).toBe(true)
  expect(queryBody.data?.dataAsOf).toBeTruthy()
  const nodeTypes = (queryBody.data?.nodes || []).map((n) => n.nodeType)
  expect(nodeTypes).toContain('SESSION')
  expect(queryBody.data?.detailList?.list?.some((row) => row.sessionCode === sessionCode)).toBe(true)

  const current = page.getByTestId('dc-trace-current-entry')
  await expect(current).toBeVisible()
  await expect(current).toContainText(hit!.entryLabel!)
  await expect(page.getByTestId('dc-trace-graph')).toContainText('SESSION')
  await expect(page.getByTestId('dc-trace-detail-table')).toContainText(sessionCode)
  return { hit, data: queryBody.data }
}

/** DC-001 场次下钻：明细表点场次 ID 打开抽屉（纯 UI，须已在穿透结果页） */
export async function openDcSessionDetailViaUi(page: Page, sessionCode: string) {
  const sessionBtn = page
    .getByTestId('dc-trace-detail-table')
    .locator(`button[data-session-code="${sessionCode}"]`)
  await expect(sessionBtn).toBeVisible({ timeout: 15_000 })
  await sessionBtn.scrollIntoViewIfNeeded()
  const detailResp = page.waitForResponse(
    (r) =>
      r.url().includes('/dc/trace/detail/') &&
      r.request().method() === 'GET' &&
      r.status() === 200,
    { timeout: 65_000 },
  )
  await sessionBtn.click()
  const detailBody = (await (await detailResp).json()) as {
    code: number
    data?: {
      sessionCode?: string
      liveData?: { gmv?: number }
      profit?: { netProfit?: number }
      costDetail?: Array<{ costItem?: string; amount?: number | null }>
    }
  }
  expect(detailBody.code).toBe(0)
  expect(detailBody.data?.sessionCode).toBe(sessionCode)
  const drawer = page.getByTestId('dc-trace-session-drawer')
  await expect(drawer).toBeVisible()
  await expect(drawer).toContainText(sessionCode)
  return { drawer, detail: detailBody.data }
}
