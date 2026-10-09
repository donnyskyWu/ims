<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润核算</h1>
        <div class="sub">FIN-002 · 利润列表 · 三级口径排序 · 11 FIN（场次财务，非账号 COST）</div>
      </div>
    </div>

    <div v-if="summary" class="g4" style="margin-bottom: 12px">
      <div class="card stat">
        <span class="l">已核算场次</span>
        <div class="n">{{ summary.sessionCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">总收入</span>
        <div class="n">¥{{ fmt(summary.totalRevenue) }}</div>
      </div>
      <div class="card stat">
        <span class="l">总成本</span>
        <div class="n">¥{{ fmt(summary.totalCost) }}</div>
      </div>
      <div class="card stat">
        <span class="l" data-testid="fin-profit-summary-label">{{ profitLabel }}合计</span>
        <div
          class="n"
          data-testid="fin-profit-summary-shown"
          :class="{ pos: shownProfit >= 0, neg: shownProfit < 0 }"
        >
          ¥{{ fmtSigned(shownProfit) }}
        </div>
        <div class="d">待结算 {{ summary.readySettlementCount }} · 结算中 {{ summary.inSettlementCount }}</div>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab on">利润列表</button>
    </div>

    <form class="qbar" @submit.prevent="reload">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 180px" />
      <input v-model="query.platform" placeholder="平台" style="width: 100px" />
      <input v-model="query.dateFrom" type="date" data-testid="fin-profit-date-from" aria-label="开始日期" />
      <input v-model="query.dateTo" type="date" data-testid="fin-profit-date-to" aria-label="结束日期" />
      <select v-model="query.calcStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="CALCULATED">已计算</option>
        <option value="RECALCULATED">已重算</option>
        <option value="PENDING">待计算</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="reload">查询</button>
    </form>

    <div class="tabs" data-testid="fin-profit-metric" role="radiogroup" aria-label="利润口径" style="margin: 8px 0">
      <button
        v-for="item in metrics"
        :key="item.value"
        type="button"
        class="tab"
        role="radio"
        :class="{ on: profitType === item.value }"
        :aria-checked="profitType === item.value"
        :data-testid="`fin-profit-metric-${item.value}`"
        @click="switchMetric(item.value)"
      >
        {{ item.label }}
      </button>
    </div>
    <p class="hint" data-testid="fin-profit-sort-hint" style="margin: 0 0 8px">
      按{{ profitLabel }}降序 · 毛利、经营利润、净利润三列同时展示
    </p>

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="fin-profit-table">
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>标题</th>
              <th>平台</th>
              <th>GMV</th>
              <th>
                <button type="button" class="btn btn-txt" data-testid="fin-profit-sort-GROSS" @click="switchMetric('GROSS')">
                  毛利<span v-if="profitType === 'GROSS'"> ↓</span>
                </button>
              </th>
              <th>
                <button type="button" class="btn btn-txt" data-testid="fin-profit-sort-OPERATING" @click="switchMetric('OPERATING')">
                  经营利润<span v-if="profitType === 'OPERATING'"> ↓</span>
                </button>
              </th>
              <th>
                <button type="button" class="btn btn-txt" data-testid="fin-profit-sort-NET" @click="switchMetric('NET')">
                  净利润<span v-if="profitType === 'NET'"> ↓</span>
                </button>
              </th>
              <th>净利率</th>
              <th>结算</th>
              <th>版本</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="11"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="11"><div class="empty"><div class="et">暂无利润数据（需先核准成本）</div></div></td>
            </tr>
            <tr
              v-for="row in rows"
              v-else
              :key="String(row.sessionCode)"
              data-testid="fin-profit-row"
              :data-session="row.sessionCode"
            >
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.sessionTitle }}</td>
              <td>{{ row.platform }}</td>
              <td class="num">¥{{ fmt(row.gmv) }}</td>
              <td class="num" data-testid="fin-profit-gross" :class="amtClass(row.grossProfit)">¥{{ fmtSigned(row.grossProfit) }}</td>
              <td class="num" data-testid="fin-profit-operating" :class="amtClass(row.operatingProfit)">¥{{ fmtSigned(row.operatingProfit) }}</td>
              <td class="num" data-testid="fin-profit-net" :class="amtClass(row.netProfit)">¥{{ fmtSigned(row.netProfit) }}</td>
              <td class="num">{{ row.netProfitRate }}%</td>
              <td>{{ settlementLabel(String(row.settlementStatus || '')) }}</td>
              <td>V{{ row.calcVersion }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(String(row.sessionCode))">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen && detail" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer" style="width: 640px">
        <div class="drawer-h">
          <b>利润详情 · {{ detail.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div class="g3" style="margin-bottom: 12px">
          <div class="card stat"><span class="l">毛利</span><div class="n" :class="amtClass(detail.grossProfit)">¥{{ fmtSigned(detail.grossProfit) }}</div></div>
          <div class="card stat"><span class="l">经营利润</span><div class="n" :class="amtClass(detail.operatingProfit)">¥{{ fmtSigned(detail.operatingProfit) }}</div></div>
          <div class="card stat"><span class="l">净利润</span><div class="n" :class="amtClass(detail.netProfit)">¥{{ fmtSigned(detail.netProfit) }}</div></div>
        </div>
        <p class="hint">{{ detail.calcRuleSnapshot?.formula }}</p>
        <pre class="mono" style="font-size: 12px; white-space: pre-wrap">{{ JSON.stringify(detail.calcRuleSnapshot?.params, null, 2) }}</pre>
        <p class="hint">计算时间：{{ detail.calculatedAt || '—' }} · 状态 {{ detail.calcStatus }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type ProfitMetric = 'GROSS' | 'OPERATING' | 'NET'

const metrics: { value: ProfitMetric; label: string }[] = [
  { value: 'GROSS', label: '毛利' },
  { value: 'OPERATING', label: '经营利润' },
  { value: 'NET', label: '净利润' },
]

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, any>[]>([])
const summary = ref<Record<string, any> | null>(null)
const drawerOpen = ref(false)
const detail = ref<Record<string, any> | null>(null)
const profitType = ref<ProfitMetric>('NET')
const query = reactive({ sessionCode: '', platform: '', calcStatus: '', dateFrom: '', dateTo: '' })

const profitLabel = computed(() => metrics.find((item) => item.value === profitType.value)?.label || '净利润')
const shownProfit = computed(() => Number(summary.value?.shownProfit ?? summary.value?.totalNetProfit ?? 0))

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtSigned(n: unknown) {
  const value = Number(n || 0)
  const text = Math.abs(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return value < 0 ? `(${text})` : text
}

function amtClass(n: unknown) {
  return Number(n || 0) < 0 ? 'neg' : 'pos'
}

function settlementLabel(s: string) {
  const map: Record<string, string> = {
    PENDING_CALC: '待计算',
    READY: '待结算',
    IN_SETTLEMENT: '结算中',
    DONE: '已结算',
  }
  return map[s] || s
}

function listParams() {
  return {
    pageNo: 1,
    pageSize: 50,
    sessionCode: query.sessionCode || undefined,
    platform: query.platform || undefined,
    calcStatus: query.calcStatus || undefined,
    dateFrom: query.dateFrom || undefined,
    dateTo: query.dateTo || undefined,
    profitType: profitType.value,
  }
}

async function loadSummary() {
  const res = await http.get('/fin/profit/summary', { params: listParams() })
  if (res.data?.code === 0) summary.value = res.data.data
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/profit/list', { params: listParams() })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } finally {
    loading.value = false
  }
}

async function reload() {
  await Promise.all([loadSummary(), loadList()])
}

async function switchMetric(kind: ProfitMetric) {
  profitType.value = kind
  await reload()
}

async function openDetail(sessionCode: string) {
  const res = await http.get(`/fin/profit/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '加载详情失败'
    return
  }
  detail.value = res.data.data
  drawerOpen.value = true
}

onMounted(async () => {
  await reload()
})
</script>
