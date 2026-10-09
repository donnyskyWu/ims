<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>穿透性能监控</h1>
        <div class="sub">DC-001 · /ims/dc/trace/perf · GET /dc/trace/perf-metrics · BR-205</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/dc/trace">返回穿透查询</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <input v-model="start" data-testid="dc-trace-perf-from" type="date" />
      <input v-model="end" data-testid="dc-trace-perf-to" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-trace-perf-refresh">刷新</button>
    </form>

    <p
      v-if="rangeNote"
      class="hint"
      data-testid="dc-trace-perf-range"
      style="color: var(--red); font-weight: 600"
    >
      {{ rangeNote }}
    </p>
    <p
      v-if="alertText"
      class="hint"
      data-testid="dc-trace-perf-alert"
      style="color: var(--red); font-weight: 600"
    >
      {{ alertText }}
    </p>
    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div v-if="metrics" class="perf-grid">
      <div class="card stat" :style="overP95 ? { outline: '1px solid var(--red)' } : undefined">
        <span class="l">P95</span>
        <div class="n" data-testid="dc-trace-perf-p95" :style="overP95 ? { color: 'var(--red)' } : undefined">
          {{ fmtMs(metrics.p95Ms) }}
        </div>
        <div class="d">{{ overP95 ? '超标' : '达标' }}</div>
      </div>
      <div class="card stat" :style="overP99 ? { outline: '1px solid var(--red)' } : undefined">
        <span class="l">P99</span>
        <div class="n" data-testid="dc-trace-perf-p99" :style="overP99 ? { color: 'var(--red)' } : undefined">
          {{ fmtMs(metrics.p99Ms) }}
        </div>
        <div class="d">目标 &lt; 8,000ms</div>
      </div>
      <div class="card stat">
        <span class="l">查询总量</span>
        <div class="n" data-testid="dc-trace-perf-count">{{ metrics.queryCount }}</div>
        <div class="d">所选日期内审计留痕</div>
      </div>
      <div class="card stat">
        <span class="l">目标 P95</span>
        <div class="n" data-testid="dc-trace-perf-target">{{ fmtMs(metrics.targetP95Ms) }}</div>
        <div class="d">BR-205</div>
      </div>
      <div class="card stat" :style="!metrics.dailyPressureTestPassed ? { outline: '1px solid var(--red)' } : undefined">
        <span class="l">每日压测</span>
        <div
          class="n"
          data-testid="dc-trace-perf-pressure"
          :style="!metrics.dailyPressureTestPassed ? { color: 'var(--red)', fontSize: '18px' } : { fontSize: '18px' }"
        >
          {{ metrics.dailyPressureTestPassed ? '通过' : '今日压测未通过' }}
        </div>
        <div class="d">区间末日满 10 条且 P95 ≤ 目标</div>
      </div>
    </div>

    <div v-if="metrics" class="tbl-block" data-testid="dc-trace-perf-slow" style="margin-top: 12px">
      <p class="hint">每日自动执行 10 条典型穿透用例（V3-C3）。P95 超标时下面列出耗时超过 3,000ms 的查询。</p>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>查询 ID</th>
              <th>穿透入口</th>
              <th>耗时</th>
              <th>发生时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in metrics.slowQueries" :key="row.queryId" data-testid="dc-trace-perf-row">
              <td class="mono">{{ row.queryId }}</td>
              <td>
                <button type="button" class="btn btn-sec btn-sm" @click="openEntry(row)">{{ row.entryLabel || '—' }}</button>
              </td>
              <td class="num" style="color: var(--red)">{{ fmtMs(row.costMs) }}</td>
              <td>{{ row.occurredAt }}</td>
            </tr>
            <tr v-if="!metrics.slowQueries.length" data-testid="dc-trace-perf-empty">
              <td colspan="4"><div class="empty"><div class="et">{{ slowEmptyText }}</div></div></td>
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

type SlowQuery = { queryId: string; entryLabel: string; costMs: number; occurredAt: string }
type PerfMetrics = {
  p95Ms: number
  p99Ms: number
  targetP95Ms: number
  queryCount: number
  slowQueries: SlowQuery[]
  dailyPressureTestPassed: boolean
}

const router = useRouter()
const start = ref('')
const end = ref('')
const metrics = ref<PerfMetrics | null>(null)
const error = ref('')
const rangeNote = ref('')
const slowEmptyText = computed(() => {
  if ((metrics.value?.queryCount || 0) === 0) return '所选日期暂无穿透查询'
  return '所选日期暂无慢查询'
})

const overP95 = computed(() => (metrics.value?.p95Ms ?? 0) > 3000)
const overP99 = computed(() => (metrics.value?.p99Ms ?? 0) > 8000)
const alertText = computed(() => {
  if (!metrics.value) return ''
  if (metrics.value.p95Ms > 3000) {
    return '穿透 P95 超标（BR-205 目标 < 3000ms），已自动告警并出具慢查询清单'
  }
  return ''
})

function ymd(date: Date) {
  const bj = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())}`
}

function fmtMs(value: number) {
  return `${Number(value || 0).toLocaleString('zh-CN')}ms`
}

function openEntry(row: SlowQuery) {
  router.push({ path: '/ims/dc/trace', query: row.entryLabel ? { keyword: row.entryLabel } : {} })
}

function rangeEdge(): string {
  if ((start.value && !end.value) || (!start.value && end.value)) return '请同时填写开始日和结束日'
  if (start.value && end.value && start.value > end.value) return '开始日期不能晚于结束日期'
  return ''
}

async function load() {
  error.value = ''
  rangeNote.value = ''
  const edge = rangeEdge()
  if (edge) {
    rangeNote.value = edge
    metrics.value = null
    return
  }
  try {
    const params: Record<string, string> = {}
    if (start.value && end.value) params.dateRange = `${start.value},${end.value}`
    const res = await http.get('/dc/trace/perf-metrics', { params })
    metrics.value = res.data.data
  } catch (err) {
    metrics.value = null
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
  .perf-grid { grid-template-columns: 1fr 1fr; }
}
</style>
