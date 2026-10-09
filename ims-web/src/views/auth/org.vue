<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>组织架构同步</h1>
        <div class="sub">AUTH-002 · 事件验签入队后写入本地用户 · 不写 Football</div>
      </div>
      <div class="acts">
        <button
          class="btn btn-sec"
          type="button"
          data-testid="org-replay-open"
          :disabled="!canManage"
          :title="canManage ? '' : '无操作权限'"
          @click="replayOpen = true"
        >
          重放失败事件
        </button>
        <button
          class="btn btn-sec"
          type="button"
          data-testid="org-local-reconcile"
          :disabled="!canManage"
          :title="canManage ? '' : '无操作权限'"
          @click="localConfirm = true"
        >
          本地对账
        </button>
        <button
          class="btn btn-pri"
          type="button"
          data-testid="org-dingtalk-sync"
          :disabled="!canManage"
          :title="canManage ? '' : '无操作权限'"
          @click="confirming = true"
        >
          手动对账
        </button>
      </div>
    </div>
    <div v-if="confirming" class="card" style="margin-bottom: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">确认全量对账</div>
      <div class="sub">只核对本系统已经同步的人员，并写入一条对账事件。</div>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-pri btn-sm" type="button" @click="reconcile">确认执行</button>
        <button class="btn btn-sec btn-sm" type="button" @click="confirming = false">取消</button>
      </div>
    </div>
    <div v-if="localConfirm" class="card" style="margin-bottom: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">确认本地对账</div>
      <div class="sub">只核对本系统已经同步的人员，写入一条对账事件。不拉取钉钉通讯录。</div>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="org-local-confirm" @click="localReconcile">确认执行</button>
        <button class="btn btn-sec btn-sm" type="button" @click="localConfirm = false">取消</button>
      </div>
    </div>
    <p v-if="msg" class="hint" style="margin-bottom: 10px">{{ msg }}</p>
    <div class="g4">
      <div class="card stat">
        <span class="l">同步延迟</span>
        <div class="n">{{ metricReady && !metricError && metrics.delayMillis != null ? metrics.delayMillis : '—' }}<small v-if="metricReady && !metricError"> ms</small></div>
        <div class="d">{{ metricError || levelText }}</div>
      </div>
      <div class="card stat">
        <span class="l">平均延迟</span>
        <div class="n">{{ metricReady && !metricError ? metrics.avgSyncDelayMinutes ?? '—' : '—' }}<small v-if="metricReady && !metricError"> 分</small></div>
        <div class="d">目标 &lt; 5 分钟</div>
      </div>
      <div class="card stat">
        <span class="l">成功率</span>
        <div class="n">{{ metricReady && !metricError && metrics.successRate != null ? percent(metrics.successRate) : '—' }}</div>
        <div class="d">GET /auth/org/sync-metrics</div>
      </div>
      <div class="card stat">
        <span class="l">事件数</span>
        <div class="n">{{ eventReady && !eventError ? total : '—' }}</div>
        <div class="d">{{ eventError || 'GET /auth/org/events' }}</div>
      </div>
    </div>
    <div class="card" data-testid="org-report" style="margin: 12px 0">
      <div style="font-weight: 600; margin-bottom: 8px">对账报告</div>
      <div v-if="!reportReady" class="empty"><div class="et">加载中</div></div>
      <div v-else-if="!canManage" class="empty" data-testid="org-report-denied">
        <div class="et">无操作权限</div>
        <div class="es">对账报告和失败事件重放仅 R1。人员列表按本部门精确查看，不含下级。</div>
      </div>
      <div v-else-if="!reportFound" class="empty" data-testid="org-report-empty">
        <div class="et">还没有对账报告</div>
        <div class="es">本地对账不拉取钉钉。生成后这里显示差异数、修正数和失败明细。</div>
      </div>
      <div v-else data-testid="org-report-body">
        <div>差异 {{ report.diffCount }} · 修正 {{ report.fixedCount }} · 本地人员 {{ report.localUserCount }}</div>
        <div class="sub">来源本地队列 · {{ text(report.triggeredAt) }}</div>
        <div v-if="!report.failures.length" data-testid="org-report-failures-empty">没有失败明细</div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'users' }" @click="tab = 'users'">人员列表</div>
      <div class="tab" :class="{ on: tab === 'events' }" @click="tab = 'events'">同步事件</div>
    </div>
    <template v-if="tab === 'users'">
    <div class="card" data-testid="org-dept-tree" style="margin-bottom: 12px">
      <div style="font-weight: 600; margin-bottom: 8px">部门树</div>
      <div class="sub" style="margin-bottom: 8px">来自已同步人员的部门，不另建部门接口。</div>
      <form class="qbar" style="margin-bottom: 10px" @submit.prevent>
        <input v-model="deptQuery" data-testid="org-dept-filter" placeholder="筛选部门" style="width: 180px" />
        <button class="btn btn-sec btn-sm" type="button" data-testid="org-dept-all" @click="clearDept">全部部门</button>
      </form>
      <div v-if="!deptReady" class="empty"><div class="et">加载中</div></div>
      <div v-else-if="!deptNodes.length" class="empty" data-testid="org-dept-empty">
        <div class="et">还没有部门</div>
        <div class="es">模拟入职或钉钉同步写入部门后，部门会显示在这里。</div>
      </div>
      <div v-else-if="!visibleDeptNodes.length" class="empty" data-testid="org-dept-empty">
        <div class="et">没有匹配的部门</div>
        <div class="es">换一个部门名称或编号再筛。</div>
      </div>
      <div v-else class="cattabs" style="margin-bottom: 0">
        <button
          v-for="node in visibleDeptNodes"
          :key="node.id"
          class="cattab"
          :class="{ on: selectedDeptId === node.id }"
          type="button"
          data-testid="org-dept-node"
          @click="pickDept(node.id)"
        >
          {{ node.name }}<span class="cbadge">{{ node.count }}</span>
        </button>
      </div>
    </div>
    <div class="tbl-block">
      <form class="qbar" style="margin-bottom: 10px" @submit.prevent="searchUsers">
        <input v-model="keyword" data-testid="org-user-keyword" placeholder="姓名 / 钉钉用户" style="width: 180px" />
        <input v-model="deptIdText" data-testid="org-dept-id" placeholder="部门编号" style="width: 120px" />
        <button class="btn btn-pri btn-sm" type="submit" data-testid="org-user-search">查询</button>
        <span class="sub" data-testid="org-dept-exact">精确匹配该部门，不含下级</span>
      </form>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>姓名</th>
              <th>手机</th>
              <th>部门</th>
              <th>岗位</th>
              <th>授予角色</th>
              <th>钉钉</th>
              <th>同步状态</th>
              <th>账号状态</th>
              <th>最近同步</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!userReady">
              <td colspan="9" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!users.length">
              <td colspan="9" style="white-space: normal">
                <div class="empty" data-testid="org-user-empty">
                  <div class="et">{{ userEmptyTitle }}</div>
                  <div class="es">{{ userEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in users" v-else :key="String(row.userId)" data-testid="org-user-row">
              <td style="font-weight: 500">
                <button class="btn btn-txt btn-sm" type="button" data-testid="org-user-open" @click="openUser(row)">
                  {{ text(row.nickname) }}
                </button>
              </td>
              <td class="masked">{{ text(row.mobileMasked) }}</td>
              <td data-testid="org-user-dept">{{ names(row.deptNames) }}</td>
              <td data-testid="org-user-position">{{ text(row.positionName) }}</td>
              <td data-testid="org-user-roles">{{ names(row.grantedRoleNames) }}</td>
              <td class="mono">{{ text(row.dingtalkUserId) }}</td>
              <td>{{ syncText(row) }}</td>
              <td data-testid="org-user-status">{{ statusText(row.status) }}</td>
              <td class="mono">{{ text(row.lastSyncTime) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ userTotal }} 条</span></div>
    </div>
    </template>
    <div v-else class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>类型</th>
              <th>事件 ID</th>
              <th>部门变更</th>
              <th>状态</th>
              <th>重试</th>
              <th>同步时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!eventReady">
              <td colspan="7" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!events.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ eventError || '没有同步事件' }}</div>
                  <div class="es">对账成功后，这里会出现对账记录。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in events" v-else :key="String(row.id)" data-testid="org-event-row">
              <td>{{ eventLabel(row.eventType) }}</td>
              <td class="mono">{{ text(row.dingtalkEventId) }}</td>
              <td>{{ deptChange(row) }}</td>
              <td>{{ text(row.syncStatus) }}</td>
              <td class="num">{{ row.retryCount ?? 0 }}</td>
              <td class="mono">{{ text(row.syncedAt) }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" data-testid="org-event-open" @click="openEvent(row)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>
    <ProtoDrawer :open="detailOpen" title="人员详情" width="560px" @close="detailOpen = false">
      <div v-if="detail" data-testid="org-user-drawer">
        <p v-if="detail.status === 'FROZEN'" class="hint" data-testid="org-user-frozen">
          该人员已冻结，不能登录，权限已失效。名下在用账号与资产待归还，未回收证件待回收。
        </p>
        <div class="formrow one">
          <div class="fld"><label>姓名</label><div>{{ text(detail.nickname) }}</div></div>
          <div class="fld"><label>岗位</label><div data-testid="org-detail-position">{{ text(detail.positionName) }}</div></div>
          <div class="fld"><label>部门</label><div data-testid="org-detail-dept">{{ names(detail.deptNames) }}</div></div>
          <div class="fld"><label>账号状态</label><div data-testid="org-detail-status">{{ statusText(detail.status) }}</div></div>
          <div class="fld"><label>授予角色</label><div data-testid="org-detail-roles">{{ names(detail.grantedRoleNames) }}</div></div>
          <div class="fld"><label>权限码</label><div data-testid="org-detail-perms">{{ names(detail.grantedPermCodes) }}</div></div>
          <div class="fld"><label>权限缓冲至</label><div data-testid="org-detail-buffer">{{ text(detail.bufferUntil) }}</div></div>
        </div>
        <div v-if="diff" data-testid="org-user-diff" class="card" style="margin: 12px 0">
          <div style="font-weight: 600">权限 diff</div>
          <div data-testid="org-diff-summary">{{ text(diff.summary) }}</div>
          <div data-testid="org-diff-dept">{{ text(diff.beforeDept) }} → {{ text(diff.afterDept) }}</div>
          <div data-testid="org-diff-position">{{ text(diff.beforePosition) }} → {{ text(diff.afterPosition) }}</div>
          <div data-testid="org-diff-retained">保留 {{ names(diff.retainedRoleNames) }}</div>
          <div data-testid="org-diff-added">新增 {{ names(diff.addedRoleNames) }}</div>
        </div>
        <div data-testid="org-user-holdings" class="card">
          <div style="font-weight: 600">名下终态</div>
          <div>账号在用 {{ holding.accountInUse }}</div>
          <div>资产在用 {{ holding.assetInUse }}</div>
          <div>证件生效或待回收 {{ holding.certActive }}</div>
          <div>证件已回收 {{ holding.certRecycled }}</div>
        </div>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="eventOpen" title="事件详情" width="480px" @close="eventOpen = false">
      <div v-if="eventDetail" data-testid="org-event-drawer">
        <div class="formrow one">
          <div class="fld"><label>类型</label><div>{{ eventLabel(eventDetail.eventType) }}</div></div>
          <div class="fld"><label>事件 ID</label><div class="mono">{{ text(eventDetail.dingtalkEventId) }}</div></div>
          <div class="fld"><label>部门</label><div>{{ deptChange(eventDetail) }}</div></div>
          <div class="fld"><label>处理轨迹</label><div data-testid="org-event-timeline">{{ timeline(eventDetail) }}</div></div>
        </div>
        <div v-if="eventPayload" class="card" style="margin-top: 12px">
          <div style="font-weight: 600">事件原文</div>
          <pre data-testid="org-event-payload" style="white-space: pre-wrap">{{ payloadText }}</pre>
        </div>
        <div v-else class="empty" data-testid="org-event-payload-empty">
          <div class="et">这条事件没有原文</div>
          <div class="es">本地队列没有可展开的 payload。</div>
        </div>
      </div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="eventOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
    <ProtoDrawer :open="replayOpen" title="重放失败事件" width="420px" @close="replayOpen = false">
      <div class="sub" style="margin-bottom: 10px">只重放本地失败或死信队列，不调用钉钉。区间不超过 7 天。</div>
      <div class="formrow one">
        <div class="fld"><label>开始</label><input v-model="replayStart" data-testid="org-replay-start" type="datetime-local" /></div>
        <div class="fld"><label>结束</label><input v-model="replayEnd" data-testid="org-replay-end" type="datetime-local" /></div>
      </div>
      <div v-if="replayEmpty" class="empty" data-testid="org-replay-empty">
        <div class="et">该时段没有失败或死信事件</div>
        <div class="es">换一个区间，或等同步失败后再重放。</div>
      </div>
      <p v-if="replayMsg" class="hint">{{ replayMsg }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="replayOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="org-replay-submit" :disabled="!canManage" @click="submitReplay">提交重放</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, readData } from '../../api/read'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const metrics = reactive<{ delayMillis?: number; level?: string; avgSyncDelayMinutes?: number; successRate?: number }>({})
const metricReady = ref(false)
const metricError = ref('')
const users = ref<Record<string, unknown>[]>([])
const userReady = ref(false)
const userError = ref('')
const userTotal = ref(0)
const events = ref<Record<string, unknown>[]>([])
const eventReady = ref(false)
const eventError = ref('')
const total = ref(0)
const msg = ref('')
const confirming = ref(false)
const tab = ref<'users' | 'events'>('users')
const keyword = ref('')
const deptQuery = ref('')
const deptCatalog = ref<Record<string, unknown>[]>([])
const deptReady = ref(false)
const selectedDeptId = ref<number | null>(null)
const deptIdText = ref('')
const invalidDept = ref(false)
const detailOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const eventOpen = ref(false)
const eventDetail = ref<Record<string, unknown> | null>(null)
const canManage = ref(false)
const reportReady = ref(false)
const reportFound = ref(false)
const report = reactive({ diffCount: 0, fixedCount: 0, localUserCount: 0, failures: [] as unknown[], triggeredAt: '' })
const localConfirm = ref(false)
const replayOpen = ref(false)
const replayStart = ref('')
const replayEnd = ref('')
const replayEmpty = ref(false)
const replayMsg = ref('')

const userEmptyTitle = computed(() => {
  if (userError.value) return userError.value
  if (invalidDept.value) return '部门编号须为数字'
  if (deptIdText.value.trim() || selectedDeptId.value) return '该部门没有已同步人员'
  if (keyword.value.trim()) return '没有匹配的人员'
  return '没有已同步人员'
})

const userEmptyHint = computed(() => {
  if (invalidDept.value || deptIdText.value.trim() || selectedDeptId.value) return '只包含这个部门本身，不含下级部门。'
  if (keyword.value.trim()) return '换一个姓名或钉钉用户后再查。'
  return '人员来自验签后的组织事件，列表只展示接口返回的行。'
})

const eventPayload = computed(() => {
  const value = eventDetail.value?.payloadJson
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const row = value as Record<string, unknown>
  return Object.keys(row).length ? row : null
})

const payloadText = computed(() => (eventPayload.value ? JSON.stringify(eventPayload.value, null, 2) : ''))

type DeptNode = { id: number; name: string; count: number }

const deptNodes = computed(() => {
  const map = new Map<number, DeptNode>()
  for (const row of deptCatalog.value) {
    const ids = Array.isArray(row.deptIds) ? row.deptIds.map((item) => Number(item)).filter((id) => id > 0) : []
    const names = Array.isArray(row.deptNames) ? row.deptNames.map((item) => String(item || '')) : []
    ids.forEach((id, index) => {
      const name = names[index] || names.find((item) => item) || `部门 ${id}`
      const prev = map.get(id)
      if (prev) prev.count += 1
      else map.set(id, { id, name, count: 1 })
    })
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh'))
})

const visibleDeptNodes = computed(() => {
  const query = deptQuery.value.trim()
  if (!query) return deptNodes.value
  return deptNodes.value.filter((node) => node.name.includes(query) || String(node.id).includes(query))
})

const diff = computed(() => {
  const value = detail.value?.permissionDiff
  if (!value || typeof value !== 'object') return null
  return value as Record<string, unknown>
})

const holding = computed(() => {
  const value = detail.value?.holdings
  const row = value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
  return {
    accountInUse: Number(row.accountInUse || 0),
    assetInUse: Number(row.assetInUse || 0),
    certActive: Number(row.certActive || 0),
    certRecycled: Number(row.certRecycled || 0),
  }
})

const levelText = computed(() => {
  if (!metricReady.value || metricError.value) return 'GET /auth/org/sync-metrics'
  if (metrics.level === 'red') return '超过 5 分钟，红色'
  if (metrics.level === 'green') return '5 分钟内，绿色'
  return metrics.level || 'GET /auth/org/sync-metrics'
})

function statusText(value: unknown) {
  if (value === 'ENABLED') return '在职'
  if (value === 'FROZEN') return '冻结'
  if (value === 'DISABLED') return '停用'
  return text(value)
}

function text(value: unknown) {
  if (value === undefined || value === null || value === '') return '—'
  return String(value)
}

function names(value: unknown) {
  if (!Array.isArray(value) || !value.length) return '—'
  return value.map((item) => String(item)).join('、')
}

function syncText(row: Record<string, unknown>) {
  if (row.deadLetter) return '死信'
  if (row.retryFlag) return '失败重试'
  if (row.syncStatus === 'SUCCESS') return '成功'
  if (row.syncStatus === 'PENDING') return '待处理'
  if (row.syncStatus === 'FAILED') return '失败'
  return text(row.syncStatus)
}

function eventLabel(value: unknown) {
  const map: Record<string, string> = {
    hire: '入职',
    transfer: '调岗',
    resign: '离职',
    dept_change: '部门变更',
    reconcile: '对账',
  }
  return map[String(value)] || text(value)
}

function timeline(row: Record<string, unknown>) {
  const steps = ['入队']
  const retries = Number(row.retryCount || 0)
  if (retries > 0) steps.push(`重试 ${retries} 次`)
  if (row.deadLetter || row.syncStatus === 'DEAD_LETTER') steps.push('死信')
  else if (row.syncStatus === 'SUCCESS') steps.push('成功')
  else steps.push(syncText(row))
  return steps.join(' → ')
}

function deptChange(row: Record<string, unknown>) {
  const before = text(row.beforeDept)
  const after = text(row.afterDept)
  if (before === '—' && after === '—') return '—'
  return `${before} → ${after}`
}

function percent(value: number) {
  return `${Math.round(value * 1000) / 10}%`
}

async function load() {
  const metricRes = await readData('/auth/org/sync-metrics')
  metricReady.value = true
  metricError.value = metricRes.error
  if (metricRes.data && typeof metricRes.data === 'object') Object.assign(metrics, metricRes.data)

  const deptText = deptIdText.value.trim()
  invalidDept.value = !!deptText && !/^\d+$/.test(deptText)
  const userParams: Record<string, unknown> = { pageNo: 1, pageSize: 20 }
  if (keyword.value.trim()) userParams.keyword = keyword.value.trim()
  if (!invalidDept.value && deptText) userParams.deptId = Number(deptText)
  else if (!deptText && selectedDeptId.value) userParams.deptId = selectedDeptId.value
  const userRes = invalidDept.value
    ? { data: { list: [], total: 0 }, error: '' }
    : await readData('/auth/org/users', userParams)
  userReady.value = true
  userError.value = userRes.error
  users.value = asList(userRes.data)
  userTotal.value = userRes.data && typeof userRes.data === 'object' && typeof (userRes.data as { total?: unknown }).total === 'number'
    ? (userRes.data as { total: number }).total
    : users.value.length

  const eventRes = await readData('/auth/org/events', { pageNo: 1, pageSize: 50 })
  eventReady.value = true
  eventError.value = eventRes.error
  events.value = asList(eventRes.data)
  total.value = eventRes.data && typeof eventRes.data === 'object' && typeof (eventRes.data as { total?: unknown }).total === 'number'
    ? (eventRes.data as { total: number }).total
    : events.value.length

  const reportRes = await readData('/callback/dingtalk/reconcile/report')
  reportReady.value = true
  if (reportRes.error) {
    canManage.value = false
    reportFound.value = false
  } else {
    canManage.value = true
    const data = (reportRes.data && typeof reportRes.data === 'object' ? reportRes.data : {}) as Record<string, unknown>
    reportFound.value = Boolean(data.found)
    report.diffCount = Number(data.diffCount || 0)
    report.fixedCount = Number(data.fixedCount || 0)
    report.localUserCount = Number(data.localUserCount || 0)
    report.failures = Array.isArray(data.failures) ? data.failures : []
    report.triggeredAt = text(data.triggeredAt)
  }
}

async function loadDeptTree() {
  const res = await readData('/auth/org/users', { pageNo: 1, pageSize: 100 })
  deptReady.value = true
  deptCatalog.value = asList(res.data)
}

function searchUsers() {
  userReady.value = false
  load()
}

function clearDept() {
  selectedDeptId.value = null
  deptQuery.value = ''
  searchUsers()
}

function pickDept(id: number) {
  selectedDeptId.value = selectedDeptId.value === id ? null : id
  searchUsers()
}

function openUser(row: Record<string, unknown>) {
  detail.value = row
  detailOpen.value = true
}

function openEvent(row: Record<string, unknown>) {
  eventDetail.value = row
  eventOpen.value = true
}

async function localReconcile() {
  msg.value = ''
  try {
    await http.post('/auth/org/reconcile', {})
    msg.value = '已写入本地对账，未拉取钉钉。'
    localConfirm.value = false
    tab.value = 'events'
    await load()
  } catch (error) {
    msg.value = errorMessage(error)
  }
}

async function submitReplay() {
  replayMsg.value = ''
  replayEmpty.value = false
  try {
    const res = await http.post('/callback/dingtalk/retry-queue/replay', {
      startTime: replayStart.value,
      endTime: replayEnd.value,
    })
    const data = res.data?.data as { replayed?: number } | undefined
    if (!data?.replayed) replayEmpty.value = true
    else replayMsg.value = `已在本地队列重放 ${data.replayed} 条，未调用钉钉。`
    await load()
  } catch (error) {
    replayMsg.value = errorMessage(error)
  }
}

async function reconcile() {
  msg.value = ''
  try {
    const res = await http.post('/auth/org/sync-from-dingtalk', {})
    const d = res.data?.data as {
      departmentsFetched?: number
      usersCreated?: number
      usersUpdated?: number
      usersFailed?: number
    } | undefined
    msg.value = d
      ? `同步完成：部门 ${d.departmentsFetched ?? 0} · 新增 ${d.usersCreated ?? 0} · 更新 ${d.usersUpdated ?? 0}${d.usersFailed ? ` · 失败 ${d.usersFailed}` : ''}`
      : '同步完成'
    confirming.value = false
    tab.value = 'users'
    await Promise.all([load(), loadDeptTree()])
  } catch (error) {
    msg.value = errorMessage(error)
  }
}

onMounted(() => {
  load()
  loadDeptTree()
})
</script>
