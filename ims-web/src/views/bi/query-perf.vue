<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>查询性能监控</h1>
        <div class="sub">BI-002 · /ims/bi/query/perf · GET /bi/query/perf-stats · BR-204 / V3-B6 · 无菜单</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/preview">返回预览与下钻</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <input v-model="start" data-testid="bi-perf-from" type="date" />
      <input v-model="end" data-testid="bi-perf-to" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="bi-perf-refresh">刷新</button>
    </form>

    <p v-if="alertText" class="hint" data-testid="bi-perf-alert" style="color: var(--red); font-weight: 600">
      {{ alertText }}
    </p>
    <p v-if="error" class="hint" data-testid="bi-perf-error" style="color: var(--red)">{{ error }}</p>
    <div v-if="stats && stats.totalQueries === 0" class="empty" data-testid="bi-perf-empty" style="margin-top: 12px">
      <div class="et">所选日期内暂无查询</div>
    </div>

    <div v-if="stats" class="perf-grid">
      <div class="card stat">
        <span class="l">查询总量</span>
        <div class="n" data-testid="bi-perf-total">{{ stats.totalQueries }}</div>
        <div class="d">所选日期内审计</div>
      </div>
      <div class="card stat">
        <span class="l">平均耗时</span>
        <div class="n" data-testid="bi-perf-avg">{{ fmtMs(stats.avgCostMs) }}</div>
        <div class="d">含同步与异步</div>
      </div>
      <div class="card stat">
        <span class="l">P95</span>
        <div class="n" data-testid="bi-perf-p95">{{ fmtMs(stats.p95CostMs) }}</div>
        <div class="d">BR-204</div>
      </div>
      <div class="card stat" :style="stats.over30sCount > 0 ? { outline: '1px solid var(--red)' } : undefined">
        <span class="l">超 30 秒</span>
        <div
          class="n"
          data-testid="bi-perf-over30"
          :style="stats.over30sCount > 0 ? { color: 'var(--red)' } : undefined"
        >
          {{ stats.over30sCount }}
        </div>
        <div class="d">已终止次数</div>
      </div>
      <div class="card stat">
        <span class="l">异步转化</span>
        <div class="n" data-testid="bi-perf-async">{{ stats.asyncConvertedCount }}</div>
        <div class="d">V3-B6</div>
      </div>
    </div>

    <div v-if="stats" class="tbl-block" data-testid="bi-perf-slow" style="margin-top: 12px">
      <p class="hint">慢报表是耗时达到 30 秒被终止的查询。点名称进入设计器，缩小日期或平台筛选后再查。</p>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>报表</th>
              <th>平均耗时</th>
              <th>超 30 秒次数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in stats.topSlowReports" :key="`${row.reportId}-${row.reportName}`" data-testid="bi-perf-slow-row">
              <td>
                <button
                  type="button"
                  class="btn btn-sec btn-sm"
                  :disabled="!row.reportId"
                  @click="openReport(row)"
                >
                  {{ row.reportName || '预览与下钻' }}
                </button>
              </td>
              <td class="num" :style="row.avgCostMs > 30000 ? { color: 'var(--red)' } : undefined">
                {{ fmtMs(row.avgCostMs) }}
              </td>
              <td class="num">{{ row.queryCount }}</td>
            </tr>
            <tr v-if="!stats.topSlowReports.length">
              <td colspan="3"><div class="empty"><div class="et">暂无慢报表</div></div></td>
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

type SlowReport = { reportId: number; reportName: string; avgCostMs: number; queryCount: number }
type PerfStats = {
  totalQueries: number
  avgCostMs: number
  p95CostMs: number
  over30sCount: number
  asyncConvertedCount: number
  topSlowReports: SlowReport[]
}

const router = useRouter()
const start = ref('')
const end = ref('')
const stats = ref<PerfStats | null>(null)
const error = ref('')

const alertText = computed(() => {
  if (!stats.value || stats.value.over30sCount <= 0) return ''
  return '有查询超过 30 秒已终止（BR-204），建议缩小筛选范围'
})

function ymd(date: Date) {
  const bj = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())}`
}

function fmtMs(value: number) {
  return `${Number(value || 0).toLocaleString('zh-CN')}ms`
}

function openReport(row: SlowReport) {
  if (!row.reportId) return
  router.push({ path: '/ims/bi/report/designer', query: { reportId: String(row.reportId) } })
}

async function load() {
  error.value = ''
  const from = start.value
  const to = end.value
  if ((from && !to) || (!from && to)) {
    error.value = '请同时填写开始和结束日期'
    return
  }
  if (from && to && from > to) {
    error.value = '开始日期不能晚于结束日期'
    return
  }
  try {
    const params: Record<string, string> = {}
    if (from && to) params.dateRange = `${from},${to}`
    const res = await http.get('/bi/query/perf-stats', { params })
    stats.value = res.data.data
  } catch (err) {
    stats.value = null
    error.value = errorMessage(err)
  }
}

onMounted(() => {
  const today = new Date()
  const from = new Date()
  from.setDate(today.getDate() - 6)
  start.value = ymd(from)
  end.value = ymd(today)
  load()
})
</script>

<style scoped>
.perf-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 1100px) {
  .perf-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
