<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>台账对账</h1>
        <div class="sub">E2E-S3-08 · 场次 × 成本 × 利润 × 分成 · 四账一致（结账锁定不在本页）</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="reconcile">
      <input v-model="sessionCode" placeholder="场次 ID" style="width: 240px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="reconcile">查询</button>
    </form>

    <div v-if="error" class="hint" data-testid="fin-ledger-error" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div v-if="view" class="tbl-block" style="margin-top: 12px">
      <p class="hint" data-testid="fin-ledger-consistent" style="margin-bottom: 8px">
        {{ view.consistent ? '四账一致' : '未对齐' }}
      </p>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>账</th>
              <th>关键数</th>
              <th>金额</th>
            </tr>
          </thead>
          <tbody>
            <tr data-testid="fin-ledger-session">
              <td>场次</td>
              <td class="mono">{{ view.sessionCode }} · GMV</td>
              <td class="num">¥{{ fmt(view.gmv) }}</td>
            </tr>
            <tr data-testid="fin-ledger-cost">
              <td>成本</td>
              <td>总成本</td>
              <td class="num">¥{{ fmt(view.totalCost) }}</td>
            </tr>
            <tr data-testid="fin-ledger-profit">
              <td>利润</td>
              <td>净利润</td>
              <td class="num">¥{{ fmt(view.netProfit) }}</td>
            </tr>
            <tr data-testid="fin-ledger-share">
              <td>分成</td>
              <td>拆分合计（{{ view.shareStatusText }}）</td>
              <td class="num">¥{{ fmt(view.shareSum) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http } from '../../api/http'

type ShareRow = { shareAmount?: number | string; status?: string }

const sessionCode = ref('')
const error = ref('')
const view = ref<{
  consistent: boolean
  sessionCode: string
  gmv: number
  totalCost: number
  netProfit: number
  shareSum: number
  shareStatusText: string
} | null>(null)

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function money(n: unknown) {
  return Math.round(Number(n || 0) * 100) / 100
}

async function reconcile() {
  error.value = ''
  view.value = null
  const code = sessionCode.value.trim()
  if (!code) {
    error.value = '请填写场次 ID'
    return
  }
  const [profitRes, costRes, shareRes] = await Promise.all([
    http.get(`/fin/profit/${encodeURIComponent(code)}`),
    http.get(`/fin/cost/${encodeURIComponent(code)}`),
    http.get('/fin/share/results', { params: { sessionCode: code, pageNo: 1, pageSize: 50 } }),
  ])
  if (profitRes.data?.code !== 0) {
    error.value = profitRes.data?.msg || '利润未就绪'
    return
  }
  if (costRes.data?.code !== 0) {
    error.value = costRes.data?.msg || '成本未就绪'
    return
  }
  if (shareRes.data?.code !== 0) {
    error.value = shareRes.data?.msg || '分成单未就绪'
    return
  }
  const profit = profitRes.data.data || {}
  const cost = costRes.data.data || {}
  const shareRows = (shareRes.data.data?.list || []) as ShareRow[]
  if (
    profit.netProfit === '***' ||
    profit.gmv === '***' ||
    cost.costGmv === '***' ||
    cost.totalCost === '***' ||
    shareRows.some((row) => row.shareAmount === '***')
  ) {
    error.value = '金额已脱敏，当前角色不能对账'
    return
  }
  const shares = shareRows.filter((row) => row.status !== 'REVERSED')
  const expectedNet = money(money(cost.costGmv) - money(cost.costRefund) - money(cost.totalCost))
  const shareExpected = money(money(cost.shareDaren) + money(cost.shareRealname))
  const shareSum = money(shares.reduce((acc, row) => acc + money(row.shareAmount), 0))
  const paidOff = shares.length > 0 && shares.every((row) => row.status === 'PAID_OFF')
  const consistent =
    profit.sessionCode === cost.sessionCode &&
    Math.abs(money(profit.netProfit) - expectedNet) < 0.01 &&
    Math.abs(shareSum - shareExpected) < 0.01 &&
    paidOff
  view.value = {
    consistent,
    sessionCode: String(profit.sessionCode || code),
    gmv: money(cost.costGmv),
    totalCost: money(cost.totalCost),
    netProfit: money(profit.netProfit),
    shareSum,
    shareStatusText: paidOff ? '已发放' : '未全部发放',
  }
}
</script>
