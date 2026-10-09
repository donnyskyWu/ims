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
        <router-link class="btn btn-sec btn-sm" data-testid="bi-open-perf" to="/ims/bi/query/perf">查询性能</router-link>
        <router-link class="btn btn-sec btn-sm" data-testid="bi-workbench-link" to="/ims/workbench/messages?sourceModule=BI">工作台通知</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/list">← 返回列表</router-link>
      </div>
    </div>

    <div class="qbar" style="flex-wrap: wrap; gap: 8px">
      <b>{{ preview?.reportTitle || '运营日报' }}</b>
      <span class="chip">预览模式</span>
      <span class="sp"></span>
      <input v-model="filters.dateFrom" data-testid="bi-filter-from" type="date" />
      <span class="csub">至</span>
      <input v-model="filters.dateTo" data-testid="bi-filter-to" type="date" />
      <select v-model="filters.platform" data-testid="bi-filter-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="抖音">抖音</option>
        <option value="视频号">视频号</option>
        <option value="斗鱼">斗鱼</option>
        <option value="快手">快手</option>
      </select>
      <button class="btn btn-pri btn-sm" type="button" data-testid="bi-filter-run" @click="runPreview({ user: true })">查询</button>
      <span class="csub">超过 180 天转异步，超过 366 天终止</span>
    </div>
    <p v-if="filterRestored" class="hint" data-testid="bi-filter-restored">已恢复上次筛选</p>
    <p v-if="filterError" class="hint bad" data-testid="bi-filter-error">{{ filterError }}</p>

    <p v-if="preview" class="csub" style="margin-top: 8px">
      数据截至 {{ preview.dataAsOf }} · 耗时 {{ preview.queryCostMs }}ms ·
      {{ preview.cacheHit ? '缓存命中 ✓' : '未命中' }} · {{ preview.total }} 行 · {{ preview.dataset }}
    </p>

    <div
      v-if="widgetEmpty"
      class="empty"
      data-testid="bi-widget-empty"
      style="margin-top: 12px"
    >
      <div class="et">{{ widgetEmptyReason }}</div>
    </div>
    <div v-else-if="kpiCards.length" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px">
      <div v-for="k in kpiCards" :key="k.label" class="card" data-testid="bi-widget-kpi">
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
        <span data-testid="bi-crumb-sep"> ▸ </span>
      </template>
      <b data-testid="bi-drill-dimension" :data-dimension="currentKey">{{ currentLabel }}</b>
      <button
        v-if="crumbs.length"
        type="button"
        class="btn btn-txt btn-sm"
        data-testid="bi-drill-rollup"
        @click="rollUpOne"
      >
        返回上卷
      </button>
    </div>
    <div v-if="asyncCard" class="card" data-testid="bi-async-card" style="margin-top: 10px; padding: 12px">
      <b>异步任务 {{ asyncCard.taskId }}</b>
      <div class="csub">{{ asyncCard.message }}</div>
    </div>
    <p v-if="drillToast" class="hint bad" data-testid="bi-drill-toast">{{ drillToast }}</p>
    <p v-if="exportNote" class="hint" data-testid="bi-export-note">{{ exportNote }}</p>
    <p v-if="drillMeta" class="csub" data-testid="bi-drill-meta">{{ drillMeta }}</p>

    <div v-if="jump" class="card" data-testid="bi-cell-jump" style="margin-top: 10px; padding: 12px">
      <b>{{ jump.jumpType === 'MODULE_DETAIL' ? '来源模块详情' : '穿透查询' }}</b>
      <div class="csub mono">{{ jump.jumpUrl }}</div>
    </div>

    <div v-if="deniedEmpty" class="empty" data-testid="bi-denied-empty" style="margin-top: 12px">
      <div class="et">您无权查看该报表</div>
    </div>
    <div v-else-if="!tableRows.length && drillReady" class="empty" data-testid="bi-drill-empty" style="margin-top: 12px">
      <div class="et">{{ drillEmptyReason }}</div>
    </div>
    <div v-else-if="tableRows.length" class="tbl-block" style="margin-top: 12px">
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
import axios from 'axios'
import { computed, onMounted, reactive, ref } from 'vue'
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
const asyncCard = ref<{ taskId: string; message: string } | null>(null)
const exportNote = ref('')
const drillMeta = ref('')
const jump = ref<Jump | null>(null)
const filterRestored = ref(false)
const filterError = ref('')
const drillReady = ref(false)
const deniedEmpty = ref(false)
const drillEmptyReason = ref('当前层暂无下钻数据')
const FILTER_KEY = 'ims.bi.preview.filters'
const filters = reactive({
  dateFrom: '2026-09-01',
  dateTo: '2026-10-03',
  platform: '',
  reportId: route.query.reportId ? Number(route.query.reportId) : undefined,
})

const kpiCards = computed(() => {
  const raw = preview.value?.kpis
  return Array.isArray(raw) ? (raw as Array<{ label: string; value: string; delta: string }>) : []
})
const widgetEmpty = computed(() => Boolean(preview.value && preview.value.empty))
const widgetEmptyReason = computed(() => String(preview.value?.emptyReason || '当前筛选下暂无指标'))

function filterStorageKey() {
  return `${FILTER_KEY}:${filters.reportId ?? ''}`
}

function persistFilters() {
  sessionStorage.setItem(
    filterStorageKey(),
    JSON.stringify({
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
      platform: filters.platform,
    }),
  )
}

function restoreFilters() {
  const raw = sessionStorage.getItem(filterStorageKey())
  if (!raw) return false
  try {
    const saved = JSON.parse(raw) as { dateFrom?: string; dateTo?: string; platform?: string }
    if (typeof saved.dateFrom === 'string') filters.dateFrom = saved.dateFrom
    if (typeof saved.dateTo === 'string') filters.dateTo = saved.dateTo
    if (typeof saved.platform === 'string') filters.platform = saved.platform
    return true
  } catch {
    return false
  }
}

function rejected(error: unknown): { code: number; msg: string } | null {
  const direct = error as { code?: number; msg?: string }
  if (error && typeof error === 'object' && typeof direct.code === 'number') {
    return { code: direct.code, msg: direct.msg || '' }
  }
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { code?: number; msg?: string } | undefined
    if (data && typeof data.code === 'number') return { code: data.code, msg: data.msg || '' }
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

function queryFilter(): Record<string, string> {
  const ctx: Record<string, string> = {}
  if (filters.platform) ctx.PLATFORM = filters.platform
  if (filters.dateFrom) ctx.dateFrom = filters.dateFrom
  if (filters.dateTo) ctx.dateTo = filters.dateTo
  return ctx
}

async function runPreview(options?: { user?: boolean }) {
  if (options?.user) filterRestored.value = false
  filterError.value = ''
  deniedEmpty.value = false
  if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
    filterError.value = '开始日期不能晚于结束日期'
    persistFilters()
    return
  }
  persistFilters()
  crumbs.value = []
  jump.value = null
  drillToast.value = ''
  asyncCard.value = null
  exportNote.value = ''
  try {
    const res = await http.post('/bi/report/preview/run', {
      reportId: filters.reportId,
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
      platform: filters.platform,
      timeGrain: 'DAY',
    })
    const data = res.data.data
    if (data?.queryMode === 'ASYNC') {
      preview.value = null
      tableRows.value = []
      drillMeta.value = ''
      asyncCard.value = { taskId: String(data.taskId || ''), message: String(data.message || '') }
      filterContext.value = queryFilter()
      return
    }
    preview.value = data
  } catch (error: unknown) {
    const body = rejected(error)
    preview.value = null
    tableRows.value = []
    drillMeta.value = ''
    drillReady.value = false
    filterContext.value = queryFilter()
    if (body?.code === 1008) {
      deniedEmpty.value = true
      filterError.value = ''
      drillToast.value = ''
      return
    }
    const text = body ? `${body.code} ${body.msg}` : errorMessage(error)
    filterError.value = text
    drillToast.value = text
    return
  }
  const root = chain.value[0]?.dimensionKey || 'PLATFORM'
  await loadLevel([root], preview.value?.empty ? {} : queryFilter(), 'DOWN')
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
    if (data?.queryMode === 'ASYNC') {
      tableRows.value = []
      drillMeta.value = ''
      asyncCard.value = { taskId: String(data.taskId || ''), message: String(data.message || '') }
      filterContext.value = filter
      drillPath.value = path
      return true
    }
    asyncCard.value = null
    tableRows.value = data.rows || []
    drillReady.value = true
    deniedEmpty.value = false
    drillEmptyReason.value = String(data.emptyReason || '当前层暂无下钻数据')
    currentKey.value = data.dimensionKey || path[path.length - 1]
    currentLabel.value = data.dimensionLabel || currentLabel.value
    filterContext.value = filter
    drillPath.value = path
    drillMeta.value = `${currentLabel.value} · ${data.total ?? tableRows.value.length} 行 · 耗时 ${data.costMs}ms`
    return true
  } catch (error: unknown) {
    const body = rejected(error)
    if (body?.code === 1008) {
      deniedEmpty.value = true
      tableRows.value = []
      drillReady.value = false
      drillToast.value = ''
      return false
    }
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
  const filter = { ...queryFilter(), ...filterContext.value, [fromKey]: value }
  const ok = await loadLevel([...drillPath.value, next.dimensionKey], filter, 'DOWN')
  if (ok) crumbs.value = [...crumbs.value, { key: fromKey, label: fromLabel, value }]
}

async function rollUp(index: number) {
  const path = chain.value.slice(0, index + 1).map((item) => item.dimensionKey)
  const filter: Record<string, string> = { ...queryFilter() }
  crumbs.value.slice(0, index).forEach((item) => {
    filter[item.key] = item.value
  })
  const ok = await loadLevel(path, filter, 'UP')
  if (ok) crumbs.value = crumbs.value.slice(0, index)
}

function rollUpOne() {
  if (!crumbs.value.length) return
  rollUp(crumbs.value.length - 1)
}

function resetDrill() {
  runPreview({ user: true })
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
    if (data.queryMode === 'ASYNC') {
      asyncCard.value = { taskId: String(data.taskId || ''), message: String(data.message || '') }
      exportNote.value = String(data.message || '已转异步')
      return
    }
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
    const sample = tableRows.value[0]?.dimensionValue || (tableRows.value.length ? currentLabel.value : '表头')
    const ttl = Number(data.expiresIn ?? 60)
    const emptyNote = tableRows.value.length ? '' : ' · 当前层无数据，已导出表头'
    exportNote.value = `已导出 ${fileName} · ${currentLabel.value} · ${sample} · ${ttl} 秒内有效${emptyNote}`
  } catch (error: unknown) {
    const body = rejected(error)
    exportNote.value = ''
    drillToast.value =
      body?.code === 1002 ? '下载链接已过期，请重新导出' : body ? `${body.code} ${body.msg}` : errorMessage(error)
  }
}

onMounted(async () => {
  filterRestored.value = restoreFilters()
  await loadTree()
  await runPreview()
})
</script>
