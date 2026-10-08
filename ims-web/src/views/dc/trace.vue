<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>穿透查询</h1>
        <div class="sub">DC-001 · /ims/dc/trace · GET/POST /dc/trace/* · 12 DC</div>
      </div>
    </div>
    <div class="hint" style="margin-bottom: 10px" data-testid="dc-trace-meta">
      <span v-if="dataAsOf">数据截至 <b>{{ dataAsOf }}</b> · </span>
      <span
        data-testid="dc-trace-query-cost"
        :style="queryCostMs > 3000 ? { color: 'var(--orange)', fontWeight: '600' } : undefined"
      >queryCostMs {{ queried ? queryCostMs : '—' }} ms</span>
      ·
      <span
        data-testid="dc-trace-timeout-hint"
        :data-degraded="timeoutDegraded ? '1' : '0'"
        :style="timeoutDegraded ? { color: 'var(--orange)', fontWeight: '600' } : undefined"
      >{{ timeoutHint }}</span>
    </div>
    <form class="qbar" @submit.prevent="onSubmit">
      <select v-model="entryType" style="width: 120px">
        <option value="ACCOUNT">账号</option>
        <option value="SESSION">场次</option>
        <option value="PERSON">实名人</option>
      </select>
      <input
        v-model="keyword"
        placeholder="关键词"
        style="width: 160px"
        data-testid="dc-trace-keyword"
      />
      <input v-model="dateFrom" type="date" data-testid="dc-trace-date-from" />
      <input v-model="dateTo" type="date" data-testid="dc-trace-date-to" />
      <button class="btn btn-sec btn-sm" type="button" data-testid="dc-trace-search-entry" @click="searchEntry">
        搜入口
      </button>
      <span class="sp"></span>
      <select v-model="exportFormat" style="width: 88px" data-testid="dc-trace-export-format">
        <option value="XLSX">XLSX</option>
        <option value="PDF">PDF</option>
      </select>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="dc-trace-export"
        :disabled="!selectedEntry"
        @click="exportReport"
      >
        导出链路报告
      </button>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-trace-submit">穿透查询</button>
    </form>
    <p v-if="exportNote" class="hint" data-testid="dc-trace-export-note">{{ exportNote }}</p>
    <div v-if="entries.length" class="hint" style="margin: 8px 0">
      入口：
      <button
        v-for="e in entries"
        :key="e.entryId"
        type="button"
        class="btn btn-sec btn-sm"
        style="margin-right: 6px"
        @click="pickEntry(e)"
      >
        {{ e.entryLabel }}
      </button>
    </div>
    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>
    <div class="g2" style="margin-top: 12px">
      <div class="card" style="padding: 12px; min-height: 200px" data-testid="dc-trace-graph">
        <b style="font-size: 13px">关系图</b>
        <ul style="margin: 10px 0 0; padding-left: 18px; font-size: 12px">
          <li v-for="n in nodes" :key="n.nodeType + ':' + n.nodeId">
            {{ n.nodeType }} ·
            <button
              v-if="n.nodeType === 'SESSION'"
              type="button"
              class="btn btn-sec btn-sm"
              @click="openSession(n.nodeId)"
            >
              {{ n.nodeLabel }}
            </button>
            <template v-else>{{ n.nodeLabel }}</template>
          </li>
        </ul>
        <p v-if="!nodes.length" class="csub">选择入口后查询</p>
      </div>
      <div class="tbl-block" data-testid="dc-trace-detail-table">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>场次</th>
                <th>平台</th>
                <th>账号</th>
                <th>实名人</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in details" :key="d.sessionCode">
                <td class="mono">
                  <button
                    type="button"
                    class="btn btn-sec btn-sm"
                    data-testid="dc-trace-session-open"
                    :data-session-code="d.sessionCode"
                    @click="openSession(d.sessionCode)"
                  >
                    {{ d.sessionCode }}
                  </button>
                </td>
                <td>{{ d.platform }}</td>
                <td>{{ d.accountNo }}</td>
                <td>{{ d.realnameName }}</td>
              </tr>
              <tr v-if="!details.length">
                <td colspan="4"><div class="empty"><div class="et">暂无明细</div></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="drawerOpen" class="mask on" @click="drawerOpen = false"></div>
    <div
      v-if="drawerOpen && sessionDetail"
      class="drawer on"
      data-testid="dc-trace-session-drawer"
      style="width: 880px"
    >
      <div class="drawer-h">
        <b>场次明细 · {{ sessionDetail.sessionCode }}</b>
        <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
      </div>
      <div class="drawer-b">
        <p class="hint">
          {{ sessionDetail.sessionTitle }} · {{ sessionDetail.platform }} · 数据截至 {{ sessionDetail.dataAsOf }}
        </p>
        <div class="g2" style="margin: 12px 0">
          <div class="card stat">
            <span class="l">GMV</span>
            <div class="n">¥{{ fmt(sessionDetail.liveData?.gmv) }}</div>
          </div>
          <div class="card stat">
            <span class="l">净利润</span>
            <div class="n">{{ moneyOrDash(sessionDetail.profit?.netProfit) }}</div>
          </div>
        </div>
        <ul class="hint" style="line-height: 1.8; margin-bottom: 12px">
          <li>退款：¥{{ fmt(sessionDetail.liveData?.refund) }}</li>
          <li>UV：{{ sessionDetail.liveData?.uv ?? '—' }}</li>
          <li>时长：{{ sessionDetail.liveData?.durationMinutes ?? '—' }} 分钟</li>
          <li>毛利：{{ moneyOrDash(sessionDetail.profit?.grossProfit) }}</li>
          <li>经营利润：{{ moneyOrDash(sessionDetail.profit?.operatingProfit) }}</li>
          <li>净利率：{{ sessionDetail.profit?.netProfitRate == null ? '—' : sessionDetail.profit.netProfitRate + '%' }}</li>
          <li>计算版本：v{{ sessionDetail.profit?.calcVersion ?? 0 }}</li>
          <li>账号：{{ sessionDetail.account?.accountNo || '—' }}</li>
        </ul>
        <h3 style="font-size: 14px; margin-bottom: 6px">成本明细</h3>
        <table>
          <thead><tr><th>项目</th><th>金额</th></tr></thead>
          <tbody>
            <tr v-for="item in sessionDetail.costDetail || []" :key="item.costItem">
              <td>{{ item.costItemLabel || item.costItem }}</td>
              <td class="num">{{ item.amount == null ? '—' : '¥' + fmt(item.amount) }}</td>
            </tr>
            <tr v-if="!(sessionDetail.costDetail || []).length">
              <td colspan="2">暂无成本</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http } from '../../api/http'

type Entry = { entryType: string; entryId: string; entryLabel: string }
type Node = { nodeType: string; nodeId: string; nodeLabel: string }
type Detail = { sessionCode: string; platform: string; accountNo: string; realnameName: string }
type CostItem = { costItem: string; costItemLabel?: string; amount: number | null }
type SessionDetail = {
  sessionCode: string
  sessionTitle?: string
  platform?: string
  dataAsOf?: string
  liveData?: { gmv?: number; refund?: number; uv?: number | null; durationMinutes?: number | null }
  profit?: {
    grossProfit?: number | null
    operatingProfit?: number | null
    netProfit?: number | null
    netProfitRate?: number | null
    calcVersion?: number
  }
  costDetail?: CostItem[]
  account?: { accountNo?: string }
}
type TracePayload = {
  queryCostMs?: number
  dataAsOf?: string
  nodes?: Node[]
  detailList?: { list?: Detail[] }
}
type ApiFail = { code?: number; msg?: string; data?: TracePayload }

const keyword = ref('')
const entryType = ref('ACCOUNT')
const dateFrom = ref('')
const dateTo = ref('')
const exportFormat = ref<'XLSX' | 'PDF'>('XLSX')
const selectedEntry = ref<Entry | null>(null)
const entries = ref<Entry[]>([])
const nodes = ref<Node[]>([])
const details = ref<Detail[]>([])
const dataAsOf = ref('')
const queryCostMs = ref(0)
const queried = ref(false)
const timeoutDegraded = ref(false)
const error = ref('')
const exportNote = ref('')
const drawerOpen = ref(false)
const sessionDetail = ref<SessionDetail | null>(null)

const timeoutHint = computed(() =>
  timeoutDegraded.value ? '1181 穿透查询超时降级，请缩小日期范围' : '超时降级 1181',
)

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function moneyOrDash(n: number | null | undefined) {
  return n == null ? '—' : '¥' + fmt(n)
}

function asApiFail(err: unknown): ApiFail | null {
  if (err && typeof err === 'object' && 'code' in err) return err as ApiFail
  return null
}

function dateRange(): string[] | undefined {
  if (dateFrom.value && dateTo.value) return [dateFrom.value, dateTo.value]
  return undefined
}

function applyResult(data: TracePayload | undefined, degraded: boolean) {
  nodes.value = degraded ? [] : data?.nodes || []
  details.value = degraded ? [] : data?.detailList?.list || []
  dataAsOf.value = data?.dataAsOf || ''
  queryCostMs.value = data?.queryCostMs ?? 0
  queried.value = true
  timeoutDegraded.value = degraded || queryCostMs.value > 3000
}

async function searchEntry() {
  error.value = ''
  try {
    const res = await http.get('/dc/trace/entry', {
      params: { keyword: keyword.value, entryType: entryType.value, limit: 8 },
    })
    entries.value = res.data.data || []
    if (entries.value.length === 1) pickEntry(entries.value[0])
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '网络错误'
  }
}

function pickEntry(e: Entry) {
  selectedEntry.value = e
  runQuery()
}

async function onSubmit() {
  if (selectedEntry.value) {
    await runQuery()
    return
  }
  await searchEntry()
}

async function runQuery() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  exportNote.value = ''
  try {
    const res = await http.post('/dc/trace/query', {
      entryType: selectedEntry.value.entryType,
      entryId: selectedEntry.value.entryId,
      mode: 'DETAIL',
      pageNo: 1,
      pageSize: 10,
      dateRange: dateRange(),
    })
    applyResult(res.data.data, false)
  } catch (err) {
    const fail = asApiFail(err)
    if (fail?.code === 1181) {
      applyResult(fail.data, true)
      return
    }
    error.value = fail?.msg || '网络错误'
  }
}

async function openSession(sessionCode: string) {
  error.value = ''
  try {
    const res = await http.get(`/dc/trace/detail/${encodeURIComponent(sessionCode)}`, { timeout: 60_000 })
    sessionDetail.value = res.data.data
    drawerOpen.value = true
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '场次明细加载失败'
  }
}

async function exportReport() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  exportNote.value = ''
  try {
    const res = await http.get('/dc/trace/export', {
      params: {
        entryType: selectedEntry.value.entryType,
        entryId: selectedEntry.value.entryId,
        format: exportFormat.value,
      },
    })
    const downloadUrl = res.data.data?.downloadUrl as string
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      error.value = `导出失败（${fileRes.status}）`
      return
    }
    const blob = await fileRes.blob()
    const ext = exportFormat.value === 'PDF' ? 'pdf' : 'xlsx'
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `dc_trace_report.${ext}`
    a.click()
    URL.revokeObjectURL(a.href)
    exportNote.value = `已导出 ${exportFormat.value}`
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '导出失败'
  }
}
</script>
