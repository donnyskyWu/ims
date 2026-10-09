<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>升级中心</h1>
        <div class="sub">ALERT-003 · 待升级清单 30 秒轮询 · 倒计时每分钟刷新</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="alert-escalate-refresh" @click="refreshAll">
          手动刷新
        </button>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/stats">统计总览</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <p class="hint" data-testid="alert-escalate-channel-stub">钉钉/短信外发保持本地桩，不实际发送</p>
    <p class="hint" data-testid="alert-escalate-poll-state">{{ pollState }}</p>
    <p v-if="pollHint" class="hint" data-testid="alert-escalate-poll-hint" style="color: var(--orange, #d97706)">
      {{ pollHint }}
    </p>
    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div v-if="stats" class="g4" style="margin-top: 12px">
      <div class="card stat">
        <span class="l">响应率</span>
        <div class="n" data-testid="alert-escalate-response-rate" :style="{ color: rateColor(stats.responseRate) }">
          {{ stats.responseRate }}%
        </div>
        <div class="d">{{ stats.responseRate >= stats.target ? '达标' : '未达标' }}（BR-112 &gt;{{ stats.target }}%）</div>
      </div>
      <div class="card stat">
        <span class="l">平均响应</span>
        <div class="n" data-testid="alert-escalate-avg">{{ stats.avgResponseMinutes }}</div>
        <div class="d">分钟 · 时限内 {{ stats.respondedInTime }} 条</div>
      </div>
      <div class="card stat">
        <span class="l">分级别</span>
        <div class="n" style="font-size: 16px; margin-top: 10px" data-testid="alert-escalate-by-level">
          <span v-for="item in stats.byLevel" :key="item.level" :style="{ color: levelColor(item) }">
            {{ item.level }} {{ item.alertCount ? item.responseRate + '%' : '—' }}
          </span>
        </div>
      </div>
    </div>

    <h2 style="font-size: 16px; margin: 16px 0 8px">待升级 / 升级中预警</h2>
    <form class="qbar" @submit.prevent="refreshPending(false)">
      <select v-model="currentLevel" data-testid="alert-escalate-level" style="width: 140px" @change="refreshPending(false)">
        <option value="">全部级别</option>
        <option value="1">一级</option>
        <option value="2">二级</option>
        <option value="3">三级</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">搜索</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>预警编号</th>
              <th>级别</th>
              <th>规则</th>
              <th>当前升级级别</th>
              <th>下一级升级于</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无升级中预警' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.alertNo" data-testid="alert-escalate-row">
              <td class="mono">{{ row.alertNo }}</td>
              <td class="num">L{{ row.level }}</td>
              <td>
                <div class="mono">{{ row.ruleCode }}</div>
                <div>{{ row.ruleName }}</div>
              </td>
              <td>{{ levelText(row.currentLevel) }}</td>
              <td class="mono" data-testid="alert-escalate-next">{{ nextText(row) }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-escalate-detail" @click="openTimeline(row.alertNo)">
                  详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <h2 style="font-size: 16px; margin: 16px 0 8px">响应率趋势</h2>
    <div v-if="!trend.length" class="empty"><div class="et">暂无趋势</div></div>
    <div v-else data-testid="alert-escalate-trend">
      <div v-for="point in trend" :key="point.statDate" class="trend-row">
        <span class="mono">{{ point.statDate }}</span>
        <div class="trend-track">
          <div class="trend-bar" :style="{ width: point.responseRate + '%' }"></div>
          <div class="trend-target"></div>
        </div>
        <span class="num">{{ point.responseRate }}% · {{ point.alertCount }} 条</span>
      </div>
      <p class="hint">虚线为目标 90%（BR-112）</p>
    </div>

    <div v-if="timeline" class="drawer-mask" @click.self="timeline = null">
      <div class="drawer on" data-testid="alert-escalate-timeline">
        <div class="drawer-h">
          <b>{{ timeline.alertNo }} · {{ timeline.alertLevel }}</b>
          <button class="btn btn-sec btn-sm" type="button" @click="timeline = null">关闭</button>
        </div>
        <div class="drawer-b">
          <p class="hint">{{ timeline.channelStub }}</p>
          <p v-if="timeline.responseStatus !== 'OPEN'" data-testid="alert-escalate-stopped">
            已响应 · 升级链停止（ALR-E-R3）· {{ timeline.responseStatus }}
          </p>
          <ol class="tl">
            <li v-for="node in timeline.timeline" :key="node.escalationLevel + '-' + node.elapsedMinutes" :class="{ skip: node.skipped }">
              <div>{{ levelText(node.escalationLevel) }} · 距产生 {{ node.elapsedMinutes }} 分钟</div>
              <div v-if="node.skipped" class="hint">{{ node.note }}</div>
              <div v-else class="hint">
                <span v-for="person in node.escalatedTo" :key="person.roleLabel">
                  {{ person.userName }}（{{ person.roleLabel }}）
                </span>
              </div>
            </li>
          </ol>
          <p v-if="timeline.responseStatus === 'OPEN' && timeline.nextEscalateAt" class="hint">
            下一级升级于 {{ timeline.nextEscalateAt.slice(11, 16) }}
          </p>
          <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">查看预警详情</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Pending = {
  alertNo: string
  level: number
  ruleCode: string
  ruleName: string
  currentLevel: 1 | 2 | 3
  nextEscalateAt: string
}

type Stats = {
  responseRate: number
  avgResponseMinutes: number
  respondedInTime: number
  target: number
  byLevel: Array<{ level: string; responseRate: number; alertCount: number }>
}

type Trend = { statDate: string; responseRate: number; alertCount: number }

type Timeline = {
  alertNo: string
  alertLevel: string
  responseStatus: string
  nextEscalateAt: string
  channelStub: string
  timeline: Array<{
    escalationLevel: number
    elapsedMinutes: number
    skipped: boolean
    note: string
    escalatedTo: Array<{ userName: string; roleLabel: string }>
  }>
}

const POLL_MS = 30_000
const CLOCK_MS = 60_000

const route = useRoute()
const rows = ref<Pending[]>([])
const total = ref(0)
const stats = ref<Stats | null>(null)
const trend = ref<Trend[]>([])
const timeline = ref<Timeline | null>(null)
const error = ref('')
const pollHint = ref('')
const failStreak = ref(0)
const currentLevel = ref('')
const tick = ref(0)
let pollTimer = 0
let clockTimer = 0

const imminent = computed(() => rows.value.some((row) => row.currentLevel < 3 && !!row.nextEscalateAt))
const pollState = computed(() => (imminent.value ? '30 秒轮询中' : '无临近升级，已暂停轮询'))

function rateColor(value: number) {
  return value >= 90 ? 'var(--green, #15803d)' : 'var(--orange, #d97706)'
}

function levelColor(item: { responseRate: number; alertCount: number }) {
  if (!item.alertCount || item.responseRate >= 90) return undefined
  return 'var(--orange, #d97706)'
}

function levelText(level: number) {
  if (level === 1) return '一级（责任人）'
  if (level === 2) return '二级（部门负责人）'
  if (level === 3) return '三级（R4+R1）'
  return '—'
}

function nextText(row: Pending) {
  tick.value
  if (row.currentLevel >= 3 || !row.nextEscalateAt) return '终级等待响应'
  const target = new Date(row.nextEscalateAt).getTime()
  const mins = Math.max(0, Math.ceil((target - Date.now()) / 60000))
  const hhmm = row.nextEscalateAt.slice(11, 16)
  const next = row.currentLevel === 1 ? '二级' : '三级'
  return `${hhmm}（再 ${mins} min → ${next}）`
}

function pendingParams() {
  const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
  if (currentLevel.value) params.currentLevel = Number(currentLevel.value)
  return params
}

async function refreshPending(silent: boolean) {
  try {
    const res = await http.get('/alert/escalate/pending', { params: pendingParams() })
    rows.value = res.data.data?.list || []
    total.value = res.data.data?.total || 0
    failStreak.value = 0
    pollHint.value = ''
    if (!silent) error.value = ''
  } catch (err) {
    if (!silent) {
      error.value = errorMessage(err)
      rows.value = []
      total.value = 0
      return
    }
    failStreak.value += 1
    if (failStreak.value >= 3) pollHint.value = '连续刷新失败，请手动刷新'
  }
}

async function loadStats() {
  const [statsRes, trendRes] = await Promise.all([
    http.get('/alert/escalate/response-stats'),
    http.get('/alert/stats/response-rate'),
  ])
  stats.value = statsRes.data.data
  trend.value = trendRes.data.data || []
}

async function openTimeline(alertNo: string) {
  error.value = ''
  try {
    const res = await http.get(`/alert/escalate/timeline/${alertNo}`)
    timeline.value = res.data.data
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function refreshAll() {
  await refreshPending(false)
  try {
    await loadStats()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

watch(imminent, (active) => {
  window.clearInterval(pollTimer)
  pollTimer = 0
  if (!active) return
  pollTimer = window.setInterval(() => {
    void refreshPending(true)
  }, POLL_MS)
})

onMounted(async () => {
  clockTimer = window.setInterval(() => {
    tick.value += 1
  }, CLOCK_MS)
  await refreshAll()
  const alertNo = String(route.query.alertNo || '')
  if (alertNo) await openTimeline(alertNo)
})

onUnmounted(() => {
  window.clearInterval(pollTimer)
  window.clearInterval(clockTimer)
})
</script>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
}
.drawer.on {
  z-index: 1001;
}
.tl {
  margin: 12px 0;
  padding-left: 18px;
}
.tl li.skip {
  color: var(--text2, #6b7280);
}
.trend-row {
  display: grid;
  grid-template-columns: 110px 1fr 140px;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}
.trend-track {
  position: relative;
  height: 10px;
  background: #f3f4f6;
  border-radius: 6px;
}
.trend-bar {
  height: 10px;
  background: #2563eb;
  border-radius: 6px;
}
.trend-target {
  position: absolute;
  left: 90%;
  top: -3px;
  width: 0;
  height: 16px;
  border-left: 1px dashed #d97706;
}
</style>
