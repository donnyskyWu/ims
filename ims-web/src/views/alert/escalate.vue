<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>升级中心</h1>
        <div class="sub">ALERT-003 · 一级 30 分钟 / 二级 60 分钟 · L3 从二级起跳 · 待升级清单 30 秒轮询</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="alert-escalate-refresh" @click="refreshAll">
          手动刷新
        </button>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/stats">统计总览</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
      </div>
    </div>

    <p class="hint" data-testid="alert-escalate-channel-stub">钉钉/短信外发保持本地桩，不实际发送</p>
    <p class="hint" data-testid="alert-escalate-poll-state">{{ pollState }}</p>
    <p v-if="pollHint" class="hint" data-testid="alert-escalate-poll-hint" style="color: var(--orange, #d97706)">
      {{ pollHint }}
    </p>

    <div class="card" style="margin-bottom: 12px">
      <h3 style="margin: 0 0 12px">升级链路配置</h3>
      <form class="qbar" novalidate @submit.prevent="saveConfig">
        <label>
          一级（分钟）
          <input
            v-model.number="form.level1TimeoutMinutes"
            data-testid="alert-escalate-l1"
            type="number"
            min="0"
            max="10080"
            style="width: 88px"
          />
        </label>
        <label>
          二级（分钟）
          <input
            v-model.number="form.level2TimeoutMinutes"
            data-testid="alert-escalate-l2"
            type="number"
            min="0"
            max="10080"
            style="width: 88px"
          />
        </label>
        <label>
          严重级起跳
          <select v-model.number="form.severeStartLevel" data-testid="alert-escalate-severe" style="width: 120px">
            <option :value="2">二级</option>
            <option :value="3">三级</option>
          </select>
        </label>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="alert-escalate-save">保存</button>
      </form>
      <p class="hint">一级责任人 → 二级部门负责人 → 三级运营总监与系统管理员。到点写入站内通知，钉钉不外发。</p>
      <p v-if="savedHint" class="hint" data-testid="alert-escalate-saved">{{ savedHint }}</p>
      <p v-if="formError" class="hint" style="color: var(--red)" data-testid="alert-escalate-form-error">{{ formError }}</p>
    </div>

    <form class="qbar" data-testid="alert-escalate-stats-filter" @submit.prevent="loadStats">
      <input v-model="statsFrom" data-testid="alert-escalate-stats-from" type="date" />
      <input v-model="statsTo" data-testid="alert-escalate-stats-to" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="alert-escalate-stats-apply">刷新统计</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="alert-escalate-stats-reset" @click="resetStatsRange">
        重置
      </button>
    </form>
    <p v-if="statsError" class="hint" style="color: var(--red)" data-testid="alert-escalate-stats-error">{{ statsError }}</p>

    <div v-if="stats" class="g4" style="margin-top: 12px">
      <div class="card stat">
        <span class="l">响应率</span>
        <div class="n" data-testid="alert-escalate-response-rate" :style="{ color: rateColor(stats.responseRate) }">
          {{ stats.responseRate }}%
        </div>
        <div class="d" data-testid="alert-escalate-rate-hint">{{ rateHint }}</div>
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
      <select v-model="levelFilter" data-testid="alert-escalate-level" style="width: 140px" @change="refreshPending(false)">
        <option value="">全部级别</option>
        <option value="1">一级</option>
        <option value="2">二级</option>
        <option value="3">三级</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="alert-escalate-level-reset" @click="resetLevel">
        重置
      </button>
    </form>

    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>预警编号</th>
              <th>规则</th>
              <th>级别</th>
              <th>当前升级级别</th>
              <th>下一级升级于</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr>
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
          </tbody>
          <tbody v-else-if="!rows.length">
            <tr>
              <td colspan="6">
                <div class="empty" data-testid="alert-escalate-empty">
                  <div class="et">{{ levelFilter ? '当前级别暂无待升级预警' : '暂无待升级预警' }}</div>
                </div>
              </td>
            </tr>
          </tbody>
          <tbody v-for="row in rows" v-else :key="row.alertNo" :data-testid="`alert-escalate-row-${row.alertNo}`">
            <tr data-testid="alert-escalate-row">
              <td class="mono">{{ row.alertNo }}</td>
              <td>
                <div class="mono">{{ row.ruleCode }}</div>
                <div>{{ row.ruleName }}</div>
              </td>
              <td>{{ row.level }}</td>
              <td data-testid="alert-escalate-current">{{ levelName(row.currentLevel) }}</td>
              <td class="mono" data-testid="alert-escalate-next">{{ nextText(row) }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-escalate-timeline" @click="openTimeline(row.alertNo)">
                  时间轴
                </button>
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-escalate-detail" @click="openTimeline(row.alertNo)">
                  详情
                </button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="alert-escalate-confirm" @click="confirmStop(row.alertNo)">
                  确认
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="toast" class="hint" data-testid="alert-escalate-toast">{{ toast }}</p>

    <h2 style="font-size: 16px; margin: 16px 0 8px">响应率趋势</h2>
    <div v-if="!trend.length" class="empty" data-testid="alert-escalate-trend-empty"><div class="et">暂无趋势</div></div>
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

    <ProtoDrawer :open="timelineOpen" title="升级时间轴" width="640px" @close="closeTimeline">
      <div v-if="timeline" data-testid="alert-escalate-timeline-panel">
        <p class="hint" data-testid="alert-escalate-timeline-status">
          {{ timeline.alertNo }} · {{ timeline.alertLevel }} · {{ timeline.responseStatus }}
          <span v-if="timeline.responseStatus !== 'OPEN'"> · 已响应，升级链停止</span>
        </p>
        <p class="hint">{{ timeline.channelStub || '钉钉/短信外发保持本地桩，未实际发送' }}</p>
        <p v-if="timeline.responseStatus !== 'OPEN'" data-testid="alert-escalate-stopped">
          已响应 · 升级链停止（ALR-E-R3）· {{ timeline.responseStatus }}
        </p>
        <div v-if="!timeline.timeline.length" class="empty"><div class="et">尚未进入下一级</div></div>
        <ul v-else style="list-style: none; padding: 0; margin: 0">
          <li
            v-for="node in timeline.timeline"
            :key="node.escalationLevel + '-' + node.elapsedMinutes + '-' + node.skipped"
            class="card"
            style="margin-bottom: 8px"
            data-testid="alert-escalate-node"
          >
            <strong>{{ levelName(node.escalationLevel) }}</strong>
            · 距产生 {{ node.elapsedMinutes }} 分钟
            <div v-if="node.skipped" class="hint">{{ node.note }}</div>
            <div v-else class="hint">{{ receiverText(node.escalatedTo) }}</div>
            <div class="hint">站内已记录，钉钉不外发，本地桩</div>
          </li>
        </ul>
        <button class="btn btn-sec btn-sm" type="button" @click="closeTimeline">关闭</button>
      </div>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

type Person = { userId?: number; userName: string; roleLabel: string }
type Row = {
  alertNo: string
  ruleCode: string
  ruleName: string
  level: string
  currentLevel: number
  nextEscalateAt: string
}
type Node = {
  escalationLevel: number
  escalatedTo: Person[]
  elapsedMinutes: number
  skipped?: boolean
  note?: string
}
type Timeline = {
  alertNo: string
  alertLevel: string
  responseStatus: string
  channelStub?: string
  timeline: Node[]
}
type Stats = {
  totalAlerts: number
  responseRate: number
  avgResponseMinutes: number
  respondedInTime: number
  target: number
  byLevel: Array<{ level: string; responseRate: number; alertCount: number }>
}
type Trend = { statDate: string; responseRate: number; alertCount: number }

const POLL_MS = 30_000
const CLOCK_MS = 60_000

const route = useRoute()
const form = reactive({
  level1TimeoutMinutes: 30,
  level2TimeoutMinutes: 60,
  severeStartLevel: 2,
})
const savedHint = ref('')
const formError = ref('')
const error = ref('')
const toast = ref('')
const loading = ref(false)
const rows = ref<Row[]>([])
const levelFilter = ref('')
const statsFrom = ref('')
const statsTo = ref('')
const statsError = ref('')
const timelineOpen = ref(false)
const timeline = ref<Timeline | null>(null)
const stats = ref<Stats | null>(null)
const trend = ref<Trend[]>([])
const pollHint = ref('')
const failStreak = ref(0)
const tick = ref(0)
let pollTimer = 0
let clockTimer = 0

const imminent = computed(() => rows.value.some((row) => row.currentLevel < 3 && !!row.nextEscalateAt))
const pollState = computed(() => (imminent.value ? '30 秒轮询中' : '无临近升级，已暂停轮询'))
const rateHint = computed(() => {
  if (!stats.value) return ''
  if (stats.value.totalAlerts === 0) return '当前没有预警样本，不记未达标'
  const mark = stats.value.responseRate >= stats.value.target ? '达标' : '未达标'
  return `${mark}（BR-112 >${stats.value.target}%）`
})

function levelName(level: number) {
  return ({ 1: '一级', 2: '二级', 3: '三级' } as Record<number, string>)[level] || String(level)
}

function rateColor(value: number) {
  if (!stats.value || stats.value.totalAlerts === 0) return 'inherit'
  return value >= 90 ? 'var(--green, #15803d)' : 'var(--orange, #d97706)'
}

function levelColor(item: { responseRate: number; alertCount: number }) {
  if (!item.alertCount || item.responseRate >= 90) return undefined
  return 'var(--orange, #d97706)'
}

function nextText(row: Row) {
  tick.value
  if (row.currentLevel >= 3 || !row.nextEscalateAt) return '终级等待响应'
  const target = new Date(row.nextEscalateAt).getTime()
  const mins = Math.max(0, Math.ceil((target - Date.now()) / 60000))
  const hhmm = row.nextEscalateAt.slice(11, 16)
  const next = row.currentLevel === 1 ? '二级' : '三级'
  return `${hhmm}（再 ${mins} min → ${next}）`
}

function receiverText(people: Person[]) {
  if (!people.length) return '暂无接收人'
  return people.map((item) => `${item.userName}（${item.roleLabel}）`).join('、')
}

function minuteProblem(label: string, value: number | string) {
  if (value === '' || value === null || value === undefined || Number.isNaN(Number(value))) {
    return `${label}升级时限须为 0～10080 的整数`
  }
  const minutes = Number(value)
  if (!Number.isInteger(minutes) || minutes < 0 || minutes > 10080) {
    return `${label}升级时限须在 0～10080 分钟`
  }
  return ''
}

async function saveConfig() {
  savedHint.value = ''
  formError.value = minuteProblem('一级', form.level1TimeoutMinutes) || minuteProblem('二级', form.level2TimeoutMinutes)
  if (formError.value) return
  try {
    await http.put('/alert/escalate/config', {
      level1TimeoutMinutes: form.level1TimeoutMinutes,
      level2TimeoutMinutes: form.level2TimeoutMinutes,
      severeStartLevel: form.severeStartLevel,
      level1Receivers: { dynamicTarget: 'RESPONSIBLE_PERSON' },
      level2Receivers: { dynamicTarget: 'DEPT_LEADER', extraUserIds: [] },
      level3Receivers: { roleCodes: ['R4', 'R1'] },
    })
    savedHint.value = `升级链路已更新：一级 ${form.level1TimeoutMinutes} 分钟，二级 ${form.level2TimeoutMinutes} 分钟`
    await refreshPending(false)
  } catch (err) {
    formError.value = errorMessage(err)
  }
}

function resetLevel() {
  levelFilter.value = ''
  refreshPending(false)
}

async function refreshPending(silent: boolean) {
  if (!silent) loading.value = true
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (levelFilter.value) params.currentLevel = Number(levelFilter.value)
    const res = await http.get('/alert/escalate/pending', { params })
    rows.value = res.data.data?.list || []
    failStreak.value = 0
    pollHint.value = ''
    if (!silent) error.value = ''
  } catch (err) {
    if (!silent) {
      error.value = errorMessage(err)
      rows.value = []
      return
    }
    failStreak.value += 1
    if (failStreak.value >= 3) pollHint.value = '连续刷新失败，请手动刷新'
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadStats() {
  statsError.value = ''
  const params: Record<string, string> = {}
  if (statsFrom.value || statsTo.value) {
    if (!statsFrom.value || !statsTo.value) {
      statsError.value = '请同时填写起止日期'
      return
    }
    params.dateRange = `${statsFrom.value},${statsTo.value}`
  }
  try {
    const [statsRes, trendRes] = await Promise.all([
      http.get('/alert/escalate/response-stats', { params }),
      http.get('/alert/stats/response-rate', { params }),
    ])
    stats.value = statsRes.data.data
    trend.value = trendRes.data.data || []
  } catch (err) {
    statsError.value = errorMessage(err)
  }
}

function resetStatsRange() {
  statsFrom.value = ''
  statsTo.value = ''
  loadStats()
}

async function openTimeline(alertNo: string) {
  toast.value = ''
  try {
    const res = await http.get(`/alert/escalate/timeline/${alertNo}`)
    timeline.value = res.data.data
    timelineOpen.value = true
  } catch (err) {
    toast.value = errorMessage(err)
  }
}

function closeTimeline() {
  timelineOpen.value = false
}

async function confirmStop(alertNo: string) {
  toast.value = ''
  try {
    const res = await http.put(`/alert/check/${alertNo}/respond`, { response: 'CONFIRM', handleRemark: '升级中心确认' })
    const stopped = res.data.data?.escalationStopped
    toast.value = stopped ? `响应成功，后续升级已停止（${alertNo}）` : `已确认（${alertNo}）`
    await refreshPending(false)
  } catch (err) {
    toast.value = errorMessage(err)
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
