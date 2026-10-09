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
              <td>{{ settlementLabel(row.settlementStatus) }}</td>
              <td>V{{ row.calcVersion }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row.sessionCode)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen && detail" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer on" data-testid="fin-profit-detail-drawer" style="width: 80%">
        <div class="drawer-h">
          <b>利润详情 · {{ detail.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div class="drawer-b">
          <div class="g3" style="margin-bottom: 12px">
            <div class="card stat" data-testid="fin-profit-level-gross">
              <span class="l">毛利</span>
              <div class="n">¥{{ fmt(detail.grossProfit) }}</div>
            </div>
            <div class="card stat" data-testid="fin-profit-level-operating">
              <span class="l">经营利润</span>
              <div class="n">¥{{ fmt(detail.operatingProfit) }}</div>
            </div>
            <div class="card stat" data-testid="fin-profit-level-net">
              <span class="l">净利润</span>
              <div class="n" :class="{ pos: Number(detail.netProfit) >= 0, neg: Number(detail.netProfit) < 0 }">
                ¥{{ fmt(detail.netProfit) }}
              </div>
            </div>
          </div>

          <section data-testid="fin-profit-waterfall">
            <b>三级口径瀑布</b>
            <p class="hint">FIN-P-R2 · GMV 逐项扣至净利润（BR-108）。悬停每级查看公式。</p>
            <ol class="wf-list">
              <li
                v-for="step in waterfall"
                :key="step.key"
                class="wf-row"
                :class="[step.kind, step.level]"
                :data-testid="`fin-profit-wf-${step.key}`"
                :data-level="step.level"
                :data-running="step.running"
                :title="step.formula"
              >
                <span class="wf-label">{{ step.label }}</span>
                <span class="wf-track" aria-hidden="true">
                  <span class="wf-bar" :class="[step.kind, { neg: step.running < 0 }]" :style="barStyle(step)"></span>
                </span>
                <span class="wf-delta num" :class="{ neg: step.kind === 'deduct' }">{{ deltaText(step) }}</span>
                <span class="wf-run num" :class="{ neg: step.running < 0, pos: step.kind === 'level' && step.running >= 0 }">
                  ¥{{ fmt(step.running) }}
                </span>
                <span class="wf-tip">{{ step.formula }}</span>
              </li>
            </ol>
          </section>

          <section data-testid="fin-profit-snapshot" style="margin-top: 16px">
            <b>计算快照</b>
            <p class="hint" data-testid="fin-profit-formula">{{ formulaText }}</p>
            <p class="hint">金额按两位小数展示（V2-E1）</p>
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>参数</th>
                    <th>金额</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in snapshotRows" :key="row.key" :data-testid="`fin-profit-param-${row.key}`">
                    <td>{{ row.label }}</td>
                    <td class="num">¥{{ fmt(row.value) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
          <p class="hint">计算时间：{{ detail.calculatedAt || '—' }} · 状态 {{ detail.calcStatus }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type WfKind = 'start' | 'deduct' | 'level'
type ProfitLevel = '' | 'GROSS' | 'OPERATING' | 'NET'

interface WfStep {
  key: string
  label: string
  kind: WfKind
  level: ProfitLevel
  delta: number
  running: number
  formula: string
}

const SNAPSHOT_FIELDS: { key: string; label: string }[] = [
  { key: 'revenue', label: 'GMV' },
  { key: 'refund', label: '退款' },
  { key: 'commissionAmount', label: '平台佣金' },
  { key: 'adCost', label: '投放成本' },
  { key: 'rechargeCost', label: '冲话费摊销' },
  { key: 'fixedCost', label: '固定成本' },
  { key: 'sampleCost', label: '样品成本' },
  { key: 'shareDaren', label: '达人分成' },
  { key: 'shareRealname', label: '实名人分成' },
  { key: 'totalCost', label: '成本合计' },
]

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, unknown>[]>([])
const summary = ref<Record<string, unknown> | null>(null)
const drawerOpen = ref(false)
const detail = ref<Record<string, unknown> | null>(null)
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

function money(n: unknown) {
  return Math.round(Number(n || 0) * 100) / 100
}

function fmt(n: unknown) {
  return money(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function snapshotParams(row: Record<string, unknown> | null) {
  const snap = row?.calcRuleSnapshot as { params?: Record<string, unknown>; formula?: string } | undefined
  return snap?.params || {}
}

function buildWaterfall(row: Record<string, unknown>): WfStep[] {
  const params = snapshotParams(row)
  const gmv = money(row.gmv ?? params.revenue)
  const refund = money(params.refund)
  const commission = money(params.commissionAmount)
  const ad = money(params.adCost)
  const recharge = money(params.rechargeCost)
  const fixed = money(params.fixedCost)
  const sample = money(params.sampleCost)
  const daren = money(params.shareDaren)
  const realname = money(params.shareRealname)
  const gross = money(row.grossProfit)
  const operating = money(row.operatingProfit)
  const net = money(row.netProfit)
  const steps: WfStep[] = []
  let running = gmv

  const pushDeduct = (key: string, label: string, amount: number, formula: string) => {
    running = money(running - amount)
    steps.push({ key, label, kind: 'deduct', level: '', delta: money(-amount), running, formula })
  }

  steps.push({
    key: 'gmv',
    label: 'GMV',
    kind: 'start',
    level: '',
    delta: 0,
    running: gmv,
    formula: '起点：GMV',
  })
  pushDeduct('refund', '退款', refund, '扣减退款')
  pushDeduct('commission', '平台佣金', commission, '扣减平台佣金')
  steps.push({
    key: 'gross',
    label: '毛利',
    kind: 'level',
    level: 'GROSS',
    delta: 0,
    running: gross,
    formula: '毛利 = GMV − 退款 − 平台佣金',
  })
  running = gross
  pushDeduct('ad', '投放成本', ad, '扣减投放成本')
  pushDeduct('recharge', '冲话费', recharge, '扣减冲话费摊销')
  steps.push({
    key: 'operating',
    label: '经营利润',
    kind: 'level',
    level: 'OPERATING',
    delta: 0,
    running: operating,
    formula: '经营利润 = 毛利 − 投放 − 冲话费',
  })
  running = operating
  pushDeduct('fixed', '固定成本', fixed, '扣减固定成本')
  pushDeduct('sample', '样品成本', sample, '扣减样品成本')
  pushDeduct('shareDaren', '达人分成', daren, '扣减达人分成')
  pushDeduct('shareRealname', '实名人分成', realname, '扣减实名人分成')
  steps.push({
    key: 'net',
    label: '净利润',
    kind: 'level',
    level: 'NET',
    delta: 0,
    running: net,
    formula: '净利润 = GMV − 退款 − 佣金 − 投放 − 冲话费 − 固定 − 样品 − 达人分成 − 实名人分成（BR-108）',
  })
  return steps
}

const waterfall = computed(() => (detail.value ? buildWaterfall(detail.value) : []))

const snapshotRows = computed(() => {
  const params = snapshotParams(detail.value)
  return SNAPSHOT_FIELDS.map((field) => ({ ...field, value: money(params[field.key]) }))
})

const formulaText = computed(() => {
  const snap = detail.value?.calcRuleSnapshot as { formula?: string } | undefined
  return snap?.formula || ''
})

function barStyle(step: WfStep) {
  const steps = waterfall.value
  const scale = Math.max(1, ...steps.map((item) => Math.max(Math.abs(item.running), Math.abs(item.running - item.delta))))
  if (step.kind === 'deduct') {
    const prev = step.running - step.delta
    const left = Math.min(step.running, prev)
    return {
      left: `${(Math.max(left, 0) / scale) * 100}%`,
      width: `${(Math.abs(step.delta) / scale) * 100}%`,
    }
  }
  return { left: '0%', width: `${(Math.abs(step.running) / scale) * 100}%` }
}

function deltaText(step: WfStep) {
  if (step.kind !== 'deduct') return step.kind === 'level' ? '口径' : ''
  return `−¥${fmt(Math.abs(step.delta))}`
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
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
}
.wf-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.wf-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 108px 120px;
  gap: 8px;
  align-items: center;
  position: relative;
  padding: 4px 6px;
  border-radius: 6px;
}
.wf-row.level {
  background: var(--blue-bg);
  font-weight: 600;
}
.wf-row.NET {
  background: #e8f8ee;
}
.wf-track {
  position: relative;
  height: 14px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}
.wf-bar {
  position: absolute;
  top: 2px;
  height: 10px;
  border-radius: 3px;
  min-width: 2px;
}
.wf-bar.start {
  background: var(--blue);
}
.wf-bar.deduct {
  background: var(--orange);
}
.wf-bar.level {
  background: var(--green);
}
.wf-bar.neg {
  background: var(--red);
}
.wf-delta,
.wf-run {
  text-align: right;
  font-size: 12.5px;
}
.wf-tip {
  display: none;
  position: absolute;
  left: 96px;
  top: calc(100% - 2px);
  z-index: 3;
  background: #1d1d1f;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}
.wf-row:hover .wf-tip {
  display: block;
}
</style>
