<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预览与下钻</h1>
        <div class="sub">BI-002 · /ims/bi/report/preview · 单元格穿透</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="resetDrill">重置路径</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/list">← 返回列表</router-link>
      </div>
    </div>

    <div class="qbar" style="flex-wrap: wrap; gap: 8px">
      <b>{{ preview?.reportTitle || '运营日报' }}</b>
      <span class="chip">预览模式</span>
      <span class="sp"></span>
      <input v-model="filters.dateFrom" type="date" />
      <span class="csub">至</span>
      <input v-model="filters.dateTo" type="date" />
      <select v-model="filters.platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="抖音">抖音</option>
        <option value="视频号">视频号</option>
        <option value="斗鱼">斗鱼</option>
        <option value="快手">快手</option>
      </select>
      <button class="btn btn-pri btn-sm" type="button" @click="runPreview">查询</button>
    </div>

    <p v-if="preview" class="csub" style="margin-top: 8px">
      数据截至 {{ preview.dataAsOf }} · 耗时 {{ preview.queryCostMs }}ms ·
      {{ preview.cacheHit ? '缓存命中 ✓' : '未命中' }} · {{ preview.total }} 行 · {{ preview.dataset }}
    </p>

    <div v-if="preview?.kpis" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px">
      <div v-for="k in preview.kpis" :key="k.label" class="card">
        <div style="font-size: 20px; font-weight: 600">{{ k.value }}</div>
        <div class="csub">{{ k.label }}</div>
        <div class="csub" style="color: var(--green)">{{ k.delta }}</div>
      </div>
    </div>

    <div v-if="drillPath.length" class="hint" style="margin-top: 10px">
      下钻路径：
      <span v-for="(p, i) in drillPath" :key="i">
        <span v-if="i"> → </span>{{ p }}
      </span>
    </div>

    <div v-if="preview" class="tbl-block" style="margin-top: 12px">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>维度 · 点击下钻</th>
              <th v-for="c in tableColumns" v-show="c !== 'platform'" :key="c">{{ c }}</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in tableRows" :key="idx">
              <td style="color: var(--blue); cursor: pointer; font-weight: 500" @click="drillRow(row)">
                {{ row.platform || row.account || row.sessionCode }} ▾
              </td>
              <td v-for="c in tableColumns" v-show="c !== 'platform' && c !== 'account' && c !== 'sessionCode'" :key="c" class="num">
                {{ formatCell(row[c]) }}
              </td>
              <td><span class="btn btn-sec btn-sm" @click="penetrate(row)">穿透</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'

const route = useRoute()
const preview = ref<Record<string, unknown> | null>(null)
const drillPath = ref<string[]>([])
const tableRows = ref<Record<string, unknown>[]>([])
const tableColumns = ref<string[]>([])
const filters = reactive({
  dateFrom: '2026-09-01',
  dateTo: '2026-10-03',
  platform: '',
  reportId: route.query.reportId ? Number(route.query.reportId) : undefined,
})

function formatCell(v: unknown) {
  if (typeof v === 'number' && v > 1000) return `¥${v.toLocaleString()}`
  return v
}

async function runPreview() {
  drillPath.value = []
  const res = await http.post('/bi/report/preview/run', {
    reportId: filters.reportId,
    dateFrom: filters.dateFrom,
    dateTo: filters.dateTo,
    platform: filters.platform,
    timeGrain: 'DAY',
  })
  if (res.data.code === 0) {
    preview.value = res.data.data
    tableRows.value = res.data.data.rows || []
    tableColumns.value = res.data.data.columns || []
  }
}

async function drillRow(row: Record<string, unknown>) {
  const dim = String(row.platform || row.account || '')
  if (!dim) return
  drillPath.value = [...drillPath.value, dim]
  const res = await http.post('/bi/report/preview/drill', {
    reportId: filters.reportId,
    dimension: 'platform',
    drillPath: drillPath.value,
    cellMetric: 'gmv',
  })
  if (res.data.code === 0) {
    tableRows.value = res.data.data.rows || []
    tableColumns.value = res.data.data.columns || []
  }
}

function resetDrill() {
  drillPath.value = []
  runPreview()
}

function penetrate(row: Record<string, unknown>) {
  window.open('/ims/dc/trace', '_blank')
  void row
}

onMounted(() => {
  runPreview()
})
</script>
