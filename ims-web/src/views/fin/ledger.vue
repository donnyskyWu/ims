<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>台账对账</h1>
        <div class="sub">E2E-S3-08 · 场次 × 成本 × 利润 × 分成 · 缺账显示空态，不打断其余账</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="reconcile">
      <input
        v-model="sessionCode"
        data-testid="fin-ledger-query"
        placeholder="场次 ID"
        style="width: 240px"
      />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-ledger-search" @click="reconcile">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-ledger-reset" @click="resetLedger">重置</button>
    </form>

    <div v-if="error" class="hint" data-testid="fin-ledger-error" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div
      v-if="periodLocked"
      class="card fin-ledger-lock"
      data-testid="fin-ledger-period-lock"
    >
      <b>财务期间已结账</b>
      <p>录入、核准、更正均冻结。本期间写操作冻结<span v-if="periodMonth"> · {{ periodMonth }}</span>。</p>
    </div>

    <div v-if="loading" class="tbl-block" style="margin-top: 12px">
      <div class="empty" data-testid="fin-ledger-loading"><div class="et">加载中</div></div>
    </div>

    <div v-else-if="!searched" class="tbl-block" style="margin-top: 12px">
      <div class="empty" data-testid="fin-ledger-jump-empty">
        <div class="et">从利润或成本跳转后，按场次核对四账</div>
        <div class="es">也可直接输入场次号。缺哪一账，对应行显示空态。</div>
      </div>
    </div>

    <div v-else-if="missingSession" class="tbl-block" style="margin-top: 12px">
      <div class="empty" data-testid="fin-ledger-missing">
        <div class="et">未找到场次 {{ queriedCode }}</div>
        <div class="es">该场次不存在或当前账号不可见，四账均为空。</div>
      </div>
    </div>

    <div v-else-if="view" class="tbl-block" style="margin-top: 12px">
      <p class="hint" data-testid="fin-ledger-consistent" style="margin-bottom: 8px">
        {{ view.headline }}
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
              <td class="mono">{{ view.session.detail }}</td>
              <td class="num">{{ view.session.amountText }}</td>
            </tr>
            <tr data-testid="fin-ledger-cost">
              <td>成本</td>
              <td>{{ view.cost.detail }}</td>
              <td class="num" :data-testid="view.cost.ready ? undefined : 'fin-ledger-cost-empty'">
                {{ view.cost.amountText }}
              </td>
            </tr>
            <tr data-testid="fin-ledger-profit">
              <td>利润</td>
              <td>{{ view.profit.detail }}</td>
              <td class="num" :data-testid="view.profit.ready ? undefined : 'fin-ledger-profit-empty'">
                {{ view.profit.amountText }}
              </td>
            </tr>
            <tr data-testid="fin-ledger-share">
              <td>分成</td>
              <td>{{ view.share.detail }}</td>
              <td class="num" :data-testid="view.share.ready ? undefined : 'fin-ledger-share-empty'">
                {{ view.share.amountText }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'

type ShareRow = { shareAmount?: number | string; status?: string }
type BookCell = { ready: boolean; detail: string; amountText: string }
type LedgerView = {
  headline: string
  session: BookCell
  cost: BookCell
  profit: BookCell
  share: BookCell
}
type BookHit<T> = { ok: true; data: T } | { ok: false; code: number; msg: string }

const route = useRoute()
const router = useRouter()
const sessionCode = ref('')
const queriedCode = ref('')
const error = ref('')
const loading = ref(false)
const searched = ref(false)
const missingSession = ref(false)
const periodLocked = ref(false)
const periodMonth = ref('')
const view = ref<LedgerView | null>(null)

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function money(n: unknown) {
  return Math.round(Number(n || 0) * 100) / 100
}

function yuan(n: unknown) {
  return `¥${fmt(n)}`
}

function emptyCell(detail: string): BookCell {
  return { ready: false, detail, amountText: '—' }
}

function failOf(err: unknown): { code: number; msg: string } {
  const data = axios.isAxiosError(err)
    ? (err.response?.data as { code?: number; msg?: string } | undefined)
    : err && typeof err === 'object'
      ? (err as { code?: number; msg?: string })
      : undefined
  return { code: Number(data?.code || 0), msg: data?.msg || '未就绪' }
}

async function readBook<T>(url: string, params?: Record<string, unknown>): Promise<BookHit<T>> {
  try {
    const res = await http.get(url, { params })
    return { ok: true, data: res.data.data as T }
  } catch (err) {
    const body = failOf(err)
    return { ok: false, code: body.code, msg: body.msg }
  }
}

function applyQueryCode() {
  const code = typeof route.query.sessionCode === 'string' ? route.query.sessionCode.trim() : ''
  if (!code || code === queriedCode.value) return
  sessionCode.value = code
  reconcile()
}

async function reconcile() {
  error.value = ''
  view.value = null
  missingSession.value = false
  periodLocked.value = false
  periodMonth.value = ''
  const code = sessionCode.value.trim()
  if (!code) {
    searched.value = false
    queriedCode.value = ''
    error.value = '请填写场次 ID'
    return
  }
  loading.value = true
  searched.value = true
  queriedCode.value = code
  try {
    const [profitHit, costHit, shareHit] = await Promise.all([
      readBook<Record<string, unknown>>(`/fin/profit/${encodeURIComponent(code)}`),
      readBook<Record<string, unknown>>(`/fin/cost/${encodeURIComponent(code)}`),
      readBook<{ list?: ShareRow[] }>('/fin/share/results', { sessionCode: code, pageNo: 1, pageSize: 50 }),
    ])
    const missing =
      (!profitHit.ok && profitHit.code === 1504) || (!costHit.ok && costHit.code === 1504)
    if (missing) {
      missingSession.value = true
      return
    }
    const profit = profitHit.ok ? profitHit.data : null
    const cost = costHit.ok ? costHit.data : null
    const shareRows = shareHit.ok ? shareHit.data?.list || [] : []
    if (
      profit?.netProfit === '***' ||
      profit?.gmv === '***' ||
      cost?.costGmv === '***' ||
      cost?.totalCost === '***' ||
      shareRows.some((row) => row.shareAmount === '***')
    ) {
      error.value = '金额已脱敏，当前角色不能对账'
      return
    }
    const shares = shareRows.filter((row) => row.status !== 'REVERSED')
    const lockedSource = profit || cost
    periodLocked.value = String(lockedSource?.financeStatus || '') === 'LOCKED'
    periodMonth.value = String(lockedSource?.periodMonth || '')

    const sessionCell: BookCell = cost
      ? { ready: true, detail: `${code} · GMV`, amountText: yuan(cost.costGmv) }
      : emptyCell(`${code} · 金额随成本带出`)
    const costCell: BookCell = cost
      ? { ready: true, detail: '总成本', amountText: yuan(cost.totalCost) }
      : emptyCell(costHit.ok ? '成本未就绪' : costHit.msg)
    const profitCell: BookCell = profit
      ? { ready: true, detail: '净利润', amountText: yuan(profit.netProfit) }
      : emptyCell(profitHit.ok ? '利润未就绪' : profitHit.msg)
    const paidOff = shares.length > 0 && shares.every((row) => row.status === 'PAID_OFF')
    const shareSum = money(shares.reduce((acc, row) => acc + money(row.shareAmount), 0))
    const shareCell: BookCell = shares.length
      ? {
          ready: true,
          detail: `拆分合计（${paidOff ? '已发放' : '未全部发放'}）`,
          amountText: yuan(shareSum),
        }
      : emptyCell(shareHit.ok ? '暂无分成单' : shareHit.msg)

    const booksReady = Boolean(cost && profit && shares.length)
    let headline = '四账未齐'
    if (booksReady && cost && profit) {
      const expectedNet = money(money(cost.costGmv) - money(cost.costRefund) - money(cost.totalCost))
      const shareExpected = money(money(cost.shareDaren) + money(cost.shareRealname))
      const aligned =
        profit.sessionCode === cost.sessionCode &&
        Math.abs(money(profit.netProfit) - expectedNet) < 0.01 &&
        Math.abs(shareSum - shareExpected) < 0.01 &&
        paidOff
      headline = aligned ? '四账一致' : '未对齐'
    }
    view.value = {
      headline,
      session: sessionCell,
      cost: costCell,
      profit: profitCell,
      share: shareCell,
    }
  } catch (err) {
    view.value = null
    error.value = failOf(err).msg || '对账失败'
  } finally {
    loading.value = false
  }
}

function resetLedger() {
  sessionCode.value = ''
  queriedCode.value = ''
  error.value = ''
  view.value = null
  searched.value = false
  missingSession.value = false
  periodLocked.value = false
  periodMonth.value = ''
  if (route.query.sessionCode) {
    router.replace({ path: '/ims/fin/ledger' })
  }
}

onMounted(applyQueryCode)
watch(() => route.query.sessionCode, applyQueryCode)
</script>

<style scoped>
.fin-ledger-lock {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 59, 48, 0.35);
  background: rgba(255, 59, 48, 0.08);
  color: #c0392b;
}
.fin-ledger-lock p {
  margin: 4px 0 0;
  font-size: 13px;
}
</style>
