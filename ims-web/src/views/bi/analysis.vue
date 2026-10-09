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

    <form class="qbar" @submit.prevent="runAnalysis">
      <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">
        <span class="csub">选择指标</span>
        <select v-model="selectedIds" data-testid="bi-analysis-metrics" multiple style="min-width: 220px; min-height: 56px">
          <option v-for="m in metricOptions" :key="m.id" :value="m.id">{{ m.metricName }} ({{ m.metricCode }})</option>
        </select>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">IP 组 ID</span>
        <input v-model.number="ipGroupId" type="number" placeholder="可选" style="width: 100px" />
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">统计日期</span>
        <input v-model="dateStart" data-testid="bi-analysis-from" type="date" style="width: 140px" />
        <span>~</span>
        <input v-model="dateEnd" data-testid="bi-analysis-to" type="date" style="width: 140px" />
      </div>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="bi-analysis-run">运行分析</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetForm">重置</button>
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
              <th>编码</th>
              <th>名称</th>
              <th>数值</th>
              <th>单位</th>
              <th>周期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in resultRows" :key="row.metricId">
              <td class="mono">{{ row.metricCode }}</td>
              <td style="font-weight: 500">{{ row.metricName }}</td>
              <td class="num">{{ row.value }}</td>
              <td>{{ row.unit }}</td>
              <td class="num" style="font-size: 12px">{{ row.dateStart }} ~ {{ row.dateEnd }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="series.length && tab === 'TREND'" class="tbl-block">
      <div v-for="s in series" :key="s.metricCode" class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div style="font-weight: 600; margin-bottom: 8px">{{ s.metricCode }}</div>
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>日期</th><th>值</th></tr></thead>
            <tbody>
              <tr v-for="p in s.points" :key="p.date">
                <td>{{ p.date }}</td>
                <td class="num">{{ p.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <p v-if="note" class="hint">{{ note }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

const metricOptions = ref<{ id: number; metricCode: string; metricName: string }[]>([])
const selectedIds = ref<number[]>([])
const ipGroupId = ref<number | undefined>()
const dateStart = ref('2026-09-01')
const dateEnd = ref('2026-09-30')
const tab = ref<'DETAIL' | 'TREND'>('DETAIL')
const loading = ref(false)
const ran = ref(false)
const analysisError = ref('')
const emptyReason = ref('当前日期下暂无分析数据')
const resultRows = ref<Record<string, unknown>[]>([])
const series = ref<{ metricCode: string; points: { date: string; value: number }[] }[]>([])
const note = ref('')

async function loadMetrics() {
  const res = await http.get('/bi/metric/list', { params: { status: 'ENABLED', pageNo: 1, pageSize: 50 } })
  if (res.data?.code === 0) {
    metricOptions.value = res.data.data.list || []
  }
}

async function runAnalysis() {
  const ids = selectedIds.value.map(Number).filter(Boolean)
  analysisError.value = ''
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
  note.value = ''
  ran.value = true
  try {
    const res = await http.post('/bi/metric/analysis/run', {
      metricIds: ids,
      ipGroupId: ipGroupId.value || null,
      dateStart: from,
      dateEnd: to,
      view: tab.value,
    })
    if (res.data?.code !== 0) {
      analysisError.value = res.data?.msg || '分析失败'
      resultRows.value = []
      series.value = []
      return
    }
    resultRows.value = res.data.data.rows || []
    series.value = res.data.data.series || []
    note.value = res.data.data.note || ''
    emptyReason.value = String(res.data.data.emptyReason || '当前日期下暂无分析数据')
  } catch (error: unknown) {
    resultRows.value = []
    series.value = []
    analysisError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  selectedIds.value = []
  ipGroupId.value = undefined
  resultRows.value = []
  series.value = []
  note.value = ''
  ran.value = false
  analysisError.value = ''
}

onMounted(loadMetrics)
</script>
