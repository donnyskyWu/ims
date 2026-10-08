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
        <select v-model="selectedIds" multiple style="min-width: 220px; min-height: 56px">
          <option v-for="m in metricOptions" :key="m.id" :value="m.id">{{ m.metricName }} ({{ m.metricCode }})</option>
        </select>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">IP 组 ID</span>
        <input v-model.number="ipGroupId" type="number" placeholder="可选" style="width: 100px" />
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-left: 8px">
        <span class="csub">统计日期</span>
        <input v-model="dateStart" placeholder="起" style="width: 110px" />
        <span>~</span>
        <input v-model="dateEnd" placeholder="止" style="width: 110px" />
      </div>
      <button class="btn btn-pri btn-sm" type="submit">运行分析</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetForm">重置</button>
    </form>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'DETAIL' }" @click="tab = 'DETAIL'">指标明细</div>
      <div class="tab" :class="{ on: tab === 'TREND' }" @click="tab = 'TREND'">指标趋势</div>
    </div>

    <div v-if="!resultRows.length && !loading" class="empty">
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
import { http } from '../../api/http'

const metricOptions = ref<{ id: number; metricCode: string; metricName: string }[]>([])
const selectedIds = ref<number[]>([])
const ipGroupId = ref<number | undefined>()
const dateStart = ref('2026-09-01')
const dateEnd = ref('2026-09-30')
const tab = ref<'DETAIL' | 'TREND'>('DETAIL')
const loading = ref(false)
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
  if (!ids.length) {
    alert('请至少选择一个指标')
    return
  }
  loading.value = true
  note.value = ''
  try {
    const res = await http.post('/bi/metric/analysis/run', {
      metricIds: ids,
      ipGroupId: ipGroupId.value || null,
      dateStart: dateStart.value,
      dateEnd: dateEnd.value,
      view: tab.value,
    })
    if (res.data?.code !== 0) {
      alert(res.data?.msg || '分析失败')
      return
    }
    resultRows.value = res.data.data.rows || []
    series.value = res.data.data.series || []
    note.value = res.data.data.note || ''
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
}

onMounted(loadMetrics)
</script>
