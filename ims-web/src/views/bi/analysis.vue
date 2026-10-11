<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>指标分析</h1>
        <div class="sub">FR-M6-001 分析视图 · /ims/bi/analysis · 17a BI0</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/metric">指标管理</router-link>
      </div>
    </div>

    <p v-if="toast" class="hint" data-testid="bi-analysis-toast">{{ toast }}</p>

    <form class="qbar" @submit.prevent="runAnalysis">
      <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">
        <span class="csub">选择指标</span>
        <select v-model="selectedIds" data-testid="bi-analysis-metrics" multiple style="min-width: 220px; min-height: 56px">
          <option v-for="m in metricOptions" :key="m.id" :value="m.id">{{ m.metricName }} ({{ m.metricCode }})</option>
        </select>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">IP 组</span>
        <select v-model="ipGroupName" data-testid="bi-analysis-ip" style="width: 140px">
          <option value="">全部</option>
          <option v-for="name in ipNames" :key="name" :value="name">{{ name }}</option>
        </select>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">统计日期</span>
        <input v-model="dateStart" data-testid="bi-analysis-from" type="date" style="width: 140px" />
        <span>~</span>
        <input v-model="dateEnd" data-testid="bi-analysis-to" type="date" style="width: 140px" />
      </div>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="bi-analysis-run">运行分析</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetForm">重置</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="bi-analysis-export" @click="exportCsv">导出</button>
    </form>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'DETAIL' }" @click="tab = 'DETAIL'">指标明细</div>
      <div class="tab" :class="{ on: tab === 'TREND' }" @click="tab = 'TREND'">指标趋势</div>
    </div>

    <p v-if="analysisError" class="hint" data-testid="bi-analysis-error" style="color: var(--red)">{{ analysisError }}</p>

    <div v-if="ran && !resultRows.length && !loading && !analysisError" class="empty" data-testid="bi-analysis-empty">
      <div class="et">{{ emptyReason }}</div>
    </div>
    <div v-else-if="!resultRows.length && !loading && !analysisError" class="empty">
      <div class="et">请选择指标并运行分析</div>
      <div class="es">多选 metricIds + 参数后点「运行分析」· 只读消费</div>
    </div>

    <div v-if="loading" class="empty"><div class="et">分析中…</div></div>

    <div v-if="resultRows.length && tab === 'DETAIL'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>统计日期</th>
              <th>IP组</th>
              <th>指标名称</th>
              <th>指标值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in resultRows" :key="`${row.metricId}-${row.ipGroupName}-${idx}`">
              <td class="num">{{ row.statDate }}</td>
              <td>{{ row.ipGroupName }}</td>
              <td style="font-weight: 500">{{ row.metricName }}</td>
              <td class="num">{{ row.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="hint" data-testid="bi-analysis-page" style="margin-top: 8px">
        共 {{ total }} 条 · 第 {{ pageNo }} 页 · 每页 {{ pageSize }} 条
      </div>
    </div>

    <div v-if="resultRows.length && tab === 'TREND'" class="tbl-block" data-testid="bi-analysis-chart">
      <div class="card" style="padding: 12px 16px">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
          <span class="csub">图表类型</span>
          <select v-model="chartType" data-testid="bi-analysis-chart-type" style="width: 120px">
            <option value="bar">柱状图</option>
            <option value="line">折线图</option>
            <option value="pie">饼图</option>
          </select>
        </div>
        <div v-html="chartSvg"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import { bi0SvgBars, bi0SvgLine, bi0SvgPie, type ChartPoint } from './query-chart'

const FALLBACK_IP = ['电竞一组', '体育二组']

const metricOptions = ref<{ id: number; metricCode: string; metricName: string }[]>([])
const ipNames = ref<string[]>([...FALLBACK_IP])
const selectedIds = ref<number[]>([])
const ipGroupName = ref('')
const dateStart = ref('2026-09-01')
const dateEnd = ref('2026-09-30')
const tab = ref<'DETAIL' | 'TREND'>('DETAIL')
const chartType = ref<'bar' | 'line' | 'pie'>('bar')
const loading = ref(false)
const ran = ref(false)
const analysisError = ref('')
const emptyReason = ref('当前日期下暂无分析数据')
const toast = ref('')
const resultRows = ref<Record<string, any>[]>([])
const series = ref<{ metricCode: string; ipGroupName?: string; points: { date: string; value: number; ipGroupName?: string }[] }[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(20)

const detailPoints = computed<ChartPoint[]>(() =>
  resultRows.value.map((row) => ({
    k: `${String(row.statDate || '').slice(5)} ${row.ipGroupName || row.metricName || ''}`.trim(),
    v: Number(row.value) || 0,
  })),
)

const chartSvg = computed(() => {
  const points = detailPoints.value
  if (!points.length) return ''
  if (chartType.value === 'pie') return bi0SvgPie(points)
  if (chartType.value === 'line') return bi0SvgLine(points)
  return bi0SvgBars(points)
})

async function loadMetrics() {
  const res = await http.get('/bi/metric/list', { params: { status: 'ENABLED', pageNo: 1, pageSize: 50 } })
  if (res.data?.code === 0) {
    metricOptions.value = res.data.data.list || []
  }
}

async function loadIpGroups() {
  try {
    const res = await http.get('/ip-group/list', { params: { pageNo: 1, pageSize: 200 } })
    const names = ((res.data?.data?.list || []) as { groupName?: string }[])
      .map((row) => String(row.groupName || '').trim())
      .filter(Boolean)
    const merged = [...FALLBACK_IP]
    for (const name of names) {
      if (!merged.includes(name)) merged.push(name)
    }
    ipNames.value = merged
  } catch {
    ipNames.value = [...FALLBACK_IP]
  }
}

async function runAnalysis() {
  const ids = selectedIds.value.map(Number).filter(Boolean)
  analysisError.value = ''
  toast.value = ''
  if (!ids.length) {
    analysisError.value = '请至少选择一个指标'
    return
  }
  const from = dateStart.value
  const to = dateEnd.value
  if ((from && !to) || (!from && to)) {
    analysisError.value = '请同时填写开始和结束日期'
    return
  }
  if (from && to && from > to) {
    analysisError.value = '开始日期不能晚于结束日期'
    return
  }
  loading.value = true
  ran.value = true
  try {
    const res = await http.post('/bi/metric/analysis/run', {
      metricIds: ids,
      ipGroupName: ipGroupName.value,
      dateStart: from,
      dateEnd: to,
      view: tab.value,
      pageNo: 1,
      pageSize: 20,
    })
    resultRows.value = res.data.data.rows || []
    series.value = res.data.data.series || []
    total.value = Number(res.data.data.total || resultRows.value.length)
    pageNo.value = Number(res.data.data.pageNo || 1)
    pageSize.value = Number(res.data.data.pageSize || 20)
    emptyReason.value = String(res.data.data.emptyReason || '当前日期下暂无分析数据')
  } catch (error: unknown) {
    resultRows.value = []
    series.value = []
    total.value = 0
    analysisError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  selectedIds.value = []
  ipGroupName.value = ''
  dateStart.value = '2026-09-01'
  dateEnd.value = '2026-09-30'
  resultRows.value = []
  series.value = []
  total.value = 0
  ran.value = false
  analysisError.value = ''
  tab.value = 'DETAIL'
  chartType.value = 'bar'
  toast.value = '已重置'
}

function exportCsv() {
  if (!ran.value || !resultRows.value.length) {
    toast.value = '请先运行分析再导出'
    return
  }
  const lines = ['统计日期,IP组,指标名称,指标值']
  for (const row of resultRows.value) {
    lines.push([row.statDate, row.ipGroupName, row.metricName, row.value].map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '指标分析.csv'
  link.click()
  URL.revokeObjectURL(url)
  toast.value = `已导出 ${resultRows.value.length} 条`
}

onMounted(() => {
  loadMetrics()
  loadIpGroups()
})
</script>
