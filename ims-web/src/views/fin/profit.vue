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

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

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
              <td>{{ settlementLabel(String(row.settlementStatus || '')) }}</td>
              <td class="mono" data-testid="fin-profit-calc-version">V{{ row.calcVersion }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(String(row.sessionCode))">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen && detail" class="drawer-mask" @click.self="closeDrawer">
      <div class="drawer on fin-profit-drawer" data-testid="fin-profit-detail-drawer">
        <div class="drawer-h">
          <b>利润详情 · {{ detail.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="closeDrawer">关闭</button>
        </div>
        <div class="drawer-b">
          <div class="g3" style="margin-bottom: 12px">
            <div class="card stat"><span class="l">毛利</span><div class="n">¥{{ fmt(detail.grossProfit) }}</div></div>
            <div class="card stat"><span class="l">经营利润</span><div class="n">¥{{ fmt(detail.operatingProfit) }}</div></div>
            <div class="card stat"><span class="l">净利润</span><div class="n">¥{{ fmt(detail.netProfit) }}</div></div>
          </div>
          <p class="hint">{{ detail.calcRuleSnapshot?.formula }}</p>
          <pre class="mono" style="font-size: 12px; white-space: pre-wrap">{{ JSON.stringify(detail.calcRuleSnapshot?.params, null, 2) }}</pre>
          <p class="hint">当前版本 V{{ detail.calcVersion }} · 计算时间 {{ detail.calculatedAt || '—' }} · 状态 {{ statusLabel(detail.calcStatus) }}</p>

          <h3 class="hist-title">重算版本历史</h3>
          <p v-if="historyError" class="hint" style="color: var(--red)">{{ historyError }}</p>
          <p v-else-if="!history.length" class="hint">暂无重算版本</p>
          <ol v-else class="hist" data-testid="fin-profit-history">
            <li v-for="item in history" :key="item.calcVersion" :data-testid="`fin-profit-history-v${item.calcVersion}`">
              <div class="hist-h">
                <b>V{{ item.calcVersion }}</b>
                <span class="tag">{{ triggerLabel(item.triggerType) }}</span>
                <span class="hint">{{ statusLabel(item.calcStatus) }}</span>
              </div>
              <div class="hint">{{ item.triggerReason || '—' }}</div>
              <div class="hist-amt">
                毛利 ¥{{ fmt(item.grossProfit) }} · 经营利润 ¥{{ fmt(item.operatingProfit) }} · 净利润 ¥{{ fmt(item.netProfit) }}
              </div>
              <div class="hint">{{ item.calculatedAt || '—' }}</div>
            </li>
          </ol>
        </div>
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-profit-recalc" @click="askRecalc">手动触发重算</button>
        </div>
      </div>
    </div>

    <div v-if="recalcOpen && detail" class="modal-mask" data-testid="fin-profit-recalc-dialog">
      <div class="modal-card">
        <b>确认重算</b>
        <p>重算将生成新版本 V{{ nextVersion }}，旧结果留痕（FIN-P-R3）</p>
        <p v-if="recalcError" class="hint" style="color: var(--red)" data-testid="fin-profit-recalc-error">{{ recalcError }}</p>
        <div class="modal-acts">
          <button class="btn btn-sec btn-sm" type="button" :disabled="recalcBusy" @click="recalcOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-profit-recalc-confirm" :disabled="recalcBusy" @click="doRecalc">确认重算</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

interface ProfitDetail {
  sessionCode: string
  grossProfit: number
  operatingProfit: number
  netProfit: number
  calcVersion: number
  calcStatus: string
  calculatedAt: string
  calcRuleSnapshot?: { formula?: string; params?: Record<string, number> }
}

interface HistoryItem {
  calcVersion: number
  netProfit: number
  grossProfit: number
  operatingProfit: number
  calcStatus: string
  triggerType: string
  triggerReason: string
  calculatedAt: string
}

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, unknown>[]>([])
const summary = ref<Record<string, unknown> | null>(null)
const drawerOpen = ref(false)
const detail = ref<ProfitDetail | null>(null)
const history = ref<HistoryItem[]>([])
const historyError = ref('')
const recalcOpen = ref(false)
const recalcBusy = ref(false)
const recalcError = ref('')
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

const nextVersion = computed(() => Number(detail.value?.calcVersion || 1) + 1)

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

function triggerLabel(t: string) {
  const map: Record<string, string> = {
    AUTO_CORRECTION: '成本更正自动',
    MANUAL: '手动',
    AUTO_CONFIRM: '成本核准',
  }
  return map[t] || t || '—'
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    PENDING: '待计算',
    CALCULATED: '已计算',
    RECALCULATED: '已重算',
    ABNORMAL: '异常待核',
  }
  return map[s] || s
}

function closeDrawer() {
  drawerOpen.value = false
  recalcOpen.value = false
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

async function loadHistory(sessionCode: string) {
  historyError.value = ''
  history.value = []
  try {
    const res = await http.get(`/fin/profit/history/${sessionCode}`)
    history.value = (res.data?.data || []) as HistoryItem[]
  } catch (err) {
    historyError.value = errorMessage(err)
  }
}

async function openDetail(sessionCode: string) {
  try {
    const res = await http.get(`/fin/profit/${sessionCode}`)
    detail.value = res.data.data as ProfitDetail
    drawerOpen.value = true
    await loadHistory(sessionCode)
  } catch (err) {
    error.value = errorMessage(err)
  }
}

function askRecalc() {
  recalcError.value = ''
  recalcOpen.value = true
}

async function doRecalc() {
  if (!detail.value || recalcBusy.value) return
  recalcBusy.value = true
  recalcError.value = ''
  const code = detail.value.sessionCode
  try {
    await http.post(`/fin/profit/recalc/${code}`)
    recalcOpen.value = false
    await loadList()
    await openDetail(code)
  } catch (err) {
    recalcError.value = errorMessage(err)
  } finally {
    recalcBusy.value = false
  }
}

onMounted(async () => {
  await loadSummary()
  await loadList()
})
</script>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 90;
}
.fin-profit-drawer {
  width: min(860px, 80vw);
  z-index: 100;
}
.hist-title {
  font-size: 14px;
  margin: 16px 0 8px;
}
.hist {
  list-style: none;
  margin: 0;
  padding: 0 0 0 12px;
  border-left: 2px solid var(--line, #e5e5ea);
}
.hist li {
  padding: 8px 0 12px 12px;
}
.hist-h {
  display: flex;
  gap: 8px;
  align-items: center;
}
.hist-amt {
  font-size: 13px;
  margin-top: 4px;
}
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
  width: 400px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.modal-card p {
  margin: 10px 0;
  line-height: 1.5;
}
.modal-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
