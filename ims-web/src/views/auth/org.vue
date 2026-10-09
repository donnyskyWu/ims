<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>组织架构同步</h1>
        <div class="sub">AUTH-002 · 事件验签入队后写入本地用户 · 不写 Football</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="confirming = true">手动对账</button>
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
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'users' }" data-testid="org-tab-users" @click="tab = 'users'">人员列表</div>
      <div class="tab" :class="{ on: tab === 'events' }" data-testid="org-tab-events" @click="tab = 'events'">同步事件</div>
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
      <form class="qbar" style="margin-bottom: 10px" data-testid="org-user-filters" @submit.prevent="searchUsers">
        <input v-model="keyword" data-testid="org-user-keyword" placeholder="姓名 / 钉钉用户" style="width: 180px" />
        <select v-model="userSync" data-testid="org-user-sync" style="width: 140px">
          <option value="">全部同步状态</option>
          <option value="PENDING">待处理</option>
          <option value="SUCCESS">成功</option>
          <option value="FAILED">失败</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="org-user-search">查询</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="org-user-reset" @click="resetUsers">重置</button>
      </form>
      <p class="sub" data-testid="org-user-sync-hint" style="margin: 0 0 8px">失败状态包含失败重试和死信。</p>
      <p v-if="userFilterNote" class="hint" data-testid="org-user-filter-note">{{ userFilterNote }}</p>
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
                  <div class="et">{{ userError || userEmpty }}</div>
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
      <form class="qbar" style="margin-bottom: 10px" data-testid="org-event-filters" @submit.prevent="searchEvents">
        <select v-model="eventType" data-testid="org-event-type" style="width: 140px">
          <option value="">全部类型</option>
          <option value="hire">入职</option>
          <option value="transfer">调岗</option>
          <option value="resign">离职</option>
          <option value="dept_change">部门变更</option>
          <option value="reconcile">对账</option>
        </select>
        <select v-model="eventSync" data-testid="org-event-sync" style="width: 140px">
          <option value="">全部状态</option>
          <option value="PENDING">待处理</option>
          <option value="SUCCESS">成功</option>
          <option value="FAILED_RETRY">失败重试</option>
          <option value="DEAD_LETTER">死信</option>
        </select>
        <input v-model="eventFrom" data-testid="org-event-from" type="date" />
        <input v-model="eventTo" data-testid="org-event-to" type="date" />
        <button class="btn btn-pri btn-sm" type="submit" data-testid="org-event-search">查询</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="org-event-reset" @click="resetEvents">重置</button>
      </form>
      <p v-if="eventHint" class="hint bad" data-testid="org-event-hint">{{ eventHint }}</p>
      <p v-else-if="eventFilterNote" class="hint" data-testid="org-event-filter-note">{{ eventFilterNote }}</p>
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
            </tr>
          </thead>
          <tbody>
            <tr v-if="!eventReady">
              <td colspan="6" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!events.length">
              <td colspan="6" style="white-space: normal">
                <div class="empty" data-testid="org-event-empty">
                  <div class="et">{{ eventError || eventEmpty }}</div>
                  <div class="es">{{ eventEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in events" v-else :key="String(row.id)">
              <td>{{ eventLabel(row.eventType) }}</td>
              <td class="mono">{{ text(row.dingtalkEventId) }}</td>
              <td>{{ deptChange(row) }}</td>
              <td>{{ text(row.syncStatus) }}</td>
              <td class="num">{{ row.retryCount ?? 0 }}</td>
              <td class="mono">{{ text(row.syncedAt) }}</td>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal, readData } from '../../api/read'
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
const userSync = ref('')
const appliedKeyword = ref('')
const appliedSync = ref('')
const appliedDeptId = ref<number | null>(null)
const eventType = ref('')
const eventSync = ref('')
const eventFrom = ref('')
const eventTo = ref('')
const appliedEventType = ref('')
const appliedEventSync = ref('')
const appliedEventFrom = ref('')
const appliedEventTo = ref('')
const eventHint = ref('')
const deptQuery = ref('')
const deptCatalog = ref<Record<string, unknown>[]>([])
const deptReady = ref(false)
const selectedDeptId = ref<number | null>(null)
const detailOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)

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

const userFilterNote = computed(() => {
  const bits: string[] = []
  if (appliedDeptId.value) bits.push('当前部门')
  if (appliedKeyword.value) bits.push(`姓名「${appliedKeyword.value}」`)
  if (appliedSync.value) bits.push(`同步状态「${syncOptionLabel(appliedSync.value)}」`)
  if (!bits.length) return ''
  return `人员列表按${bits.join('、')}筛选。`
})

const userEmpty = computed(() => {
  if (appliedDeptId.value && !appliedKeyword.value && !appliedSync.value) return '该部门下没有已同步人员'
  if (appliedSync.value && !appliedKeyword.value && !appliedDeptId.value) return '没有该同步状态的人员'
  if (appliedKeyword.value || appliedSync.value || appliedDeptId.value) return '没有匹配的人员'
  return '没有已同步人员'
})

const userEmptyHint = computed(() => {
  if (appliedKeyword.value || appliedSync.value || appliedDeptId.value) return '换姓名、部门或同步状态后再查。'
  return '人员来自验签后的组织事件，列表只展示接口返回的行。'
})

const eventFilterNote = computed(() => {
  const bits: string[] = []
  if (appliedEventType.value) bits.push(`类型「${eventLabel(appliedEventType.value)}」`)
  if (appliedEventSync.value) bits.push(`状态「${eventSyncLabel(appliedEventSync.value)}」`)
  if (appliedEventFrom.value && appliedEventTo.value) bits.push(`${appliedEventFrom.value} 至 ${appliedEventTo.value}`)
  if (!bits.length) return ''
  return `同步事件按${bits.join('、')}筛选。`
})

const eventEmpty = computed(() => {
  if (appliedEventType.value || appliedEventSync.value || appliedEventFrom.value || appliedEventTo.value) return '没有符合条件的同步事件'
  return '没有同步事件'
})

const eventEmptyHint = computed(() => {
  if (appliedEventType.value || appliedEventSync.value || appliedEventFrom.value || appliedEventTo.value) return '换事件类型、状态或日期区间后再查。'
  return '对账成功后，这里会出现对账记录。'
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

function syncOptionLabel(value: string) {
  return { PENDING: '待处理', SUCCESS: '成功', FAILED: '失败' }[value] || value
}

function eventSyncLabel(value: string) {
  return { PENDING: '待处理', SUCCESS: '成功', FAILED_RETRY: '失败重试', DEAD_LETTER: '死信' }[value] || value
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

function captureUserFilters() {
  appliedKeyword.value = keyword.value.trim()
  appliedSync.value = userSync.value
  appliedDeptId.value = selectedDeptId.value
}

function captureEventFilters() {
  appliedEventType.value = eventType.value
  appliedEventSync.value = eventSync.value
  appliedEventFrom.value = eventFrom.value
  appliedEventTo.value = eventTo.value
}

async function load() {
  captureUserFilters()
  const metricRes = await readData('/auth/org/sync-metrics')
  metricReady.value = true
  metricError.value = metricRes.error
  if (metricRes.data && typeof metricRes.data === 'object') Object.assign(metrics, metricRes.data)

  const userParams: Record<string, unknown> = { pageNo: 1, pageSize: 20 }
  if (keyword.value.trim()) userParams.keyword = keyword.value.trim()
  if (selectedDeptId.value) userParams.deptId = selectedDeptId.value
  if (userSync.value) userParams.syncStatus = userSync.value
  const userRes = await readData('/auth/org/users', userParams)
  userReady.value = true
  userError.value = userRes.error
  users.value = asList(userRes.data)
  userTotal.value = asTotal(userRes.data, users.value.length)
  await loadEvents()
}

async function loadEvents() {
  captureEventFilters()
  const params: Record<string, unknown> = { pageNo: 1, pageSize: 10 }
  if (eventType.value) params.eventType = eventType.value
  if (eventSync.value) params.syncStatus = eventSync.value
  if (eventFrom.value && eventTo.value) {
    params.timeRange = [`${eventFrom.value} 00:00:00`, `${eventTo.value} 23:59:59`]
  }
  try {
    const res = await http.get('/auth/org/events', {
      params,
      paramsSerializer: { indexes: null },
    })
    const data = res.data?.data
    eventError.value = ''
    events.value = asList(data)
    total.value = asTotal(data, events.value.length)
  } catch (error) {
    eventError.value = errorMessage(error)
    events.value = []
    total.value = 0
  } finally {
    eventReady.value = true
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

function resetUsers() {
  keyword.value = ''
  userSync.value = ''
  selectedDeptId.value = null
  deptQuery.value = ''
  searchUsers()
}

function searchEvents() {
  eventHint.value = ''
  const from = eventFrom.value
  const to = eventTo.value
  if ((from && !to) || (!from && to)) {
    eventHint.value = '请同时填写开始和结束日期'
    return
  }
  if (from && to && from > to) {
    eventHint.value = '结束日期不能早于开始日期'
    return
  }
  eventReady.value = false
  loadEvents()
}

function resetEvents() {
  eventType.value = ''
  eventSync.value = ''
  eventFrom.value = ''
  eventTo.value = ''
  eventHint.value = ''
  eventReady.value = false
  loadEvents()
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
