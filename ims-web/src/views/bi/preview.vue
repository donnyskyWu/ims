<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预览与下钻</h1>
        <div class="sub">BI-002 · /ims/bi/report/preview · DrillDimension 六维</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-drill-reset" @click="resetDrill">重置路径</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-export-xlsx" @click="exportDrill('XLSX')">导出 XLSX</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-export-csv" @click="exportDrill('CSV')">导出 CSV</button>
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

    <div data-testid="bi-drill-path" class="hint" style="margin-top: 10px">
      <template v-for="(c, i) in crumbs" :key="c.key">
        <button type="button" class="btn btn-txt btn-sm" :data-testid="`bi-crumb-${c.key}`" @click="rollUp(i)">
          {{ c.label }} {{ c.value }}
        </button>
        <span> → </span>
      </template>
      <b data-testid="bi-drill-dimension" :data-dimension="currentKey">{{ currentLabel }}</b>
    </div>
    <p v-if="drillToast" class="hint bad" data-testid="bi-drill-toast">{{ drillToast }}</p>
    <p v-if="exportNote" class="hint" data-testid="bi-export-note">{{ exportNote }}</p>
    <p v-if="drillMeta" class="csub" data-testid="bi-drill-meta">{{ drillMeta }}</p>

    <div v-if="jump" class="card" data-testid="bi-cell-jump" style="margin-top: 10px; padding: 12px">
      <b>{{ jump.jumpType === 'MODULE_DETAIL' ? '来源模块详情' : '穿透查询' }}</b>
      <div class="csub mono">{{ jump.jumpUrl }}</div>
    </div>

    <div v-if="tableRows.length" class="tbl-block" style="margin-top: 12px">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ currentLabel }} · 点击下钻</th>
              <th>GMV</th>
              <th>订单数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in tableRows" :key="idx">
              <td
                data-testid="bi-drill-value"
                style="color: var(--blue); cursor: pointer; font-weight: 500"
                @click="drillDown(row)"
              >
                {{ row.dimensionValue }} ▾
              </td>
              <td
                data-testid="bi-metric-gmv"
                class="num"
                title="点击穿透到明细"
                style="cursor: pointer"
                @click="cellDrill(row)"
              >
                {{ formatMoney(row.gmv) }}
              </td>
              <td class="num">{{ row.orders }}</td>
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
import { errorMessage, http } from '../../api/http'

type Level = { level: number; dimensionKey: string; dimensionLabel: string }
type Tree = { treeName: string; levels: Level[] }
type DrillRow = { dimensionKey: string; dimensionValue: string; gmv: number; orders: number }
type Crumb = { key: string; label: string; value: string }
type Jump = { jumpType: string; jumpUrl: string }

const route = useRoute()
const preview = ref<Record<string, unknown> | null>(null)
const chain = ref<Level[]>([])
const crumbs = ref<Crumb[]>([])
const currentKey = ref('PLATFORM')
const currentLabel = ref('平台')
const drillPath = ref<string[]>(['PLATFORM'])
const filterContext = ref<Record<string, string>>({})
const tableRows = ref<DrillRow[]>([])
const drillToast = ref('')
const exportNote = ref('')
const drillMeta = ref('')
const jump = ref<Jump | null>(null)
const filters = reactive({
  dateFrom: '2026-09-01',
  dateTo: '2026-10-03',
  platform: '',
  reportId: route.query.reportId ? Number(route.query.reportId) : undefined,
})

function rejected(error: unknown): { code: number; msg: string } | null {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    if (typeof body.code === 'number') return { code: body.code, msg: body.msg || '' }
  }
  return null
}

function formatMoney(v: unknown) {
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v ?? '')
  return `¥${n.toLocaleString('zh-CN')}`
}

async function loadTree() {
  const res = await http.get('/bi/query/dimension-tree')
  const trees = (res.data.data?.trees || []) as Tree[]
  const six = trees.find((item) => item.treeName === '自助六维') || trees[0]
  chain.value = six?.levels || []
  if (chain.value.length) {
    currentKey.value = chain.value[0].dimensionKey
    currentLabel.value = chain.value[0].dimensionLabel
  }
}

async function runPreview() {
  crumbs.value = []
  jump.value = null
  drillToast.value = ''
  const res = await http.post('/bi/report/preview/run', {
    reportId: filters.reportId,
    dateFrom: filters.dateFrom,
    dateTo: filters.dateTo,
    platform: filters.platform,
    timeGrain: 'DAY',
  })
  if (res.data.code === 0) preview.value = res.data.data
  const root = chain.value[0]?.dimensionKey || 'PLATFORM'
  await loadLevel([root], {}, 'DOWN')
}

async function loadLevel(path: string[], filter: Record<string, string>, direction: 'DOWN' | 'UP') {
  drillToast.value = ''
  try {
    const res = await http.post('/bi/query/drill', {
      reportId: filters.reportId,
      drillPath: path,
      direction,
      filterContext: filter,
    })
    const data = res.data.data
    tableRows.value = data.rows || []
    currentKey.value = data.dimensionKey || path[path.length - 1]
    currentLabel.value = data.dimensionLabel || currentLabel.value
    filterContext.value = filter
    drillPath.value = path
    drillMeta.value = `${currentLabel.value} · ${data.total ?? tableRows.value.length} 行 · 耗时 ${data.costMs}ms`
    return true
  } catch (error: unknown) {
    const body = rejected(error)
    if (body?.code === 1195) {
      drillToast.value = `1195 ${body.msg || '已到达预定义层级末端或路径非法'}`
      return false
    }
    drillToast.value = body ? `${body.code} ${body.msg}` : errorMessage(error)
    return false
  }
}

async function drillDown(row: DrillRow) {
  const idx = chain.value.findIndex((item) => item.dimensionKey === currentKey.value)
  const value = String(row.dimensionValue || '')
  if (idx < 0 || idx >= chain.value.length - 1) {
    await loadLevel([...drillPath.value, 'EXTRA'], { ...filterContext.value, [currentKey.value]: value }, 'DOWN')
    return
  }
  const fromKey = currentKey.value
  const fromLabel = currentLabel.value
  const next = chain.value[idx + 1]
  const filter = { ...filterContext.value, [fromKey]: value }
  const ok = await loadLevel([...drillPath.value, next.dimensionKey], filter, 'DOWN')
  if (ok) crumbs.value = [...crumbs.value, { key: fromKey, label: fromLabel, value }]
}

async function rollUp(index: number) {
  const path = chain.value.slice(0, index + 1).map((item) => item.dimensionKey)
  const filter: Record<string, string> = {}
  crumbs.value.slice(0, index).forEach((item) => {
    filter[item.key] = item.value
  })
  const ok = await loadLevel(path, filter, 'UP')
  if (ok) crumbs.value = crumbs.value.slice(0, index)
}

function resetDrill() {
  runPreview()
}

async function cellDrill(row: DrillRow) {
  jump.value = null
  drillToast.value = ''
  if (!filters.reportId) {
    drillToast.value = '请从报表设计器进入后再穿透'
    return
  }
  try {
    const res = await http.post('/bi/query/cell-drill', {
      reportId: filters.reportId,
      cellDimensions: { ...filterContext.value, [currentKey.value]: row.dimensionValue },
      drillToDetail: true,
    })
    jump.value = res.data.data
  } catch (error: unknown) {
    const body = rejected(error)
    drillToast.value = body ? `${body.code} ${body.msg}` : errorMessage(error)
  }
}

async function exportDrill(format: 'XLSX' | 'CSV') {
  exportNote.value = ''
  try {
    const res = await http.get('/bi/query/export', {
      params: {
        reportId: filters.reportId,
        drillPath: drillPath.value.join(','),
        filterContext: JSON.stringify(filterContext.value),
        format,
      },
    })
    const data = res.data.data || {}
    const downloadUrl = String(data.downloadUrl || '')
    const fileName = String(data.fileName || `bi_drill.${format === 'CSV' ? 'csv' : 'xlsx'}`)
    if (!downloadUrl) return
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      let body: unknown = {}
      try {
        body = await fileRes.json()
      } catch {
        body = {}
      }
      throw body
    }
    const blob = await fileRes.blob()
    const anchor = document.createElement('a')
    anchor.href = URL.createObjectURL(blob)
    anchor.download = fileName
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(anchor.href)
    const sample = tableRows.value[0]?.dimensionValue || currentLabel.value
    exportNote.value = `已导出 ${fileName} · ${currentLabel.value} · ${sample}`
  } catch (error: unknown) {
    const body = rejected(error)
    exportNote.value = ''
    drillToast.value = body ? `${body.code} ${body.msg}` : errorMessage(error)
  }
}

onMounted(async () => {
  await loadTree()
  await runPreview()
})
</script>
