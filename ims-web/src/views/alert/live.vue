<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>实时预警</h1>
        <div class="sub">ALERT-002/003/004 · 实时 · 处置记录 · 去重</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
    </div>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'live' }" @click="switchTab('live')">实时预警</div>
      <div class="tab" :class="{ on: tab === 'history' }" @click="switchTab('history')">处置记录</div>
      <div class="tab" :class="{ on: tab === 'dedup' }" @click="switchTab('dedup')">去重合并</div>
    </div>

    <div v-if="tab === 'history' && summary" class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">累计</span><div class="n">{{ summary.totalAlerts }}</div></div>
      <div class="card stat"><span class="l">已处置</span><div class="n">{{ summary.handledCount }}</div></div>
      <div class="card stat"><span class="l">待响应</span><div class="n">{{ summary.openCount }}</div></div>
      <div class="card stat"><span class="l">误报</span><div class="n">{{ summary.falsePositiveCount }}</div></div>
    </div>

    <form v-if="tab !== 'dedup'" class="qbar" @submit.prevent="loadList">
      <select v-model="filters.responseStatus" style="width: 120px">
        <option value="">全部处置</option>
        <option value="OPEN">待响应</option>
        <option value="ACK">已确认</option>
        <option value="HANDLED">已处理</option>
        <option value="FALSE_ALARM">误报</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
    </form>

    <div v-if="tab === 'dedup'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>策略编码</th>
              <th>名称</th>
              <th>窗口(分)</th>
              <th>合并键</th>
              <th>已合并</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in dedupRows" v-else :key="row.id">
              <td class="mono">{{ row.policyCode }}</td>
              <td>{{ row.policyName }}</td>
              <td class="num">{{ row.windowMinutes }}</td>
              <td class="mono">{{ row.mergeKeyExpr }}</td>
              <td class="num">{{ row.mergedCount }}</td>
              <td>{{ row.enabled ? '启用' : '停用' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>预警编号</th>
              <th>规则</th>
              <th>级别</th>
              <th>内容</th>
              <th>状态</th>
              <th>时间</th>
              <th v-if="tab === 'live'">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="tab === 'live' ? 7 : 6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td :colspan="tab === 'live' ? 7 : 6"><div class="empty"><div class="et">{{ error || '暂无预警' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.alertNo }}</td>
              <td>{{ row.ruleName }}</td>
              <td class="num">L{{ row.level }}</td>
              <td>{{ row.content }}</td>
              <td>{{ row.responseStatus }}</td>
              <td class="mono">{{ row.occurredAt?.slice(0, 16) || '—' }}</td>
              <td v-if="tab === 'live'">
                <button
                  v-if="row.responseStatus === 'OPEN'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="respond(row.alertNo, 'ACK')"
                >
                  确认
                </button>
                <button
                  v-if="row.responseStatus === 'OPEN'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  @click="respond(row.alertNo, 'HANDLE')"
                >
                  处理
                </button>
                <button
                  v-if="row.responseStatus === 'OPEN' || row.responseStatus === 'ACK' || row.responseStatus === 'FALSE_ALARM'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="alert-false-alarm-btn"
                  @click="respond(row.alertNo, 'FALSE_ALARM')"
                >
                  误报
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="toast" class="hint" style="margin-top: 10px">{{ toast }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Row = {
  id: number
  alertNo: string
  ruleName: string
  level: number
  content: string
  responseStatus: string
  occurredAt: string
}

type DedupRow = {
  id: number
  policyCode: string
  policyName: string
  windowMinutes: number
  mergeKeyExpr: string
  mergedCount: number
  enabled: boolean
}

const route = useRoute()
const router = useRouter()
const tab = ref<'live' | 'history' | 'dedup'>('live')
const rows = ref<Row[]>([])
const dedupRows = ref<DedupRow[]>([])
const loading = ref(false)
const error = ref('')
const summary = ref<{ totalAlerts: number; handledCount: number; openCount: number; falsePositiveCount: number } | null>(
  null
)
const filters = reactive({ responseStatus: '' })
const toast = ref('')

function tabFromRoute() {
  const q = String(route.query.tab || '')
  if (q === 'history' || q === 'dedup') return q
  return 'live'
}

function switchTab(name: 'live' | 'history' | 'dedup') {
  tab.value = name
  router.replace({ path: '/ims/alert/live', query: name === 'live' ? {} : { tab: name } })
  if (name === 'dedup') loadDedup()
  else {
    if (name === 'history') {
      filters.responseStatus = ''
      loadSummary()
    }
    loadList()
  }
}

async function loadSummary() {
  const res = await http.get('/alert/history/summary')
  if (res.data.code === 0) summary.value = res.data.data
}

async function loadDedup() {
  loading.value = true
  try {
    const res = await http.get('/alert/dedup/list', { params: { pageNo: 1, pageSize: 20 } })
    if (res.data.code === 0) dedupRows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.responseStatus) params.responseStatus = filters.responseStatus
    const res = await http.get('/alert/check/records', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    let list: Row[] = res.data.data?.list || []
    if (tab.value === 'history' && !filters.responseStatus) {
      list = list.filter((r) => r.responseStatus !== 'OPEN')
    }
    rows.value = list
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function respond(alertNo: string, action: string) {
  toast.value = ''
  try {
    const res = await http.put(`/alert/check/${alertNo}/respond`, { action })
    if (res.data.code !== 0) {
      toast.value = res.data.msg || '处置失败'
      return
    }
    const status = res.data.data?.responseStatus || ''
    const labels: Record<string, string> = {
      ACK: '已确认',
      HANDLED: '已处理',
      FALSE_ALARM: '已标记误报',
      FALSE_POSITIVE: '已标记误报',
    }
    toast.value = `处置成功：${labels[status] || status}（${alertNo}）`
    if (tab.value === 'history') await loadSummary()
    await loadList()
  } catch (error) {
    const body = error as { msg?: string }
    toast.value = body?.msg || errorMessage(error)
  }
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(() => {
  tab.value = tabFromRoute()
  if (tab.value === 'dedup') loadDedup()
  else {
    if (tab.value === 'history') loadSummary()
    loadList()
  }
})
</script>
