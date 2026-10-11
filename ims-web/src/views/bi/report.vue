<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表中心</h1>
        <div class="sub">M6 八张标准报表 · 统一筛选条 · /ims/bi/report</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-report-reset" @click="resetFilters">重置</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-report-export-xlsx" @click="exportExcel">导出 Excel</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-report-export-pdf" @click="exportPdf">导出 PDF</button>
      </div>
    </div>

    <div class="qbar" style="flex-wrap: wrap; gap: 8px">
      <span class="csub">IP 组</span>
      <select v-model="ipGroupId" data-testid="bi-report-ip" style="width: 140px">
        <option value="">全部 IP 组</option>
        <option v-for="group in ipGroups" :key="group.id" :value="String(group.id)">{{ group.name }}</option>
      </select>
      <span class="csub">平台</span>
      <select v-model="platform" data-testid="bi-report-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="WECHAT_CHANNELS">视频号</option>
        <option value="KUAISHOU">快手</option>
        <option value="DOUYU">斗鱼</option>
      </select>
      <input v-model="dateFrom" data-testid="bi-report-from" type="date" />
      <span class="csub">至</span>
      <input v-model="dateTo" data-testid="bi-report-to" type="date" />
      <span class="csub">时间维度</span>
      <select v-model="timeGrain" data-testid="bi-report-grain" style="width: 100px">
        <option value="DAY">日</option>
        <option value="WEEK">周</option>
        <option value="MONTH">月</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="bi-report-run" @click="reloadPreview">查询</button>
    </div>
    <p v-if="resetNote" class="hint" data-testid="bi-report-reset-note">{{ resetNote }}</p>
    <p v-if="reportError" class="hint bad" data-testid="bi-report-error">{{ reportError }}</p>

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-top: 14px">
      <div
        v-for="item in reports"
        :key="item.code"
        class="card hov"
        style="cursor: pointer"
        :data-testid="`bi-report-card-${item.code}`"
        :style="{ outline: selected?.code === item.code ? '2px solid var(--blue)' : '' }"
        @click="selectReport(item)"
      >
        <b>{{ item.title }}</b>
        <div class="csub" style="margin-top: 8px">{{ item.desc }}</div>
        <div class="rowline" style="margin-top: 10px; gap: 6px; flex-wrap: wrap">
          <span v-for="tag in item.tags" :key="tag" class="tag tag-info">{{ tag }}</span>
        </div>
      </div>
    </div>

    <div v-if="preview" class="card" style="margin-top: 16px" data-testid="bi-report-result">
      <div class="bi0-result-hd"><b>{{ preview.title }}</b> · {{ preview.total }} 行 · {{ preview.dataAsOf }}</div>
      <div v-if="preview.kpis?.length" data-testid="bi-report-kpi" style="display: flex; gap: 12px; margin-top: 10px">
        <div v-for="kpi in preview.kpis" :key="kpi.metric" class="card" style="padding: 10px; min-width: 140px">
          <div class="csub">{{ kpi.metric }}</div>
          <b>{{ kpi.value }}</b>
          <div class="csub">{{ kpi.note }}</div>
        </div>
      </div>
      <svg v-if="preview.trend?.length" data-testid="bi-report-trend" width="420" height="88" style="margin-top: 8px">
        <polyline fill="none" stroke="#0071e3" stroke-width="2" :points="trendPoints(preview.trend)" />
      </svg>
      <p v-if="preview.filterNote" class="hint" data-testid="bi-report-filter-note">{{ preview.filterNote }}</p>
      <div v-if="preview.empty" class="empty" data-testid="bi-report-empty">
        <div class="et">{{ preview.emptyReason || '当前筛选下暂无数据' }}</div>
      </div>
      <div v-else class="tbl-wrap" style="margin-top: 8px">
        <table>
          <thead>
            <tr>
              <th v-for="c in preview.columns" :key="c">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in preview.rows" :key="idx" data-testid="bi-report-row">
              <td v-for="c in preview.columns" :key="c">{{ row[c] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type ReportCard = { code: string; title: string; desc: string; tags: string[] }
type Preview = {
  title: string
  columns: string[]
  rows: Record<string, unknown>[]
  total: number
  dataAsOf: string
  kpis?: { metric: string; value: number; note: string }[]
  trend?: { label: string; value: number }[]
  empty?: boolean
  emptyReason?: string
  filterNote?: string
}

type IpGroup = { id: number; name: string }

const reports = ref<ReportCard[]>([])
const selected = ref<ReportCard | null>(null)
const preview = ref<Preview | null>(null)
const platform = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const ipGroupId = ref('')
const timeGrain = ref('DAY')
const ipGroups = ref<IpGroup[]>([])
const reportError = ref('')
const resetNote = ref('')

function trendPoints(trend: { label: string; value: number }[]) {
  const width = 400
  const max = Math.max(...trend.map((item) => Number(item.value) || 0), 1)
  return trend
    .map((item, index) => {
      const x = trend.length === 1 ? width / 2 : (index / (trend.length - 1)) * (width - 8) + 4
      const y = 76 - (Number(item.value) / max) * 64
      return `${x},${y}`
    })
    .join(' ')
}

function resetFilters() {
  platform.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  ipGroupId.value = ''
  timeGrain.value = 'DAY'
  resetNote.value = '已重置'
  reportError.value = ''
  void reloadPreview()
}

function downloadBlob(filename: string, blob: Blob) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

function exportExcel() {
  const view = preview.value
  if (!view) return
  const head = (view.columns || []).map((col) => `<th>${col}</th>`).join('')
  const body = (view.rows || [])
    .map((row) => `<tr>${(view.columns || []).map((col) => `<td>${row[col] ?? ''}</td>`).join('')}</tr>`)
    .join('')
  const html = `<html><head><meta charset="utf-8"></head><body><table><tr>${head}</tr>${body}</table></body></html>`
  downloadBlob(`${view.title || 'report'}.xls`, new Blob([html], { type: 'application/vnd.ms-excel' }))
}

function exportPdf() {
  const view = preview.value
  if (!view) return
  const title = (view.title || 'report').replace(/[()\\]/g, ' ')
  const stream = `BT /F1 18 Tf 40 80 Td (${title}) Tj ET`
  const pdf = `%PDF-1.1\n1 0 obj<<>>endobj\n2 0 obj<</Length ${stream.length}>>stream\n${stream}\nendstream\nendobj\n3 0 obj<</Type/Page/Parent 4 0 R/Contents 2 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n4 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n6 0 obj<</Type/Catalog/Pages 4 0 R>>endobj\nxref\n0 7\n0000000000 65535 f \ntrailer<</Size 7/Root 6 0 R>>\nstartxref\n0\n%%EOF`
  downloadBlob(`${view.title || 'report'}.pdf`, new Blob([pdf], { type: 'application/pdf' }))
}

async function loadIpGroups() {
  try {
    const res = await http.get('/ip-group/list', { params: { pageNo: 1, pageSize: 50 } })
    const list = (res.data.data?.list || res.data.data?.records || []) as { id: number; groupName?: string; name?: string }[]
    ipGroups.value = list.map((item) => ({ id: item.id, name: item.groupName || item.name || `IP组${item.id}` }))
  } catch {
    ipGroups.value = []
  }
}

async function loadCatalog() {
  const res = await http.get('/bi/report/catalog')
  if (res.data.code === 0) {
    reports.value = res.data.data.reports || []
    if (reports.value.length && !selected.value) {
      selected.value = reports.value[0]
      await reloadPreview()
    }
  }
}

async function selectReport(item: ReportCard) {
  selected.value = item
  await reloadPreview()
}

async function reloadPreview() {
  if (!selected.value) return
  reportError.value = ''
  const from = dateFrom.value
  const to = dateTo.value
  if ((from && !to) || (!from && to)) {
    reportError.value = '请同时填写开始和结束日期'
    return
  }
  if (from && to && from > to) {
    reportError.value = '开始日期不能晚于结束日期'
    return
  }
  try {
    const res = await http.get(`/bi/report/${selected.value.code}`, {
      params: {
        platform: platform.value || undefined,
        dateFrom: from || undefined,
        dateTo: to || undefined,
        ipGroupId: ipGroupId.value || undefined,
        timeGrain: timeGrain.value || 'DAY',
      },
    })
    if (res.data.code === 0) preview.value = res.data.data
  } catch (error: unknown) {
    const body = error as { code?: number; msg?: string }
    reportError.value = typeof body?.code === 'number' ? `${body.code} ${body.msg || ''}` : errorMessage(error)
  }
}

onMounted(() => {
  void loadIpGroups()
  void loadCatalog()
})
</script>
