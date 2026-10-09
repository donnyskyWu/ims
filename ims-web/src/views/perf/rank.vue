<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>排名与预警</h1>
        <div class="sub">PERF-004 · 综合得分低于 60 预警本人、直属上级与 HR。连续两月待改进进入辅导名单。</div>
      </div>
      <label>
        周期
        <input v-model="period" data-testid="perf-rank-period" type="month" @change="reload" />
      </label>
    </div>

    <p v-if="error" data-testid="perf-rank-error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div class="tabs" style="margin: 12px 0">
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'board' }"
        data-testid="perf-rank-tab-board"
        @click="tab = 'board'"
      >
        排名看板
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'alerts' }"
        data-testid="perf-rank-tab-alerts"
        @click="tab = 'alerts'"
      >
        预警清单
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'coaching' }"
        data-testid="perf-rank-tab-coaching"
        @click="tab = 'coaching'"
      >
        重点辅导名单
      </button>
    </div>

    <template v-if="tab === 'board'">
      <p data-testid="perf-rank-distribution" class="hint">
        优秀 {{ distribution.excellent }} | 合格 {{ distribution.qualified }} | 待改进 {{ distribution.improve }}（含预警
        {{ alertedCount }}）
      </p>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>排名</th>
                <th>员工</th>
                <th>部门</th>
                <th>综合得分</th>
                <th>分档</th>
                <th>预警</th>
                <th>连续待改进</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!ranks.length">
                <td colspan="7"><div class="empty"><div class="et">本周期还没有已发布排名</div></div></td>
              </tr>
              <tr v-for="row in ranks" v-else :key="row.id" :data-testid="`perf-rank-row-${row.userName}`">
                <td class="num">{{ row.rankNo }}</td>
                <td>{{ row.userName }}</td>
                <td>{{ row.deptName }}</td>
                <td class="num">{{ scoreText(row.totalScore) }}</td>
                <td><span class="tag">{{ gradeText(row.gradeLevel) }}</span></td>
                <td>
                  <span v-if="row.alertStatus === 'ALERTED'" class="tag" style="color: var(--red)">已预警</span>
                  <span v-else>—</span>
                </td>
                <td class="num">{{ row.consecutiveMonths || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'alerts'">
      <form class="qbar" @submit.prevent="loadAlerts">
        <select v-model="handleStatus" data-testid="perf-alert-status-filter" style="width: 140px">
          <option value="">全部处置</option>
          <option value="PENDING">待处置</option>
          <option value="DONE">已处置</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>周期</th>
                <th>员工</th>
                <th>部门</th>
                <th>得分</th>
                <th>预警时间</th>
                <th>推送对象</th>
                <th>处置</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!alerts.length">
                <td colspan="8"><div class="empty"><div class="et">没有预警</div></div></td>
              </tr>
              <tr v-for="row in alerts" :key="row.id" data-testid="perf-alert-row">
                <td class="mono">{{ row.periodMonth }}</td>
                <td>{{ row.userName }}</td>
                <td>{{ row.deptName }}</td>
                <td class="num" style="color: var(--red)">{{ scoreText(row.totalScore) }}</td>
                <td>{{ row.alertedAt }}</td>
                <td>
                  <span v-for="target in row.pushTargets" :key="target" class="tag" style="margin-right: 4px">
                    {{ pushText(target) }}
                  </span>
                </td>
                <td>
                  <span class="tag" data-testid="perf-alert-status">{{ row.handleStatus === 'DONE' ? '已处置' : '待处置' }}</span>
                </td>
                <td>
                  <button
                    v-if="row.handleStatus === 'PENDING'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="perf-alert-handle"
                    @click="openHandle(row)"
                  >
                    处置登记
                  </button>
                  <span v-else class="csub">{{ row.handleRemark || '已登记' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else>
      <p class="hint">连续 2 月待改进。名单推送部门负责人与运营总监（本地名单，不外发钉钉）。</p>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>员工</th>
                <th>部门</th>
                <th>连续月数</th>
                <th>近两周期</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!coaching.length">
                <td colspan="5"><div class="empty"><div class="et">没有连续两月待改进的员工</div></div></td>
              </tr>
              <tr v-for="row in coaching" :key="`${row.userId}-${row.periodMonth}`" data-testid="perf-coaching-row">
                <td>{{ row.userName }}</td>
                <td>{{ row.deptName }}</td>
                <td class="num">{{ row.consecutiveMonths }}</td>
                <td :style="trendStyle(row)">{{ trendText(row) }}</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="perf-coaching-detail" @click="openCoach(row)">
                    辅导详情
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <ProtoDrawer :open="handleOpen" title="预警处置登记" width="560px" @close="handleOpen = false">
      <p v-if="activeAlert" class="hint">
        {{ activeAlert.userName }} · {{ activeAlert.periodMonth }} · {{ scoreText(activeAlert.totalScore) }}
      </p>
      <p class="hint">推送对象：本人、直属上级、HR。本地只记站内说明，不外发。</p>
      <div class="fld">
        <label>处置说明</label>
        <textarea v-model="handleRemark" data-testid="perf-alert-remark" rows="3" />
      </div>
      <div class="fld">
        <label>后续辅导计划</label>
        <textarea v-model="followUpPlan" data-testid="perf-alert-plan" rows="3" />
      </div>
      <p v-if="handleError" data-testid="perf-alert-error" class="hint" style="color: var(--red)">{{ handleError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="handleOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="perf-alert-save" @click="saveHandle">登记</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="coachOpen" title="辅导详情" width="640px" @close="coachOpen = false">
      <template v-if="activeCoach">
        <p>{{ activeCoach.userName }} · {{ activeCoach.deptName }} · 连续 {{ activeCoach.consecutiveMonths }} 月待改进</p>
        <ul data-testid="perf-coaching-periods">
          <li v-for="item in activeCoach.lastTwoPeriods" :key="item.periodMonth">
            {{ item.periodMonth }} {{ scoreText(item.totalScore) }} {{ gradeText(item.gradeLevel) }}
          </li>
        </ul>
        <p class="hint">已列入重点辅导，推送部门负责人与运营总监。</p>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type RankRow = {
  id: number
  userId: number
  userName: string
  deptName: string
  totalScore: number
  rankNo: number
  gradeLevel: string
  alertStatus: string
  consecutiveMonths: number
  periodMonth: string
  lastTwoPeriods?: Array<{ periodMonth: string; totalScore: number; gradeLevel: string }>
}
type AlertRow = {
  id: number
  periodMonth: string
  userName: string
  deptName: string
  totalScore: number
  alertedAt: string
  pushTargets: string[]
  handleStatus: string
  handleRemark?: string
}

const period = ref(previousMonth())
const tab = ref<'board' | 'alerts' | 'coaching'>('board')
const loading = ref(false)
const error = ref('')
const ranks = ref<RankRow[]>([])
const alerts = ref<AlertRow[]>([])
const coaching = ref<RankRow[]>([])
const handleStatus = ref('')
const handleOpen = ref(false)
const activeAlert = ref<AlertRow | null>(null)
const handleRemark = ref('')
const followUpPlan = ref('')
const handleError = ref('')
const coachOpen = ref(false)
const activeCoach = ref<RankRow | null>(null)

const distribution = computed(() => ({
  excellent: ranks.value.filter((row) => row.gradeLevel === 'EXCELLENT').length,
  qualified: ranks.value.filter((row) => row.gradeLevel === 'QUALIFIED').length,
  improve: ranks.value.filter((row) => row.gradeLevel === 'IMPROVE').length,
}))
const alertedCount = computed(() => ranks.value.filter((row) => row.alertStatus === 'ALERTED').length)

function previousMonth() {
  const now = new Date()
  const cursor = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  return `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`
}

function scoreText(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(2)
}

function gradeText(level: string) {
  if (level === 'EXCELLENT') return '优秀'
  if (level === 'QUALIFIED') return '合格'
  if (level === 'IMPROVE') return '待改进'
  return level || '—'
}

function pushText(target: string) {
  if (target === 'SELF') return '本人'
  if (target === 'SUPERIOR') return '直属上级'
  if (target === 'HR') return 'HR'
  return target
}

function trendText(row: RankRow) {
  const periods = row.lastTwoPeriods || []
  if (!periods.length) return '—'
  return periods.map((item) => `${item.periodMonth} ${scoreText(item.totalScore)}`).join(' → ')
}

function trendStyle(row: RankRow) {
  const periods = row.lastTwoPeriods || []
  if (periods.length < 2) return {}
  if (periods[1].totalScore < periods[0].totalScore) return { color: 'var(--red)' }
  return {}
}

function rejectText(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    return `${body.code ?? ''} ${body.msg || ''}`.trim()
  }
  return errorMessage(err)
}

async function loadBoard() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get(`/perf/rank/period/${period.value}`, { params: { pageNo: 1, pageSize: 200 } })
    ranks.value = res.data.data.list || []
  } catch (err) {
    ranks.value = []
    error.value = rejectText(err)
  } finally {
    loading.value = false
  }
}

async function loadAlerts() {
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 100, periodMonth: period.value }
    if (handleStatus.value) params.handleStatus = handleStatus.value
    const res = await http.get('/perf/rank/alerts', { params })
    alerts.value = res.data.data.list || []
  } catch (err) {
    alerts.value = []
    error.value = rejectText(err)
  }
}

async function loadCoaching() {
  error.value = ''
  try {
    const res = await http.get('/perf/rank/coaching-list')
    const rows = (res.data.data || []) as RankRow[]
    coaching.value = rows.filter((row) => (row.lastTwoPeriods || []).some((item) => item.periodMonth === period.value) || row.periodMonth === period.value)
  } catch (err) {
    coaching.value = []
    error.value = rejectText(err)
  }
}

async function reload() {
  await Promise.all([loadBoard(), loadAlerts(), loadCoaching()])
}

function openHandle(row: AlertRow) {
  activeAlert.value = row
  handleRemark.value = ''
  followUpPlan.value = ''
  handleError.value = ''
  handleOpen.value = true
}

async function saveHandle() {
  if (!activeAlert.value) return
  handleError.value = ''
  try {
    await http.put(`/perf/rank/alert/${activeAlert.value.id}/handle`, {
      handleRemark: handleRemark.value.trim(),
      followUpPlan: followUpPlan.value.trim(),
    })
    handleOpen.value = false
    await loadAlerts()
  } catch (err) {
    handleError.value = rejectText(err)
  }
}

function openCoach(row: RankRow) {
  activeCoach.value = row
  coachOpen.value = true
}

onMounted(reload)
</script>
