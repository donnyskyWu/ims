<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润核算</h1>
        <div class="sub">FIN-002 · 利润列表 · 结算概览 · 11 FIN（场次财务，非账号 COST）</div>
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
      <button type="button" class="tab on">利润列表</button>
    </div>

    <form class="qbar" @submit.prevent="loadList">
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

    <div v-if="error" class="hint" data-testid="fin-profit-recalc-error" style="color: var(--red); margin: 8px 0">{{ error }}</div>
    <div v-if="recalcMsg" class="hint" data-testid="fin-profit-recalc-msg" style="margin: 8px 0">{{ recalcMsg }}</div>

    <div class="tbl-block">
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
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row.sessionCode)">详情</button>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-profit-recalc"
                  style="margin-left: 6px"
                  :disabled="row.financeStatus === 'LOCKED' || recalcBusy"
                  :title="recalcTitle(row)"
                  @click="askRecalc(row)"
                >
                  重算
                </button>
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
          <div class="card stat"><span class="l">毛利</span><div class="n">¥{{ fmt(detail.grossProfit) }}</div></div>
          <div class="card stat"><span class="l">经营利润</span><div class="n">¥{{ fmt(detail.operatingProfit) }}</div></div>
          <div class="card stat"><span class="l">净利润</span><div class="n">¥{{ fmt(detail.netProfit) }}</div></div>
        </div>
        <p class="hint">{{ detail.calcRuleSnapshot?.formula }}</p>
        <pre class="mono" style="font-size: 12px; white-space: pre-wrap">{{ JSON.stringify(detail.calcRuleSnapshot?.params, null, 2) }}</pre>
        <p class="hint">计算时间：{{ detail.calculatedAt || '—' }} · 状态 {{ detail.calcStatus }}</p>
      </div>
    </div>

    <div v-if="recalcTarget" class="modal-mask" data-testid="fin-profit-recalc-confirm">
      <div class="card" style="width: 400px; padding: 20px">
        <h3 style="margin: 0 0 12px">确认重算</h3>
        <p style="margin: 0">
          重算将生成新版本 V{{ nextVersion }}，旧结果留痕（FIN-P-R3）
        </p>
        <p class="hint" style="margin: 8px 0 0">{{ recalcTarget.sessionCode }}</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" data-testid="fin-profit-recalc-cancel" @click="recalcTarget = null">
            取消
          </button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="fin-profit-recalc-ok"
            :disabled="recalcBusy"
            @click="confirmRecalc"
          >
            确认重算
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type ProfitRow = {
  sessionCode: string
  sessionTitle?: string
  platform?: string
  gmv?: number
  grossProfit?: number
  operatingProfit?: number
  netProfit?: number
  netProfitRate?: number
  settlementStatus?: string
  calcVersion: number
  financeStatus?: string
}

const loading = ref(false)
const error = ref('')
const recalcMsg = ref('')
const recalcBusy = ref(false)
const recalcTarget = ref<ProfitRow | null>(null)
const rows = ref<ProfitRow[]>([])
const summary = ref<Record<string, unknown> | null>(null)
const drawerOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

const nextVersion = computed(() => Number(recalcTarget.value?.calcVersion || 0) + 1)

function recalcTitle(row: ProfitRow) {
  if (row.financeStatus === 'LOCKED') return '财务期间已结账，重算冻结（1142）'
  return '手动触发重算（FIN-P-R3）'
}

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function settlementLabel(s: string | undefined) {
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
    rows.value = (res.data.data?.list || []) as ProfitRow[]
  } finally {
    loading.value = false
  }
}

function askRecalc(row: ProfitRow) {
  if (row.financeStatus === 'LOCKED' || recalcBusy.value) return
  error.value = ''
  recalcTarget.value = row
}

async function confirmRecalc() {
  const row = recalcTarget.value
  if (!row || recalcBusy.value) return
  recalcBusy.value = true
  error.value = ''
  recalcMsg.value = ''
  try {
    const res = await http.post(`/fin/profit/recalc/${row.sessionCode}`)
    const code = res.data?.code
    if (code === 1142) {
      row.financeStatus = 'LOCKED'
      error.value = res.data?.msg || '财务期间已结账，重算冻结（1142）'
      recalcTarget.value = null
      return
    }
    if (code !== 0) {
      error.value = res.data?.msg || '重算失败'
      return
    }
    const data = res.data.data || {}
    recalcMsg.value = `${data.message || '利润已重算'} · V${data.calcVersion}`
    recalcTarget.value = null
    await loadSummary()
    await loadList()
  } finally {
    recalcBusy.value = false
  }
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
  await loadSummary()
  await loadList()
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
</style>
