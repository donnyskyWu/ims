<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>运营仪表盘</h1>
        <div class="sub">IP 组筛选、核心指标、待办与快捷入口（HOME-001）</div>
      </div>
      <div class="acts">
        <select v-model="ipGroupId" data-testid="home-ip-filter" style="width: 160px" @change="loadDashboard">
          <option value="">全部 IP 组</option>
          <option v-for="group in ipGroups" :key="group.id" :value="String(group.id)">{{ group.label }}</option>
        </select>
        <select v-model="rangeDays" data-testid="home-range" style="width: 110px">
          <option :value="7">近 7 天</option>
          <option :value="30">近 30 天</option>
        </select>
        <input v-model="dateFrom" data-testid="home-date-from" type="date" aria-label="开始日期" />
        <input v-model="dateTo" data-testid="home-date-to" type="date" aria-label="结束日期" />
        <button class="btn btn-pri btn-sm" type="button" @click="loadDashboard">刷新</button>
      </div>
    </div>
    <p v-if="ipReady && !ipGroups.length" class="hint" data-testid="home-ip-empty">没有可筛选的 IP 组。筛选器只保留全部。</p>
    <div v-if="dashBlocked" class="card" data-testid="home-dash-error">
      <div class="empty">
        <div class="et">{{ error }}</div>
        <div class="es">{{ errorHint }}</div>
      </div>
    </div>
    <div v-if="!dashBlocked" class="g4">
      <div v-if="dashReady && !kpis.length" class="card" data-testid="home-kpi-empty">
        <div class="empty">
          <div class="et">{{ error || '暂无指标' }}</div>
          <div class="es">当前筛选下没有可展示的指标卡片</div>
        </div>
      </div>
      <div
        v-for="kpi in kpis"
        :key="kpi.key"
        class="card stat hov"
        @click="onKpiClick(kpi.key)"
      >
        <span class="l">{{ kpi.label }}</span>
        <div class="n">{{ kpi.value }}</div>
        <div v-if="kpi.wow" class="d">{{ kpi.wow }}</div>
      </div>
    </div>
    <div v-if="!dashBlocked" class="g2" style="margin-top: 16px">
      <div class="card">
        <div class="hd-row">
          <h3>播放 / 互动</h3>
          <span class="csub">占位趋势 · 不请求 Football</span>
        </div>
        <div v-if="dashReady && !trend.length" class="empty" data-testid="home-trend-empty">
          <div class="et">暂无播放趋势</div>
        </div>
        <div v-else class="bars">
          <div
            v-for="(pt, idx) in trend"
            :key="idx"
            class="b"
            :style="{ height: `${Math.min(90, pt.play)}%` }"
          />
        </div>
      </div>
      <div class="card">
        <div class="hd-row">
          <h3>待办聚合</h3>
          <span class="csub">不请求 OPS</span>
        </div>
        <div v-if="!dashReady" class="empty"><div class="et">加载中</div></div>
        <div v-else-if="!todos.length" class="empty" data-testid="home-todo-empty"><div class="et">暂无待办</div></div>
        <div
          v-for="(row, idx) in todos"
          v-else
          :key="idx"
          class="mg-i"
          style="border-radius: 8px; cursor: pointer"
          @click="go(row.url)"
        >
          <div>
            <div class="mt">{{ row.title }}</div>
            <div class="md">{{ todoTypeLabel(row.type) }}</div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!dashBlocked" class="sec">快捷入口</div>
    <div v-if="!dashBlocked && dashReady && !shortcuts.length" class="card" data-testid="home-shortcut-empty">
      <div class="empty">
        <div class="et">暂无可用快捷入口</div>
        <div class="es">当前账号没有可打开的快捷入口</div>
      </div>
    </div>
    <div v-else-if="!dashBlocked && shortcuts.length" style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px">
      <div
        v-for="sc in shortcuts"
        :key="sc.code"
        class="card hov"
        style="padding: 13px 8px; text-align: center; box-shadow: none; border: 1px solid var(--line); cursor: pointer"
        @click="go(sc.route)"
      >
        <div style="font-size: 12px; font-weight: 500">{{ sc.name }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

const router = useRouter()
const kpis = ref<{ key: string; label: string; value: string; wow?: string }[]>([])
const todos = ref<{ type: string; title: string; bizId: string; url: string }[]>([])
const shortcuts = ref<{ code: string; name: string; route: string }[]>([])
const trend = ref<{ label: string; play: number; engage: number }[]>([])
const error = ref('')
const errorCode = ref(0)
const dashBlocked = ref(false)
const dashReady = ref(false)
const ipReady = ref(false)
const ipGroupId = ref('')
const ipGroups = ref<{ id: number; label: string }[]>([])
const rangeDays = ref(7)
const dateFrom = ref('')
const dateTo = ref('')

const todoTypeNames: Record<string, string> = {
  CONTENT_REVIEW: '内容审核',
  COLLECT_FAIL: '采集失败',
  ALERT: '预警',
  WORK_TASK: '工作任务',
  WORK_TASK_CONFIRM: '工作任务确认',
  ACCT_RETURN: '账号归还',
}

const errorHint = computed(() => {
  if (errorCode.value === 1202 || error.value.includes('90')) return '请把开始和结束日期收在 90 天以内。'
  if (errorCode.value === 1201) return '这个 IP 组不在你的权限范围内。筛选器只列出可访问的组。'
  if (error.value === '结束日期不能早于开始日期') return '对调两个日期后再刷新。'
  if (error.value === '请同时填写开始和结束日期') return '只填了一边时不会按自定义日期查询。'
  return '刷新后再看。'
})

function todoTypeLabel(value: string) {
  return todoTypeNames[value] || value || '待办'
}

function clearDash() {
  kpis.value = []
  todos.value = []
  shortcuts.value = []
  trend.value = []
}

function applyDashError(code: number, message: string) {
  errorCode.value = code
  error.value = message || '加载失败'
  dashBlocked.value = true
  clearDash()
}

type IpNode = { id: number; groupName?: string; children?: IpNode[] }

function flattenGroups(nodes: IpNode[], depth = 0): { id: number; label: string }[] {
  const out: { id: number; label: string }[] = []
  for (const node of nodes) {
    const name = node.groupName || `IP 组 ${node.id}`
    out.push({ id: node.id, label: `${'　'.repeat(depth)}${name}` })
    if (node.children?.length) out.push(...flattenGroups(node.children, depth + 1))
  }
  return out
}

async function loadIpGroups() {
  try {
    const res = await http.get('/ip-group/accessible-tree')
    const data = res.data.data
    ipGroups.value = flattenGroups(Array.isArray(data) ? data : [])
  } catch {
    ipGroups.value = []
  } finally {
    ipReady.value = true
  }
}

function dateProblem() {
  const from = dateFrom.value
  const to = dateTo.value
  if (!from && !to) return ''
  if (!from || !to) return '请同时填写开始和结束日期'
  if (from > to) return '结束日期不能早于开始日期'
  return ''
}

function dateParams() {
  if (dateFrom.value && dateTo.value) {
    return { dateFrom: dateFrom.value, dateTo: dateTo.value }
  }
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - Number(rangeDays.value))
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { dateFrom: fmt(start), dateTo: fmt(end) }
}

async function loadDashboard() {
  error.value = ''
  errorCode.value = 0
  const problem = dateProblem()
  if (problem) {
    applyDashError(0, problem)
    dashReady.value = true
    return
  }
  try {
    const params: Record<string, string | number> = { ...dateParams() }
    if (ipGroupId.value) params.ipGroupId = Number(ipGroupId.value)
    const res = await http.get('/home/dashboard', { params })
    if (res.data.code !== 0) {
      applyDashError(Number(res.data.code) || 0, res.data.msg || '加载失败')
      return
    }
    const data = res.data.data
    dashBlocked.value = false
    kpis.value = data.kpis || []
    todos.value = data.todos || []
    shortcuts.value = data.shortcuts || []
    trend.value = data.trendPlayEngage || []
  } catch (e: unknown) {
    const code = e && typeof e === 'object' && 'code' in e ? Number((e as { code?: number }).code) || 0 : 0
    applyDashError(code, errorMessage(e))
  } finally {
    dashReady.value = true
  }
}

function go(path: string) {
  router.push(path)
}

function onKpiClick(key: string) {
  const map: Record<string, string> = {
    accounts: '/ims/corp/account/douyin',
    worksToday: '/ims/collect/log',
    pendingTodos: '/ims/workbench',
    collectAlert: '/ims/collect/log',
  }
  if (map[key]) go(map[key])
}

onMounted(async () => {
  await loadIpGroups()
  await loadDashboard()
})
</script>
