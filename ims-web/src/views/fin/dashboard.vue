<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润看板</h1>
        <div class="sub">FIN-004 · 按月汇总 · 平台 / 账号 / IP 组 / 达人 / 责任人 · #90</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="loadAll">
      <input v-model="statPeriod" data-testid="fin-dash-period" placeholder="yyyy-MM" style="width: 120px" />
      <select v-model="profitType" data-testid="fin-dash-profit-type" style="width: 120px">
        <option value="NET">净利润</option>
        <option value="GROSS">毛利</option>
        <option value="OPERATING">经营利润</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-dash-query" @click="loadAll">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-dash-export" @click="openExport">导出报表</button>
    </form>

    <p v-if="error" class="hint" data-testid="fin-dash-error" style="color: var(--red); margin: 8px 0">{{ error }}</p>
    <p v-if="exportMsg" class="hint" data-testid="fin-dash-export-msg" style="margin: 8px 0">{{ exportMsg }}</p>

    <div v-if="overview" class="g4" style="margin: 12px 0">
      <div class="card stat">
        <span class="l">GMV</span>
        <div class="n" data-testid="fin-dash-gmv">¥{{ fmt(overview.totalGmv) }}</div>
      </div>
      <div class="card stat">
        <span class="l">总成本</span>
        <div class="n" data-testid="fin-dash-cost">¥{{ fmt(overview.totalCost) }}</div>
      </div>
      <div class="card stat">
        <span class="l">{{ profitLabel }}</span>
        <div class="n" data-testid="fin-dash-profit">¥{{ fmt(overview.shownProfit) }}</div>
      </div>
      <div class="card stat">
        <span class="l">净利率</span>
        <div class="n" data-testid="fin-dash-rate">{{ overview.netProfitRate }}%</div>
        <div class="d" data-testid="fin-dash-sessions">场次 {{ overview.sessionCount }}</div>
      </div>
    </div>
    <p v-if="overview" class="hint" data-testid="fin-dash-refreshed">缓存时间 {{ overview.refreshedAt }}</p>

    <div class="tabs" style="margin: 12px 0 8px">
      <button
        v-for="dim in dimensions"
        :key="dim.value"
        type="button"
        class="tab"
        :class="{ on: dimension === dim.value }"
        :data-testid="`fin-dash-dim-${dim.value}`"
        @click="switchDim(dim.value)"
      >
        {{ dim.label }}
      </button>
    </div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="fin-dash-drill">
          <thead>
            <tr>
              <th>维度</th>
              <th>GMV</th>
              <th>总成本</th>
              <th>净利润</th>
              <th>场次</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!drill.length">
              <td colspan="6"><div class="empty"><div class="et">本月暂无已核算场次</div></div></td>
            </tr>
            <template v-for="row in drill" :key="row.dimensionValue">
              <tr>
                <td>{{ row.dimensionLabel }}</td>
                <td class="num">¥{{ fmt(row.totalGmv) }}</td>
                <td class="num">¥{{ fmt(row.totalCost) }}</td>
                <td class="num">¥{{ fmt(row.netProfit) }}</td>
                <td class="num">{{ row.sessionCount }}</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="fin-dash-expand" @click="toggle(row.dimensionValue)">
                    场次
                  </button>
                </td>
              </tr>
              <tr
                v-for="child in expanded === row.dimensionValue ? row.children || [] : []"
                :key="child.sessionCode"
                data-testid="fin-dash-session"
              >
                <td class="mono">{{ child.sessionCode }}</td>
                <td class="num">¥{{ fmt(child.gmv) }}</td>
                <td class="num">¥{{ fmt(child.totalCost) }}</td>
                <td class="num" data-testid="fin-dash-session-net">¥{{ fmt(child.netProfit) }}</td>
                <td class="num">1</td>
                <td></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 14px">趋势</h2>
    <div class="tabs" data-testid="fin-dash-granularity" style="margin: 0 0 8px">
      <button
        v-for="item in grains"
        :key="item.value"
        type="button"
        class="tab"
        :class="{ on: granularity === item.value }"
        :data-testid="`fin-dash-grain-${item.value}`"
        @click="switchGrain(item.value)"
      >
        {{ item.label }}
      </button>
    </div>
    <div class="tbl-block">
      <table data-testid="fin-dash-trend">
        <thead>
          <tr>
            <th>周期</th>
            <th>GMV</th>
            <th>成本</th>
            <th>净利润</th>
            <th>环比</th>
            <th>同比</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!trend.length">
            <td colspan="6"><div class="empty"><div class="et">区间内无趋势</div></div></td>
          </tr>
          <tr v-for="point in trend" :key="point.statPeriod" data-testid="fin-dash-trend-row">
            <td>{{ point.periodLabel || point.statPeriod }}</td>
            <td class="num">¥{{ fmt(point.gmv) }}</td>
            <td class="num">¥{{ fmt(point.cost) }}</td>
            <td class="num">¥{{ fmt(point.netProfit) }}</td>
            <td>{{ point.momRate == null ? '—' : `${point.momRate}%` }}</td>
            <td>{{ point.yoyRate == null ? '—' : `${point.yoyRate}%` }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 14px">成本结构</h2>
    <div class="tbl-block">
      <table data-testid="fin-dash-cost-structure">
        <thead>
          <tr>
            <th>成本项</th>
            <th>金额</th>
            <th>占比</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in structure" :key="item.costItem">
            <td>{{ costLabel(item.costItem) }}</td>
            <td class="num">¥{{ fmt(item.amount) }}</td>
            <td class="num">{{ item.ratio }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 14px">分成汇总</h2>
    <div class="tbl-block">
      <table data-testid="fin-dash-share">
        <thead>
          <tr>
            <th>对象</th>
            <th>名称</th>
            <th>总额</th>
            <th>已发放</th>
            <th>待发放</th>
            <th>场次</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!shares.length">
            <td colspan="6"><div class="empty"><div class="et">本月无分成</div></div></td>
          </tr>
          <tr v-for="row in shares" :key="`${row.shareTarget}-${row.targetRefId}`">
            <td>{{ targetLabel(row.shareTarget) }}</td>
            <td>{{ row.targetRefName }}</td>
            <td class="num">¥{{ fmt(row.totalAmount) }}</td>
            <td class="num">¥{{ fmt(row.paidOffAmount) }}</td>
            <td class="num">¥{{ fmt(row.pendingAmount) }}</td>
            <td class="num">{{ row.sessionCount }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="exportOpen" class="modal-mask" data-testid="fin-dash-export-dialog">
      <div class="modal-card" role="dialog" aria-label="导出格式">
        <b>导出报表</b>
        <p class="hint" data-testid="fin-dash-export-scope">{{ statPeriod }} · {{ dimensionLabel }} · {{ profitLabel }}</p>
        <div class="fmt">
          <label>
            <input v-model="exportFormat" type="radio" value="XLSX" data-testid="fin-dash-export-xlsx" />
            Excel
          </label>
          <label>
            <input v-model="exportFormat" type="radio" value="PDF" data-testid="fin-dash-export-pdf" />
            PDF
          </label>
        </div>
        <div class="modal-acts">
          <button class="btn btn-sec btn-sm" type="button" :disabled="exportBusy" @click="exportOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-dash-export-confirm" :disabled="exportBusy" @click="confirmExport">
            下载
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Overview = {
  totalGmv: number
  totalCost: number
  shownProfit: number
  netProfitRate: number
  sessionCount: number
  refreshedAt: string
}
type DrillRow = {
  dimensionValue: string
  dimensionLabel: string
  totalGmv: number
  totalCost: number
  netProfit: number
  sessionCount: number
  children?: Array<{ sessionCode: string; gmv: number; totalCost: number; netProfit: number }>
}
type TrendPoint = {
  statPeriod: string
  periodLabel?: string
  gmv: number
  cost: number
  netProfit: number
  momRate?: number | null
  yoyRate?: number | null
}
type CostItem = { costItem: string; amount: number; ratio: number }
type ShareItem = {
  shareTarget: string
  targetRefId: number
  targetRefName: string
  totalAmount: number
  paidOffAmount: number
  pendingAmount: number
  sessionCount: number
}

const dimensions = [
  { value: 'PLATFORM', label: '平台' },
  { value: 'ACCOUNT', label: '账号' },
  { value: 'IP_GROUP', label: 'IP组' },
  { value: 'DAREN', label: '达人' },
  { value: 'OWNER', label: '责任人' },
]
const grains = [
  { value: 'DAY', label: '日' },
  { value: 'WEEK', label: '周' },
  { value: 'MONTH', label: '月' },
]

const statPeriod = ref(currentMonth())
const profitType = ref('NET')
const dimension = ref('ACCOUNT')
const granularity = ref('MONTH')
const error = ref('')
const exportMsg = ref('')
const exportOpen = ref(false)
const exportFormat = ref<'XLSX' | 'PDF'>('XLSX')
const exportBusy = ref(false)
const overview = ref<Overview | null>(null)
const drill = ref<DrillRow[]>([])
const trend = ref<TrendPoint[]>([])
const structure = ref<CostItem[]>([])
const shares = ref<ShareItem[]>([])
const expanded = ref('')

const profitLabel = computed(() => {
  const map: Record<string, string> = { NET: '净利润', GROSS: '毛利', OPERATING: '经营利润' }
  return map[profitType.value] || '净利润'
})
const dimensionLabel = computed(() => dimensions.find((item) => item.value === dimension.value)?.label || dimension.value)

function currentMonth() {
  const now = new Date(Date.now() + 8 * 3600 * 1000)
  const month = String(now.getUTCMonth() + 1).padStart(2, '0')
  return `${now.getUTCFullYear()}-${month}`
}

function monthBounds(period: string) {
  const [year, month] = period.split('-').map((part) => Number(part))
  const last = new Date(year, month, 0).getDate()
  const mm = String(month).padStart(2, '0')
  return `${year}-${mm}-01,${year}-${mm}-${String(last).padStart(2, '0')}`
}

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function costLabel(code: string) {
  const map: Record<string, string> = {
    COMMISSION: '平台佣金',
    AD: '投放成本',
    RECHARGE: '冲话费摊销',
    FIXED: '固定成本',
    SAMPLE: '样品成本',
    SHARE_DAREN: '达人分成',
    SHARE_REALNAME: '实名人分成',
  }
  return map[code] || code
}

function targetLabel(value: string) {
  const map: Record<string, string> = { DAREN: '达人', REALNAME: '实名人', TEAM: '团队' }
  return map[value] || value
}

function toggle(value: string) {
  expanded.value = expanded.value === value ? '' : value
}

async function switchDim(value: string) {
  dimension.value = value
  expanded.value = ''
  await loadDrill()
}

async function switchGrain(value: string) {
  granularity.value = value
  await loadTrend()
}

async function loadTrend() {
  const trendRes = await http.get('/fin/dashboard/trend', {
    params: {
      dateRange: monthBounds(statPeriod.value),
      granularity: granularity.value,
      profitType: profitType.value,
    },
  })
  trend.value = trendRes.data?.data || []
}

async function loadDrill() {
  const res = await http.get('/fin/dashboard/drilldown', {
    params: {
      statPeriod: statPeriod.value,
      dimensionType: dimension.value,
      profitType: profitType.value,
      drillToSession: true,
    },
  })
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '下钻失败'
    drill.value = []
    return
  }
  drill.value = res.data.data || []
}

async function loadAll() {
  error.value = ''
  exportMsg.value = ''
  expanded.value = ''
  const period = statPeriod.value
  const [overviewRes, structureRes, shareRes, trendRes] = await Promise.all([
    http.get('/fin/dashboard/overview', { params: { statPeriod: period, profitType: profitType.value } }),
    http.get('/fin/dashboard/cost-structure', { params: { statPeriod: period } }),
    http.get('/fin/dashboard/share-summary', { params: { statPeriod: period } }),
    http.get('/fin/dashboard/trend', {
      params: { dateRange: monthBounds(period), granularity: granularity.value, profitType: profitType.value },
    }),
  ])
  if (overviewRes.data?.code !== 0) {
    error.value = overviewRes.data?.msg || '总览失败'
    overview.value = null
  } else {
    overview.value = overviewRes.data.data
  }
  structure.value = structureRes.data?.code === 0 ? structureRes.data.data || [] : []
  shares.value = shareRes.data?.code === 0 ? shareRes.data.data || [] : []
  trend.value = trendRes.data?.code === 0 ? trendRes.data.data || [] : []
  await loadDrill()
}

function openExport() {
  exportFormat.value = 'XLSX'
  exportOpen.value = true
}

async function confirmExport() {
  if (exportBusy.value) return
  exportBusy.value = true
  exportMsg.value = ''
  const format = exportFormat.value
  try {
    const res = await http.get('/fin/dashboard/export', {
      params: { statPeriod: statPeriod.value, dimensionType: dimension.value, format },
    })
    const downloadUrl = String(res.data.data?.downloadUrl || '')
    const fileName = String(res.data.data?.fileName || '')
    const token = new URL(downloadUrl, 'http://127.0.0.1').searchParams.get('token') || ''
    const file = await http.get('/fin/dashboard/export/file', { params: { token }, responseType: 'blob' })
    const type = String(file.headers?.['content-type'] || '')
    const ready = format === 'PDF' ? type.includes('pdf') : type.includes('sheet')
    if (!ready) {
      exportMsg.value = '导出失败'
      return
    }
    const blob = file.data as Blob
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName || `fin_dashboard.${format === 'PDF' ? 'pdf' : 'xlsx'}`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    exportMsg.value = `导出成功 ${fileName}`
    exportOpen.value = false
  } catch (err) {
    exportMsg.value = errorMessage(err)
  } finally {
    exportBusy.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-card {
  width: 360px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.modal-card p {
  margin: 10px 0;
}
.fmt {
  display: flex;
  gap: 16px;
  margin: 8px 0 14px;
}
.modal-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
