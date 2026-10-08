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
      <div class="tab" :class="{ on: tab === 'users' }" @click="tab = 'users'">人员列表</div>
      <div class="tab" :class="{ on: tab === 'events' }" @click="tab = 'events'">同步事件</div>
    </div>
    <div v-if="tab === 'users'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>姓名</th>
              <th>手机</th>
              <th>部门</th>
              <th>钉钉</th>
              <th>同步状态</th>
              <th>账号状态</th>
              <th>最近同步</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!userReady">
              <td colspan="7" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!users.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ userError || '没有已同步人员' }}</div>
                  <div class="es">人员来自验签后的组织事件，列表只展示接口返回的行。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in users" v-else :key="String(row.userId)">
              <td style="font-weight: 500">{{ text(row.nickname) }}</td>
              <td class="masked">{{ text(row.mobileMasked) }}</td>
              <td>{{ names(row.deptNames) }}</td>
              <td class="mono">{{ text(row.dingtalkUserId) }}</td>
              <td>{{ syncText(row) }}</td>
              <td>{{ text(row.status) }}</td>
              <td class="mono">{{ text(row.lastSyncTime) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ userTotal }} 条</span></div>
    </div>
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
            </tr>
          </thead>
          <tbody>
            <tr v-if="!eventReady">
              <td colspan="6" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!events.length">
              <td colspan="6" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ eventError || '没有同步事件' }}</div>
                  <div class="es">对账成功后，这里会出现对账记录。</div>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, readData } from '../../api/read'

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

const levelText = computed(() => {
  if (!metricReady.value || metricError.value) return 'GET /auth/org/sync-metrics'
  if (metrics.level === 'red') return '超过 5 分钟，红色'
  if (metrics.level === 'green') return '5 分钟内，绿色'
  return metrics.level || 'GET /auth/org/sync-metrics'
})

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

  const userRes = await readData('/auth/org/users', { pageNo: 1, pageSize: 10 })
  userReady.value = true
  userError.value = userRes.error
  users.value = asList(userRes.data)
  userTotal.value = userRes.data && typeof userRes.data === 'object' && typeof (userRes.data as { total?: unknown }).total === 'number'
    ? (userRes.data as { total: number }).total
    : users.value.length

  const eventRes = await readData('/auth/org/events', { pageNo: 1, pageSize: 10 })
  eventReady.value = true
  eventError.value = eventRes.error
  events.value = asList(eventRes.data)
  total.value = eventRes.data && typeof eventRes.data === 'object' && typeof (eventRes.data as { total?: unknown }).total === 'number'
    ? (eventRes.data as { total: number }).total
    : events.value.length
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
    await load()
  } catch (error) {
    msg.value = errorMessage(error)
  }
}

onMounted(load)
</script>
