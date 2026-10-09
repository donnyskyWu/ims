<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润核算</h1>
        <div class="sub">FIN-002 · 利润列表 · 三级口径排序 · 异常净利率（2σ）· 11 FIN（场次财务，非账号 COST）</div>
      </div>
    </div>

    <div v-if="summary" class="g4" style="margin-bottom: 12px">
      <div class="card stat">
        <span class="l">已核算场次</span>
        <div class="n">{{ summary.sessionCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">总收入</span>
        <div class="n" data-testid="fin-profit-summary-revenue">{{ yuan(summary.totalRevenue) }}</div>
      </div>
      <div class="card stat">
        <span class="l">总成本</span>
        <div class="n" data-testid="fin-profit-summary-cost">{{ yuan(summary.totalCost) }}</div>
      </div>
      <div class="card stat">
        <span class="l" data-testid="fin-profit-summary-label">{{ profitLabel }}合计</span>
        <div
          class="n"
          data-testid="fin-profit-summary-shown"
          :class="amtClass(summary.shownProfit)"
        >
          {{ yuanSigned(summary.shownProfit) }}
        </div>
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

    <form v-show="tab === 'list'" class="qbar" @submit.prevent="reload">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 180px" />
      <input v-model="query.platform" placeholder="平台" style="width: 100px" />
      <input v-model="query.dateFrom" type="date" data-testid="fin-profit-date-from" aria-label="开始日期" />
      <input v-model="query.dateTo" type="date" data-testid="fin-profit-date-to" aria-label="结束日期" />
      <select v-model="query.calcStatus" aria-label="计算状态" style="width: 120px">
        <option value="">全部状态</option>
        <option value="PENDING">待计算</option>
        <option value="CALCULATED">已计算</option>
        <option value="RECALCULATED">已重算</option>
        <option value="ABNORMAL">异常待核</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="reload">查询</button>
    </form>

    <div v-show="tab === 'list'" class="tabs" data-testid="fin-profit-metric" role="radiogroup" aria-label="利润口径" style="margin: 8px 0">
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
    <p v-show="tab === 'list'" class="hint" data-testid="fin-profit-sort-hint" style="margin: 0 0 8px">
      按{{ profitLabel }}降序 · 毛利、经营利润、净利润三列同时展示
    </p>
    <div v-if="recalcMsg" class="hint" data-testid="fin-profit-recalc-msg" style="margin: 8px 0">{{ recalcMsg }}</div>
    <p v-if="listAmountsMasked && tab === 'list'" class="hint" data-testid="fin-profit-amount-mask">金额已脱敏</p>

    <div v-if="error && tab === 'list'" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div v-show="tab === 'list'" class="tbl-block">
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
              <th data-testid="fin-profit-col-calc-status">计算状态</th>
              <th data-testid="fin-profit-col-calculated-at">计算时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="13"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="13"><div class="empty"><div class="et">暂无利润数据（需先核准成本）</div></div></td>
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
              <td class="num" data-testid="fin-profit-gmv">{{ yuan(row.gmv) }}</td>
              <td class="num" data-testid="fin-profit-gross" :class="amtClass(row.grossProfit)">{{ yuanSigned(row.grossProfit) }}</td>
              <td class="num" data-testid="fin-profit-operating" :class="amtClass(row.operatingProfit)">{{ yuanSigned(row.operatingProfit) }}</td>
              <td class="num" data-testid="fin-profit-net" :class="amtClass(row.netProfit)">{{ yuanSigned(row.netProfit) }}</td>
              <td class="num">{{ row.netProfitRate }}%</td>
              <td>{{ settlementLabel(String(row.settlementStatus || '')) }}</td>
              <td class="mono" data-testid="fin-profit-calc-version">V{{ row.calcVersion }}</td>
              <td>
                <span
                  class="tag"
                  data-testid="fin-profit-calc-status"
                  :style="calcStatusStyle(row.calcStatus)"
                ><span class="dot"></span>{{ calcStatusLabel(row.calcStatus) }}</span>
              </td>
              <td class="mono" data-testid="fin-profit-calculated-at">{{ formatCalculatedAt(row.calculatedAt) }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(String(row.sessionCode))">详情</button>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-profit-recalc"
                  style="margin-left: 6px"
                  :disabled="row.financeStatus === 'LOCKED' || recalcBusy"
                  :title="recalcTitle(row)"
                  @click="askListRecalc(row)"
                >
                  重算
                </button>
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

    <div v-if="drawerOpen && detail" class="drawer-mask" @click.self="closeDrawer">
      <div class="drawer on fin-profit-drawer" data-testid="fin-profit-detail-drawer">
        <div class="drawer-h">
          <b>利润详情 · {{ detail.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="closeDrawer">关闭</button>
        </div>
        <div class="drawer-b">
          <p v-if="verifyHint" class="hint" data-testid="fin-profit-abnormal-hint" style="color: var(--red)">{{ verifyHint }}</p>
          <div class="g3" style="margin-bottom: 12px">
            <div class="card stat" data-testid="fin-profit-level-gross">
              <span class="l">毛利</span>
              <div class="n">{{ yuan(detail.grossProfit) }}</div>
            </div>
            <div class="card stat" data-testid="fin-profit-level-operating">
              <span class="l">经营利润</span>
              <div class="n">{{ yuan(detail.operatingProfit) }}</div>
            </div>
            <div class="card stat" data-testid="fin-profit-level-net">
              <span class="l">净利润</span>
              <div class="n" :class="amtClass(detail.netProfit)">
                {{ yuan(detail.netProfit) }}
              </div>
            </div>
          </div>

          <p v-if="detailAmountsMasked" class="hint" data-testid="fin-profit-detail-mask">金额已脱敏 ***</p>
          <section v-else data-testid="fin-profit-waterfall">
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
                    <td class="num">{{ yuan(row.value) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
          <p class="hint">当前版本 V{{ detail.calcVersion }} · 计算时间 {{ formatCalculatedAt(detail.calculatedAt) }} · 状态 {{ detail.calcStatus }}</p>
          <p class="hint">
            计算状态
            <span class="tag" :style="calcStatusStyle(detail.calcStatus)">{{ calcStatusLabel(detail.calcStatus) }}</span>
          </p>

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
                毛利 {{ yuan(item.grossProfit) }} · 经营利润 {{ yuan(item.operatingProfit) }} · 净利润 {{ yuan(item.netProfit) }}
              </div>
              <div class="hint">{{ item.calculatedAt || '—' }}</div>
            </li>
          </ol>
        </div>
        <div class="drawer-f">
          <p v-if="periodLocked" class="hint" data-testid="fin-profit-recalc-locked">财务期间已结账，重算冻结（1142）</p>
          <p v-if="recalcNote" class="hint" data-testid="fin-profit-recalc-done">{{ recalcNote }}</p>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="fin-profit-recalc-open"
            :disabled="periodLocked || recalcBusy"
            :title="periodLocked ? '财务期间已结账，重算冻结（1142）' : '手动触发重算'"
            @click="askRecalc"
          >
            手动触发重算
          </button>
        </div>
      </div>
    </div>

    <div v-if="recalcOpen && detail" class="modal-mask" data-testid="fin-profit-recalc-dialog">
      <div class="modal-card" data-testid="fin-profit-recalc-confirm">
        <b>确认重算</b>
        <p>重算将生成新版本 V{{ nextVersion }}，旧结果留痕（FIN-P-R3）</p>
        <p class="hint">重算生成新版本，旧结果留痕（FIN-P-R3）</p>
        <p v-if="recalcError" class="hint" style="color: var(--red)" data-testid="fin-profit-recalc-error">{{ recalcError }}</p>
        <div class="modal-acts">
          <button class="btn btn-sec btn-sm" type="button" :disabled="recalcBusy" @click="recalcOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-profit-recalc-submit" :disabled="recalcBusy" @click="doRecalc">确认重算</button>
        </div>
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
import { errorMessage, http } from '../../api/http'

interface ProfitDetail {
  sessionCode: string
  gmv?: number | string
  grossProfit: number | string
  operatingProfit: number | string
  netProfit: number | string
  calcVersion: number
  calcStatus: string
  calculatedAt: string
  financeStatus?: string
  periodMonth?: string
  calcRuleSnapshot?: { formula?: string; params?: Record<string, number | string> }
}

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

type ProfitMetric = 'GROSS' | 'OPERATING' | 'NET'

const metrics: { value: ProfitMetric; label: string }[] = [
  { value: 'GROSS', label: '毛利' },
  { value: 'OPERATING', label: '经营利润' },
  { value: 'NET', label: '净利润' },
]

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
  calcStatus?: string
  calculatedAt?: string
  calcVersion: number
  financeStatus?: string
}

const loading = ref(false)
const error = ref('')
const recalcMsg = ref('')
const recalcTarget = ref<ProfitRow | null>(null)
const rows = ref<ProfitRow[]>([])
const summary = ref<Record<string, any> | null>(null)
const drawerOpen = ref(false)
const detail = ref<ProfitDetail | null>(null)
const verifyHint = ref('')
const tab = ref<'list' | 'abnormal'>('list')
const abnormalLoading = ref(false)
const abnormalRows = ref<Record<string, unknown>[]>([])
const abnormalPlatform = ref('')
const history = ref<HistoryItem[]>([])
const historyError = ref('')
const recalcOpen = ref(false)
const recalcBusy = ref(false)
const recalcError = ref('')
const recalcNote = ref('')
const profitType = ref<ProfitMetric>('NET')
const query = reactive({ sessionCode: '', platform: '', calcStatus: '', dateFrom: '', dateTo: '' })

const AMOUNT_MASK = '***'
const profitLabel = computed(() => metrics.find((item) => item.value === profitType.value)?.label || '净利润')
const listAmountsMasked = computed(
  () => summary.value?.shownProfit === AMOUNT_MASK || rows.value.some((row) => row.netProfit === AMOUNT_MASK || row.gmv === AMOUNT_MASK),
)
const detailAmountsMasked = computed(() => {
  const row = detail.value
  if (!row) return false
  return row.netProfit === AMOUNT_MASK || row.grossProfit === AMOUNT_MASK || snapshotParams(row).revenue === AMOUNT_MASK
})

const nextVersion = computed(() => {
  if (recalcTarget.value) return Number(recalcTarget.value.calcVersion || 0) + 1
  return Number(detail.value?.calcVersion || 1) + 1
})
const periodLocked = computed(() => String(detail.value?.financeStatus || '') === 'LOCKED')

function snapshotParams(row: ProfitDetail | null) {
  return row?.calcRuleSnapshot?.params || {}
}

function buildWaterfall(row: ProfitDetail): WfStep[] {
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

  steps.push({ key: 'gmv', label: 'GMV', kind: 'start', level: '', delta: 0, running: gmv, formula: '起点：GMV' })
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
  return SNAPSHOT_FIELDS.map((field) => {
    const raw = params[field.key]
    return { ...field, value: raw === AMOUNT_MASK ? AMOUNT_MASK : money(raw) }
  })
})

const formulaText = computed(() => detail.value?.calcRuleSnapshot?.formula || '')

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

function money(n: unknown) {
  return Math.round(Number(n || 0) * 100) / 100
}

function recalcTitle(row: ProfitRow) {
  if (row.financeStatus === 'LOCKED') return '财务期间已结账，重算冻结（1142）'
  return '手动触发重算（FIN-P-R3）'
}

function fmt(n: unknown) {
  return money(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtSigned(n: unknown) {
  const value = Number(n || 0)
  const text = Math.abs(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return value < 0 ? `(${text})` : text
}

function yuan(n: unknown) {
  if (n === AMOUNT_MASK) return AMOUNT_MASK
  return `¥${fmt(n)}`
}

function yuanSigned(n: unknown) {
  if (n === AMOUNT_MASK) return AMOUNT_MASK
  return `¥${fmtSigned(n)}`
}

function amtClass(n: unknown) {
  if (n === AMOUNT_MASK) return ''
  return Number(n || 0) < 0 ? 'neg' : 'pos'
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

function triggerLabel(t: string) {
  const map: Record<string, string> = {
    AUTO_CORRECTION: '成本更正自动',
    MANUAL: '手动',
    AUTO_CONFIRM: '成本核准',
  }
  return map[t] || t || '—'
}

function textOf(value: unknown) {
  return value == null ? '' : String(value)
}

function statusLabel(value: unknown) {
  const map: Record<string, string> = {
    PENDING: '待计算',
    CALCULATED: '已计算',
    RECALCULATED: '已重算',
    ABNORMAL: '异常待核',
  }
  const key = textOf(value)
  return map[key] || key
}

function calcStatusLabel(value: unknown) {
  const label = statusLabel(value)
  return label || '—'
}

function calcStatusStyle(value: unknown) {
  const key = textOf(value)
  if (key === 'CALCULATED') return { background: 'rgba(52,199,89,.12)', color: '#248a3d' }
  if (key === 'RECALCULATED') return { background: 'rgba(90,200,250,.18)', color: '#0e7fb8' }
  if (key === 'ABNORMAL') return { background: 'rgba(255,149,0,.14)', color: '#c46a00' }
  return { background: 'rgba(142,142,147,.14)', color: '#6d6d72' }
}

function formatCalculatedAt(value: unknown) {
  const matched = textOf(value).trim().match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/)
  if (!matched) return '—'
  return `${matched[1]} ${matched[2]}`
}

function closeDrawer() {
  drawerOpen.value = false
  recalcOpen.value = false
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
    rows.value = (res.data.data?.list || []) as ProfitRow[]
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

function askListRecalc(row: ProfitRow) {
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

async function openDetail(sessionCode: string, abnormal?: Record<string, unknown>) {
  const res = await http.get(`/fin/profit/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '加载详情失败'
    return
  }
  detail.value = res.data.data as ProfitDetail
  verifyHint.value = abnormal
    ? `净利率 ${abnormal.netProfitRate}% 偏离同类均值 ${abnormal.peerAvgRate}%，超过 2σ 阈值（当前 ${abnormal.deviationSigma}σ），请核实成本项`
    : ''
  drawerOpen.value = true
  await loadHistory(sessionCode)
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

function askRecalc() {
  if (periodLocked.value || recalcBusy.value) return
  recalcError.value = ''
  recalcOpen.value = true
}

async function doRecalc() {
  if (!detail.value || recalcBusy.value) return
  recalcBusy.value = true
  recalcError.value = ''
  const code = detail.value.sessionCode
  try {
    const res = await http.post(`/fin/profit/recalc/${code}`)
    const body = res.data
    if (body?.code === 1142) {
      detail.value = { ...detail.value, financeStatus: 'LOCKED' }
      recalcError.value = body.msg || '财务期间已结账，重算冻结（1142）'
      recalcOpen.value = false
      return
    }
    if (body?.code !== 0) {
      recalcError.value = body?.msg || '重算失败'
      return
    }
    recalcNote.value = String(body.data?.message || '利润已重算')
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
  await reload()
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
  width: 80%;
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
