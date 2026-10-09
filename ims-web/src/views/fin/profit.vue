<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润核算</h1>
        <div class="sub">FIN-002 · 利润列表 · 异常净利率（2σ）· 11 FIN（场次财务，非账号 COST）</div>
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
        <span class="l">净利润合计</span>
        <div class="n" style="color: var(--green)">¥{{ fmt(summary.totalNetProfit) }}</div>
        <div class="d">待结算 {{ summary.readySettlementCount }} · 结算中 {{ summary.inSettlementCount }}</div>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'list' }"
        data-testid="fin-profit-tab-list"
        @click="tab = 'list'"
      >
        利润列表
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'abnormal' }"
        data-testid="fin-profit-tab-abnormal"
        @click="openAbnormal"
      >
        异常净利率(2σ)
      </button>
    </div>

    <form v-show="tab === 'list'" class="qbar" @submit.prevent="loadList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 180px" />
      <input v-model="query.platform" placeholder="平台" style="width: 100px" />
      <select v-model="query.calcStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="CALCULATED">已计算</option>
        <option value="RECALCULATED">已重算</option>
        <option value="PENDING">待计算</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadList">查询</button>
    </form>

    <div v-if="error && tab === 'list'" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div v-show="tab === 'list'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>标题</th>
              <th>平台</th>
              <th>GMV</th>
              <th>毛利</th>
              <th>经营利润</th>
              <th>净利润</th>
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
            <tr v-for="row in rows" v-else :key="row.sessionCode">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.sessionTitle }}</td>
              <td>{{ row.platform }}</td>
              <td class="num">¥{{ fmt(row.gmv) }}</td>
              <td class="num">¥{{ fmt(row.grossProfit) }}</td>
              <td class="num">¥{{ fmt(row.operatingProfit) }}</td>
              <td class="num" :class="{ pos: row.netProfit >= 0, neg: row.netProfit < 0 }">¥{{ fmt(row.netProfit) }}</td>
              <td class="num">{{ row.netProfitRate }}%</td>
              <td>{{ settlementLabel(row.settlementStatus) }}</td>
              <td>V{{ row.calcVersion }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(String(row.sessionCode))">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-show="tab === 'abnormal'" data-testid="fin-profit-abnormal-panel">
      <p class="hint" style="margin: 8px 0">同类为同平台已核算场次。净利率偏离同行均值达到 2 倍标准差时列入本表。</p>
      <form class="qbar" @submit.prevent="loadAbnormal">
        <input v-model="abnormalPlatform" placeholder="平台" style="width: 120px" data-testid="fin-profit-abnormal-platform" />
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="button" @click="loadAbnormal">查询</button>
      </form>
      <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table data-testid="fin-profit-abnormal-table">
            <thead>
              <tr>
                <th>场次号</th>
                <th>平台</th>
                <th>净利率</th>
                <th>同类均值</th>
                <th>标准差 σ</th>
                <th>偏离 σ</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="abnormalLoading">
                <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!abnormalRows.length">
                <td colspan="7"><div class="empty"><div class="et">暂无偏离 2σ 的场次</div></div></td>
              </tr>
              <tr v-for="row in abnormalRows" v-else :key="row.sessionCode" :data-testid="'fin-profit-abnormal-row-' + row.sessionCode">
                <td class="mono">{{ row.sessionCode }}</td>
                <td>{{ row.platform }}</td>
                <td class="num" style="color: var(--red)">{{ row.netProfitRate }}%</td>
                <td class="num">{{ row.peerAvgRate }}%</td>
                <td class="num">{{ row.sigma }}</td>
                <td class="num" style="color: var(--red)">{{ row.deviationSigma }}σ</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="fin-profit-abnormal-verify" @click="openDetail(String(row.sessionCode), row)">
                    去核实
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="drawerOpen && detail" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer" data-testid="fin-profit-detail-drawer" style="width: 640px">
        <div class="drawer-h">
          <b>利润详情 · {{ detail.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <p v-if="verifyHint" class="hint" data-testid="fin-profit-abnormal-hint" style="color: var(--red)">{{ verifyHint }}</p>
        <div class="g3" style="margin-bottom: 12px">
          <div class="card stat"><span class="l">毛利</span><div class="n">¥{{ fmt(detail.grossProfit) }}</div></div>
          <div class="card stat"><span class="l">经营利润</span><div class="n">¥{{ fmt(detail.operatingProfit) }}</div></div>
          <div class="card stat"><span class="l">净利润</span><div class="n">¥{{ fmt(detail.netProfit) }}</div></div>
        </div>
        <p class="hint">{{ detail.calcRuleSnapshot?.formula }}</p>
        <pre class="mono" style="font-size: 12px; white-space: pre-wrap">{{ JSON.stringify(detail.calcRuleSnapshot?.params, null, 2) }}</pre>
        <p class="hint">计算时间：{{ detail.calculatedAt || '—' }} · 状态 {{ detail.calcStatus }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, unknown>[]>([])
const summary = ref<Record<string, unknown> | null>(null)
const drawerOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const verifyHint = ref('')
const tab = ref<'list' | 'abnormal'>('list')
const abnormalLoading = ref(false)
const abnormalRows = ref<Record<string, unknown>[]>([])
const abnormalPlatform = ref('')
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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

async function loadSummary() {
  const res = await http.get('/fin/profit/summary')
  if (res.data?.code === 0) summary.value = res.data.data
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/profit/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        platform: query.platform || undefined,
        calcStatus: query.calcStatus || undefined,
      },
    })
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

async function loadAbnormal() {
  abnormalLoading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/profit/abnormal', {
      params: {
        pageNo: 1,
        pageSize: 50,
        platform: abnormalPlatform.value || undefined,
      },
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      abnormalRows.value = []
      return
    }
    abnormalRows.value = res.data.data?.list || []
  } finally {
    abnormalLoading.value = false
  }
}

function openAbnormal() {
  tab.value = 'abnormal'
  loadAbnormal()
}

async function openDetail(sessionCode: string, abnormal?: Record<string, unknown>) {
  const res = await http.get(`/fin/profit/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '加载详情失败'
    return
  }
  detail.value = res.data.data
  verifyHint.value = abnormal
    ? `净利率 ${abnormal.netProfitRate}% 偏离同类均值 ${abnormal.peerAvgRate}% 达 ${abnormal.deviationSigma}σ，请核实成本项`
    : ''
  drawerOpen.value = true
}

onMounted(async () => {
  await loadSummary()
  await loadList()
})
</script>
