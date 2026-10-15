<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>完成率统计</h1>
        <div class="sub">按模板查看上报完成情况</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/submission')">填报单管理</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      完成率 = 审核通过 ÷ 应提交，目标线 95%。通过率 = 已通过 ÷ 已提交，只作辅助，不替代完成率。
    </p>
    <form class="qbar" @submit.prevent="loadAll">
      <input v-model="statPeriod" type="date" data-testid="stat-period" />
      <select v-model.number="templateId" data-testid="stat-template" style="width: 200px">
        <option :value="0">全部模板</option>
        <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.templateName }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadAll">刷新</button>
    </form>

    <div class="g4" style="margin: 12px 0">
      <div class="card stat" data-testid="stat-complete-card">
        <span class="l">完成率</span>
        <div class="n" data-testid="stat-complete-rate" :style="{ color: rateColor(summary?.totalCompleteRate ?? 0) }">
          {{ summary?.totalCompleteRate ?? 0 }}%
        </div>
        <div class="d">审核通过 ÷ 应提交（{{ summary?.completeApprovedCount ?? 0 }}/{{ summary?.shouldCount ?? 0 }}）</div>
        <div class="rate-track" data-testid="stat-target-line">
          <div class="rate-fill" :style="{ width: barWidth(summary?.totalCompleteRate ?? 0) }"></div>
          <i class="target-mark" title="目标线 95%"></i>
        </div>
        <div class="d">目标线 95%</div>
      </div>
      <div class="card stat aux" data-testid="stat-pass-card">
        <span class="l">通过率</span>
        <div class="n" data-testid="stat-pass-rate" :style="{ color: rateColor(summary?.passRate ?? 0) }">
          {{ summary?.passRate ?? 0 }}%
        </div>
        <div class="d">已通过 ÷ 已提交（{{ summary?.approvedCount ?? 0 }}/{{ summary?.submittedCount ?? 0 }}）</div>
      </div>
      <div class="card stat">
        <span class="l">今日上报</span>
        <div class="n" data-testid="stat-today">{{ summary?.todayCount ?? 0 }} 单</div>
        <div class="d">当日已提交的填报单</div>
      </div>
      <div class="card stat">
        <span class="l">字段校验命中率</span>
        <div class="n" data-testid="stat-field-hit">{{ summary?.fieldCheckHitRate ?? 0 }}%</div>
        <div class="d">必填、范围和字段校验</div>
      </div>
      <div class="card stat">
        <span class="l">平均审核时长</span>
        <div class="n" data-testid="stat-audit-hours">{{ summary?.avgAuditHours ?? 0 }}h</div>
        <div class="d">超 4h 自动催办</div>
      </div>
    </div>

    <div class="sec">近 7 天上报量与通过量</div>
    <div class="card trend-card" data-testid="stat-trend">
      <svg viewBox="0 0 420 180" role="img" aria-label="近 7 天上报量与通过量">
        <polyline :points="linePoints('submittedCount')" fill="none" stroke="#0071e3" stroke-width="2" />
        <polyline :points="linePoints('approvedCount')" fill="none" stroke="#34c759" stroke-width="2" />
        <text
          v-for="(day, index) in trend7"
          :key="day.statPeriod"
          :x="pointX(index)"
          y="172"
          font-size="10"
          text-anchor="middle"
          fill="#6d6d72"
        >
          {{ day.statPeriod.slice(5) }}
        </text>
      </svg>
      <div class="legend">
        <span><i class="swatch" style="background: #0071e3"></i>上报量</span>
        <span><i class="swatch" style="background: #34c759"></i>通过量</span>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'template' }"
        @click="tab = 'template'"
      >
        按模板
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" @click="tab = 'dept'">
        按部门
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'trend' }" @click="tab = 'trend'">
        周期趋势
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'missed' }"
        data-testid="stat-missed-tab"
        @click="tab = 'missed'"
      >
        未交清单
      </button>
    </div>

    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>

    <div v-if="tab === 'template'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>模板</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!summary?.byTemplate?.length">
              <td colspan="4"><div class="empty"><div class="et">暂无数据</div></div></td>
            </tr>
            <tr v-for="row in summary?.byTemplate || []" v-else :key="row.templateId">
              <td>{{ row.templateName }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td :style="{ color: rateColor(row.completeRate) }">{{ row.completeRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'dept'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>部门</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary?.byDept || []" :key="row.deptName">
              <td>{{ row.deptName }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td :style="{ color: rateColor(row.completeRate) }">{{ row.completeRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'trend'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>周期</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
              <th>退回率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!trend.length">
              <td colspan="5"><div class="empty"><div class="et">暂无趋势</div></div></td>
            </tr>
            <tr v-for="row in trend" v-else :key="row.statPeriod">
              <td class="mono">{{ row.statPeriod }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td>{{ row.completeRate }}%</td>
              <td>{{ row.rejectRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'missed'" class="tbl-block" data-testid="stat-missed">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>填报人</th>
              <th>部门</th>
              <th>模板</th>
              <th>周期</th>
              <th>截止</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!missed.length">
              <td colspan="6"><div class="empty"><div class="et">暂无未交</div></div></td>
            </tr>
            <tr v-for="row in missed" v-else :key="`${row.templateName}-${row.period}-${row.userId}`">
              <td>{{ row.userName }}</td>
              <td>{{ row.deptName || '—' }}</td>
              <td>{{ row.templateName }}</td>
              <td class="mono">{{ row.period }}</td>
              <td class="mono">{{ row.dueTime }}</td>
              <td>{{ missedLabel(row.status) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Summary = {
  totalCompleteRate: number
  shouldCount: number
  completeApprovedCount: number
  submittedCount: number
  approvedCount: number
  passRate: number
  rejectCount: number
  todayCount: number
  todayCompleteRate: number
  fieldCheckHitRate: number
  avgAuditHours: number
  byTemplate: Array<{
    templateId: number
    templateName: string
    shouldCount: number
    approvedCount: number
    completeRate: number
  }>
  byDept: Array<{
    deptName: string
    shouldCount: number
    approvedCount: number
    completeRate: number
  }>
}

type TrendRow = {
  statPeriod: string
  shouldCount: number
  submittedCount: number
  approvedCount: number
  completeRate: number
  rejectRate: number
}

type MissedRow = {
  userId: number
  userName: string
  deptName: string
  templateName: string
  period: string
  dueTime: string
  status: string
}

type TemplateOpt = { id: number; templateName: string }

const router = useRouter()
const statPeriod = ref('')
const templateId = ref(0)
const templates = ref<TemplateOpt[]>([])
const summary = ref<Summary | null>(null)
const trend = ref<TrendRow[]>([])
const missed = ref<MissedRow[]>([])
const tab = ref<'template' | 'dept' | 'trend' | 'missed'>('template')
const loading = ref(false)
const error = ref('')

function last7Days() {
  const now = new Date(Date.now() + 8 * 60 * 60 * 1000)
  const days: string[] = []
  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = new Date(now)
    day.setUTCDate(day.getUTCDate() - offset)
    days.push(day.toISOString().slice(0, 10))
  }
  return days
}

const trend7 = computed<TrendRow[]>(() => {
  const map = new Map(trend.value.map((row) => [row.statPeriod, row]))
  return last7Days().map(
    (day) =>
      map.get(day) || {
        statPeriod: day,
        shouldCount: 0,
        submittedCount: 0,
        approvedCount: 0,
        completeRate: 0,
        rejectRate: 0,
      },
  )
})

function pointX(index: number) {
  return 36 + index * 58
}

function linePoints(key: 'submittedCount' | 'approvedCount') {
  const max = Math.max(1, ...trend7.value.map((row) => Math.max(row.submittedCount || 0, row.approvedCount || 0)))
  return trend7.value
    .map((row, index) => {
      const y = 140 - ((Number(row[key]) || 0) / max) * 110
      return `${pointX(index)},${y}`
    })
    .join(' ')
}

function go(path: string) {
  router.push(path)
}

function missedLabel(status: string) {
  if (status === 'LATE') return '迟交'
  if (status === 'PENDING_AUDIT') return '待审核'
  return '未交'
}

function rateColor(rate: number) {
  if (rate >= 95) return 'var(--green)'
  if (rate >= 90) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

function barWidth(rate: number) {
  const width = Math.max(0, Math.min(100, Number(rate) || 0))
  return `${width}%`
}

async function loadTemplates() {
  try {
    const res = await http.get('/report/template/list', { params: { pageNo: 1, pageSize: 100 } })
    templates.value = res.data.data?.list || []
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {}
    if (statPeriod.value.trim()) params.statPeriod = statPeriod.value.trim()
    if (templateId.value) params.templateId = templateId.value
    const res = await http.get('/report/stat/complete-rate', { params })
    summary.value = res.data.data

    const days = last7Days()
    const trendParams: Record<string, string | number> = { dateRange: `${days[0]},${days[6]}` }
    if (templateId.value) trendParams.templateId = templateId.value
    const tr = await http.get('/report/stat/trend', { params: trendParams })
    trend.value = tr.data.data || []
    const missedRes = await http.get('/report/stat/missed', { params: { ...params, pageNo: 1, pageSize: 100 } })
    missed.value = missedRes.data.data?.list || []
  } catch (err) {
    error.value = errorMessage(err)
    summary.value = null
    missed.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTemplates()
  loadAll()
})
</script>

<style scoped>
.g4 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.sec {
  margin: 8px 0;
  font-weight: 600;
}
.trend-card {
  padding: 12px;
}
.trend-card svg {
  width: 100%;
  height: 180px;
}
.legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text2);
}
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 4px;
  border-radius: 2px;
}
.stat .l {
  font-size: 12px;
  color: var(--text2);
}
.stat .n {
  font-size: 28px;
  font-weight: 600;
  margin: 4px 0;
}
.stat .d {
  font-size: 11px;
  color: var(--text2);
}
.stat.aux .n {
  font-size: 22px;
}
.rate-track {
  position: relative;
  height: 8px;
  margin: 8px 0 4px;
  background: rgba(142, 142, 147, 0.18);
  border-radius: 4px;
}
.rate-fill {
  height: 100%;
  background: #0071e3;
  border-radius: 4px;
}
.target-mark {
  position: absolute;
  top: -3px;
  left: 95%;
  width: 2px;
  height: 14px;
  background: #c62828;
}
.tabs .tab {
  background: none;
  border: none;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text2);
  border-bottom: 2px solid transparent;
}
.tabs .tab.on {
  color: var(--text);
  border-bottom-color: var(--blue);
  font-weight: 600;
}
</style>
