<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>提交率统计</h1>
        <div class="sub">按时提交率</div>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      分子 = 当日 22:00 前提交；分母 = 已提交日报（不含草稿）。目标大于 95%。
    </p>
    <form class="qbar" @submit.prevent="load">
      <input v-model="dateFrom" placeholder="起始 yyyy-MM-dd" style="width: 140px" />
      <input v-model="dateTo" placeholder="结束 yyyy-MM-dd" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div v-if="summary" class="stat-grid">
      <div class="card stat">
        <span class="l">本周提交率</span>
        <div class="n">{{ summary.weekSubmitCount }}/{{ summary.weekShouldCount }}</div>
        <div class="d">{{ summary.weekSubmitRate }}% · 人次</div>
      </div>
      <div class="card stat">
        <span class="l">准时率</span>
        <div class="n" :style="{ color: rateColor(summary.totalOnTimeRate) }">{{ summary.totalOnTimeRate }}%</div>
        <div class="d">环比 {{ deltaText }}</div>
      </div>
      <div class="card stat">
        <span class="l">字段完成度均值</span>
        <div class="n">{{ summary.fieldCompletenessAvg }}%</div>
      </div>
      <div class="card stat">
        <span class="l">审阅完成率</span>
        <div class="n">{{ summary.reviewDoneRate }}%</div>
        <div class="d">待审 {{ summary.pendingReviewCount }}</div>
      </div>
    </div>
    <div v-if="summary" class="card" style="padding: 12px; margin-bottom: 12px" data-testid="daily-trend">
      <b>近 7 天提交趋势</b>
      <svg viewBox="0 0 280 120" width="100%" height="140" role="img" aria-label="近7天提交趋势">
        <polyline :points="trendPoints" fill="none" stroke="#0071e3" stroke-width="2" />
        <text v-for="(point, index) in trendDots" :key="point.date" :x="point.x" :y="112" font-size="8" text-anchor="middle">
          {{ point.date.slice(5) }}
        </text>
      </svg>
      <p class="hint">应提交人次按本周已出现的提交人 × 已过工作日估算，未扣请假和节假日。</p>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" @click="tab = 'dept'">按部门</button>
      <button type="button" class="tab" :class="{ on: tab === 'person' }" @click="tab = 'person'">按人员</button>
    </div>

    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>

    <div v-if="tab === 'dept'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>部门</th>
              <th>按时率</th>
              <th>提交率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="3"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!summary?.byDept?.length">
              <td colspan="3"><div class="empty"><div class="et">暂无数据</div></div></td>
            </tr>
            <tr v-for="row in summary?.byDept || []" v-else :key="row.deptId">
              <td>{{ row.deptName }}</td>
              <td :style="{ color: rateColor(row.onTimeRate) }">{{ row.onTimeRate }}%</td>
              <td>{{ row.submitRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'person'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>姓名</th>
              <th>部门</th>
              <th>应报天</th>
              <th>已报天</th>
              <th>按时天</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary?.byPerson || []" :key="row.userId">
              <td>{{ row.userName }}</td>
              <td>{{ row.deptName }}</td>
              <td class="num">{{ row.shouldDays }}</td>
              <td class="num">{{ row.submittedDays }}</td>
              <td class="num">{{ row.onTimeDays }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type TrendPoint = { date: string; onTimeRate: number; submitCount?: number }
type Summary = {
  totalOnTimeRate: number
  onTimeRateDelta?: number
  weekSubmitCount?: number
  weekShouldCount?: number
  weekSubmitRate?: number
  fieldCompletenessAvg?: number
  reviewDoneRate?: number
  pendingReviewCount?: number
  dateFrom: string
  dateTo: string
  byDept: { deptId: number; deptName: string; onTimeRate: number; submitRate: number }[]
  byPerson: {
    userId: number
    userName: string
    deptName: string
    shouldDays: number
    submittedDays: number
    onTimeDays: number
  }[]
  trend: TrendPoint[]
  trend7?: TrendPoint[]
}

const summary = ref<Summary | null>(null)
const loading = ref(false)
const error = ref('')
const tab = ref<'dept' | 'person'>('dept')
const deltaText = computed(() => {
  const delta = summary.value?.onTimeRateDelta ?? 0
  return `${delta > 0 ? '+' : ''}${delta}%`
})
const trendDots = computed(() => {
  const rows = summary.value?.trend7 || summary.value?.trend || []
  if (!rows.length) return []
  const max = Math.max(1, ...rows.map((row) => row.submitCount ?? row.onTimeRate))
  return rows.map((row, index) => {
    const x = rows.length === 1 ? 140 : 16 + (index * 248) / (rows.length - 1)
    const value = row.submitCount ?? row.onTimeRate
    const y = 96 - (value / max) * 72
    return { ...row, x, y }
  })
})
const trendPoints = computed(() => trendDots.value.map((point) => `${point.x},${point.y}`).join(' '))
const dateFrom = ref('')
const dateTo = ref('')

function rateColor(rate: number) {
  if (rate >= 95) return 'var(--green)'
  if (rate >= 80) return 'var(--orange, #e6a23c)'
  return 'var(--red)'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/meet/stat/on-time-rate', {
      params: {
        dateFrom: dateFrom.value || undefined,
        dateTo: dateTo.value || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      summary.value = null
      return
    }
    summary.value = res.data.data
  } catch (errorValue: unknown) {
    error.value = errorMessage(errorValue)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 12px 0;
}
@media (max-width: 900px) {
  .stat-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
