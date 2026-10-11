<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>成本核算</h1>
        <div class="sub">FIN-001 · 场次成本录入 · 期间结账后写操作冻结（1142）</div>
      </div>
    </div>

    <div class="card" data-testid="fin-period-bar" style="margin-bottom: 12px; padding: 12px">
      <div class="acts" style="align-items: center; gap: 8px; flex-wrap: wrap">
        <label style="display: flex; align-items: center; gap: 6px">
          财务期间
          <input
            v-model="periodMonth"
            data-testid="fin-period-month"
            placeholder="yyyy-MM"
            style="width: 120px"
            @change="loadPeriod"
            @blur="loadPeriod"
          />
        </label>
        <span
          class="tag"
          data-testid="fin-period-status"
          :style="
            periodStatus === 'LOCKED'
              ? 'background: rgba(255, 59, 48, 0.12); color: #c0392b'
              : 'background: rgba(52, 199, 89, 0.12); color: #1f8a4c'
          "
        >{{ periodStatus || 'OPEN' }}</span>
        <button
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="fin-period-close"
          :disabled="periodStatus === 'LOCKED' || periodBusy || !periodMonthValid"
          :title="periodCloseHint"
          @click="closePeriod"
        >
          结账
        </button>
        <span class="hint" data-testid="fin-period-close-hint">{{ periodCloseHint }}</span>
      </div>
      <p
        v-if="periodClosedNote"
        class="hint"
        data-testid="fin-period-close-done"
        style="color: #1f8a4c; margin-top: 8px"
      >
        {{ periodClosedNote }}
      </p>
      <div
        v-if="periodStatus === 'LOCKED' && periodMonthValid"
        data-testid="fin-period-lock-banner"
        class="hint"
        style="color: var(--red); margin-top: 8px"
      >
        财务期间已结账，本期间写操作冻结
        <span v-if="periodLockedBy || periodLockedAt" data-testid="fin-period-locked-by">
          · {{ periodLockedBy }} {{ periodLockedAt }}
        </span>
      </div>
      <p v-if="periodError" class="hint" data-testid="fin-period-error" style="color: var(--red); margin-top: 8px">
        {{ periodError }}
      </p>
    </div>

    <div v-if="lastRed.length" data-testid="fin-lock-red-entries" class="hint" style="color: #c0392b; margin-bottom: 8px">
      红冲
      <span v-for="(entry, i) in lastRed" :key="'red' + i">
        {{ entry.item }} （{{ fmt(Math.abs(Number(entry.amount))) }}）
      </span>
    </div>

    <div v-if="rate" class="g3" style="margin-bottom: 12px">
      <div class="card stat">
        <span class="l">已核准场次</span>
        <div class="n">{{ rate.approvedSessionCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">已录入</span>
        <div class="n">{{ rate.costEnteredCount }}</div>
      </div>
      <div class="card stat" data-testid="fin-cost-complete-rate">
        <span class="l">完整率</span>
        <div class="n" :style="{ color: rate.completeRate >= 95 ? 'var(--green)' : 'var(--orange)' }">
          {{ rate.completeRate }}%
        </div>
        <div class="d">BR-107 目标 &gt;95%</div>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab" :class="{ on: tab === 'pending' }" @click="switchTab('pending')">
        待录入清单
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'entered' }" @click="switchTab('entered')">
        已录入管理
      </button>
    </div>

    <form class="qbar" @submit.prevent="loadTab">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 180px" />
      <select v-if="tab === 'entered'" v-model="query.entryStatus" style="width: 120px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="SUBMITTED">已提交</option>
        <option value="CONFIRMED">已核准</option>
      </select>
      <select
        v-if="tab === 'entered'"
        v-model="query.platform"
        data-testid="fin-cost-platform-filter"
        style="width: 140px"
      >
        <option value="">全部平台</option>
        <option v-for="opt in platformOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadTab">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-cost-filter-reset" @click="resetQuery">重置</button>
    </form>

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div v-if="confirmOpen" class="mask on" style="z-index: 140" data-testid="fin-cost-confirm-dialog">
      <div class="card" style="position: fixed; z-index: 150; left: 50%; top: 28%; transform: translateX(-50%); width: 420px; padding: 16px">
        <b>核准成本</b>
        <p>成本合计 {{ yuan(confirmTotal) }}</p>
        <p>核准后 5 分钟内自动计算利润</p>
        <div class="acts" style="gap: 8px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-cost-confirm-ok" @click="submitConfirm">确认</button>
          <button class="btn btn-sec btn-sm" type="button" @click="confirmOpen = false">取消</button>
        </div>
      </div>
    </div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table v-if="tab === 'pending'">
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>标题</th>
              <th>平台</th>
              <th>GMV</th>
              <th>退款</th>
              <th>核准时间</th>
              <th>超 48h</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!pendingRows.length">
              <td colspan="8">
                <div class="empty" data-testid="fin-cost-pending-empty">
                  <div class="et">{{ pendingEmptyText }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in pendingRows" v-else :key="row.sessionCode">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.sessionTitle }}</td>
              <td>{{ row.platform }}</td>
              <td class="num">¥{{ fmt(row.gmv) }}</td>
              <td class="num">¥{{ fmt(row.refund) }}</td>
              <td>{{ row.approvedAt || '—' }}</td>
              <td>
                <span v-if="row.isOver48h" class="tag" style="background: rgba(255, 59, 48, 0.12); color: #c0392b">是</span>
                <span v-else>否</span>
              </td>
              <td>
                <button class="btn btn-pri btn-sm" type="button" @click="openEntry(row)">录入</button>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-cost-ledger-jump"
                  @click="jumpLedger(String(row.sessionCode || ''))"
                >
                  对账
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <table v-else>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>平台</th>
              <th>成本合计</th>
              <th>状态</th>
              <th>录入人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!enteredRows.length">
              <td colspan="6">
                <div class="empty" data-testid="fin-cost-entered-empty">
                  <div class="et">{{ enteredEmptyText }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in enteredRows" v-else :key="row.id">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.platform }}</td>
              <td class="num">¥{{ fmt(row.totalCost) }}</td>
              <td>{{ statusLabel(row.entryStatus) }}</td>
              <td>{{ row.entryUserName || row.entryUserId }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="viewDetail(row.sessionCode)">详情</button>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-cost-ledger-jump"
                  @click="jumpLedger(String(row.sessionCode || ''))"
                >
                  对账
                </button>
                <button
                  v-if="row.entryStatus === 'SUBMITTED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  @click="confirmCost(row.sessionCode)"
                >
                  核准
                </button>
                <button
                  v-if="row.entryStatus === 'CONFIRMED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="fin-cost-correction-open"
                  @click="openCorrection(row.sessionCode)"
                >
                  更正
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer
      :open="drawerOpen"
      :title="'成本录入 · ' + form.sessionCode"
      width="720px"
      @close="drawerOpen = false"
    >
      <p class="hint">GMV / 退款来自 LIVE 下播核准数据，财务侧只读（FIN-C-R2）</p>
      <p v-if="error" data-testid="fin-cost-entry-error" class="hint" style="color: var(--red)">{{ error }}</p>
      <div class="form-grid">
        <div>
          <label>平台<input :value="platformLabel(form.platform)" data-testid="fin-cost-platform" disabled /></label>
        </div>
        <div>
          <label>GMV（只读）<input :value="'¥' + fmt(form.costGmv)" disabled /></label>
        </div>
        <div>
          <label>退款（只读）<input :value="'¥' + fmt(form.costRefund)" disabled /></label>
        </div>
        <div>
          <label>分成方式
            <select v-model="form.shareCostType" data-testid="fin-cost-share-type">
              <option value="MANUAL">手工</option>
              <option value="ENGINE">引擎计算</option>
            </select>
          </label>
        </div>
        <div>
          <label>佣金率<i class="req">*</i><input v-model="form.commissionRate" type="number" step="0.0001" min="0" max="1" /></label>
          <div v-if="fieldErrors.commissionRate" class="ferr">{{ fieldErrors.commissionRate }}</div>
        </div>
        <div>
          <label>投放成本<i class="req">*</i><input v-model="form.adCost" type="number" step="0.01" min="0" /></label>
          <div v-if="fieldErrors.adCost" class="ferr">{{ fieldErrors.adCost }}</div>
        </div>
        <div>
          <label>冲话费摊销<i class="req">*</i><input v-model="form.rechargeCost" type="number" step="0.01" min="0" /></label>
          <div v-if="fieldErrors.rechargeCost" class="ferr">{{ fieldErrors.rechargeCost }}</div>
        </div>
        <div>
          <label>固定成本<i class="req">*</i><input v-model="form.fixedCost" type="number" step="0.01" min="0" /></label>
          <div v-if="fieldErrors.fixedCost" class="ferr">{{ fieldErrors.fixedCost }}</div>
        </div>
        <div>
          <label>样品成本<i class="req">*</i><input v-model="form.sampleCost" type="number" step="0.01" min="0" /></label>
          <div v-if="fieldErrors.sampleCost" class="ferr">{{ fieldErrors.sampleCost }}</div>
        </div>
        <div>
          <label>达人分成<i v-if="form.shareCostType === 'MANUAL'" class="req">*</i><input v-model="form.shareDaren" type="number" step="0.01" min="0" :disabled="form.shareCostType === 'ENGINE'" /></label>
          <div v-if="fieldErrors.shareDaren" class="ferr">{{ fieldErrors.shareDaren }}</div>
        </div>
        <div>
          <label>实名人分成<i v-if="form.shareCostType === 'MANUAL'" class="req">*</i><input v-model="form.shareRealname" type="number" step="0.01" min="0" :disabled="form.shareCostType === 'ENGINE'" /></label>
          <div v-if="fieldErrors.shareRealname" class="ferr">{{ fieldErrors.shareRealname }}</div>
        </div>
      </div>
      <p class="hint" data-testid="fin-cost-entry-total" style="margin-top: 8px">成本合计 {{ yuan(entryTotal) }}</p>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="submitEntry(true)">保存草稿</button>
        <button class="btn btn-pri" type="button" @click="submitEntry(false)">提交</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer
      :open="correctionOpen"
      :title="'成本更正 · ' + form.sessionCode"
      width="720px"
      data-testid="fin-cost-correction-drawer"
      @close="correctionOpen = false"
    >
      <p class="hint">核准后修改走更正单（红冲+蓝补），自动触发利润重算（FIN-P-R3）</p>
      <div v-if="sessionLocked" data-testid="fin-lock-adjust-panel" class="hint" style="margin-bottom: 8px">
        <div>期间已结账。锁后更正须 R4 审批通过后才能红冲调整。</div>
        <div data-testid="fin-lock-adjust-status">{{ lockAdjustStatus || '未申请' }}</div>
        <div class="acts" style="margin-top: 8px">
          <button class="btn btn-sec btn-sm" type="button" data-testid="fin-lock-adjust-apply" @click="applyLockAdjust">
            申请锁后更正
          </button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="fin-lock-adjust-approve"
            :disabled="!lockAdjustTaskId"
            @click="approveLockAdjust"
          >
            审批通过
          </button>
        </div>
      </div>
      <p v-if="correctionError" data-testid="fin-lock-adjust-error" class="hint" style="color: var(--red)">
        {{ correctionError }}
      </p>
      <div class="form-grid">
        <label>佣金率<input v-model.number="form.commissionRate" type="number" step="0.0001" min="0" max="1" /></label>
        <label>投放成本<input v-model.number="form.adCost" type="number" step="0.01" min="0" /></label>
        <label>冲话费摊销<input v-model.number="form.rechargeCost" type="number" step="0.01" min="0" /></label>
        <label>固定成本<input v-model.number="form.fixedCost" type="number" step="0.01" min="0" /></label>
        <label>样品成本<input v-model.number="form.sampleCost" type="number" step="0.01" min="0" /></label>
        <label>达人分成<input v-model.number="form.shareDaren" type="number" step="0.01" min="0" /></label>
        <label>实名人分成<input v-model.number="form.shareRealname" type="number" step="0.01" min="0" /></label>
        <label style="grid-column: 1 / -1">
          更正原因（必填）
          <input
            v-model="correctionReason"
            data-testid="fin-cost-correction-reason"
            placeholder="例如：投放账单补录"
          />
        </label>
      </div>
      <p class="hint" data-testid="fin-cost-correction-reason-hint">更正原因必填，不超过 512 字 · {{ correctionReasonTrimmed }}/512</p>
      <p class="hint" data-testid="fin-cost-correction-total" style="margin-top: 8px">更正后成本合计 {{ yuan(entryTotal) }}</p>
      <div v-if="correctionPreview" class="hint" style="margin-top: 8px">
        <div v-if="correctionPreview.redEntries?.length">
          红冲：
          <span v-for="(e, i) in correctionPreview.redEntries" :key="'r' + i">
            {{ e.item }} {{ e.amount }}
          </span>
        </div>
        <div v-if="correctionPreview.blueEntries?.length">
          蓝补：
          <span v-for="(e, i) in correctionPreview.blueEntries" :key="'b' + i">
            {{ e.item }} +{{ e.amount }}
          </span>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="correctionOpen = false">取消</button>
        <button
          class="btn btn-pri"
          type="button"
          data-testid="fin-cost-correction-submit"
          @click="submitCorrection"
        >
          提交更正
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http } from '../../api/http'

const router = useRouter()

const tab = ref<'pending' | 'entered'>('pending')
const loading = ref(false)
const error = ref('')
const rate = ref<Record<string, any> | null>(null)
const pendingRows = ref<Record<string, any>[]>([])
const enteredRows = ref<Record<string, any>[]>([])
const drawerOpen = ref(false)
const confirmOpen = ref(false)
const confirmTarget = ref('')
const confirmTotal = ref(0)
const correctionOpen = ref(false)
const correctionReason = ref('')
const correctionPreview = ref<Record<string, any> | null>(null)
const correctionError = ref('')
const sessionFinanceStatus = ref('OPEN')
const lockAdjustStatus = ref('')
const lockAdjustTaskId = ref<number | null>(null)
const lastRed = ref<Array<{ item: string; amount: number }>>([])
const periodMonth = ref(currentPeriodMonth())
const periodStatus = ref('OPEN')
const periodError = ref('')
const periodBusy = ref(false)
const periodLockedBy = ref('')
const periodLockedAt = ref('')
const periodClosedNote = ref('')
const periodClosedFor = ref('')
const periodMonthValid = computed(() => /^\d{4}-(0[1-9]|1[0-2])$/.test(periodMonth.value.trim()))
const periodCloseHint = computed(() => {
  if (!periodMonthValid.value) return '期间格式须为 yyyy-MM'
  if (periodStatus.value === 'LOCKED') return '本月已结账，无需重复结账'
  return '结账后该月场次录入/核准/重算冻结；锁后更正须 R4 审批'
})
const pendingFailed = ref(false)
const enteredFailed = ref(false)
const query = reactive({ sessionCode: '', entryStatus: '', platform: '' })
const platformOptions = [
  { value: 'DOUYIN', label: '抖音' },
  { value: 'KUAISHOU', label: '快手' },
  { value: 'WECHAT_CHANNELS', label: '视频号' },
  { value: 'TAOBAO', label: '淘宝' },
  { value: 'JD', label: '京东' },
  { value: 'OTHER', label: '其他' },
]
const fieldErrors = reactive({
  commissionRate: '',
  adCost: '',
  rechargeCost: '',
  fixedCost: '',
  sampleCost: '',
  shareDaren: '',
  shareRealname: '',
})
const costFiltered = ref(false)
const pendingEmptyText = computed(() => {
  if (pendingFailed.value) return '待录入清单加载失败，请重试'
  return costFiltered.value ? '当前筛选无待录入场次' : '暂无待录入场次'
})
const enteredEmptyText = computed(() => {
  if (enteredFailed.value) return '已录入列表加载失败，请重试'
  return costFiltered.value ? '当前筛选无已录入成本' : '暂无已录入成本'
})
const correctionReasonTrimmed = computed(() => correctionReason.value.trim().length)

const sessionLocked = computed(() => sessionFinanceStatus.value === 'LOCKED')

function currentPeriodMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const form = reactive({
  sessionCode: '',
  platform: '',
  accountId: 0,
  ipGroupId: 0,
  costGmv: 0,
  costRefund: 0,
  commissionRate: '' as string | number,
  adCost: '' as string | number,
  rechargeCost: '' as string | number,
  fixedCost: '' as string | number,
  sampleCost: '' as string | number,
  shareDaren: '' as string | number,
  shareRealname: '' as string | number,
  shareCostType: 'MANUAL',
  remark: '',
})

const shareRules = ref<Array<Record<string, any>>>([])

function platformCodes(code: string) {
  const raw = (code || '').toUpperCase()
  const alias: Record<string, string> = {
    DOUYIN: 'DYS',
    KUAISHOU: 'KS',
    WECHAT_CHANNELS: 'WX',
    WECHAT_VIDEO: 'WX',
    TAOBAO: 'TM',
    OTHER: 'OTA',
  }
  return new Set([raw, alias[raw] || raw].filter(Boolean))
}

async function ensureShareRules() {
  if (shareRules.value.length) return
  try {
    const res = await http.get('/fin/share/rules', { params: { pageNo: 1, pageSize: 200, status: 'ENABLED' } })
    shareRules.value = res.data?.data?.list || []
  } catch {
    shareRules.value = []
  }
}

async function previewEngine() {
  if (form.shareCostType !== 'ENGINE') return
  await ensureShareRules()
  const gmv = finite(form.costGmv) || 0
  const refund = finite(form.costRefund) || 0
  const rate = finite(form.commissionRate)
  const commission = round2(gmv * (Number.isFinite(rate) ? rate : 0))
  const gross = round2(gmv - refund - commission)
  const ad = finite(form.adCost)
  const recharge = finite(form.rechargeCost)
  const fixed = finite(form.fixedCost)
  const sample = finite(form.sampleCost)
  const preShare = round2(gross - (Number.isFinite(ad) ? ad : 0) - (Number.isFinite(recharge) ? recharge : 0) - (Number.isFinite(fixed) ? fixed : 0) - (Number.isFinite(sample) ? sample : 0))
  const bases: Record<string, number> = { GMV: gmv, GROSS_PROFIT: gross, NET_PROFIT: preShare }
  const codes = platformCodes(form.platform)
  const winners = new Map<string, Record<string, any>>()
  for (const rule of shareRules.value) {
    if (rule.status && rule.status !== 'ENABLED') continue
    if (rule.rateType !== 'FIXED') continue
    const scope = rule.scope || {}
    const platforms = scope.platforms || []
    const accounts = (scope.accountIds || []).map(Number)
    const groups = (scope.ipGroupIds || []).map(Number)
    if (platforms.length && !platforms.some((item: string) => codes.has(String(item).toUpperCase()))) continue
    if (accounts.length && !accounts.includes(Number(form.accountId))) continue
    if (groups.length && !groups.includes(Number(form.ipGroupId))) continue
    const prev = winners.get(rule.shareTarget)
    if (!prev || Number(rule.priority) > Number(prev.priority) || (Number(rule.priority) === Number(prev.priority) && Number(rule.id) > Number(prev.id))) {
      winners.set(rule.shareTarget, rule)
    }
  }
  const amountOf = (target: string) => {
    const rule = winners.get(target)
    if (!rule) return 0
    const base = bases[rule.baseType] ?? preShare
    return round2(Math.max(base, 0) * Number(rule.fixedRate || 0))
  }
  form.shareDaren = amountOf('DAREN')
  form.shareRealname = amountOf('REALNAME')
}

function platformLabel(code: string) {
  return platformOptions.find((item) => item.value === code)?.label || ({ DYS: '抖音', KS: '快手', WX: '视频号', TM: '淘宝', OTA: '其他' } as Record<string, string>)[code] || code || '—'
}

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function yuan(n: unknown) {
  return `¥${fmt(n)}`
}

function round2(n: number) {
  return Math.round(n * 100) / 100
}

function finite(n: unknown) {
  const value = Number(n)
  return Number.isFinite(value) ? value : Number.NaN
}

const entryTotal = computed(() => {
  const rate = finite(form.commissionRate)
  const gmv = finite(form.costGmv)
  const commission = round2((Number.isFinite(gmv) ? gmv : 0) * (Number.isFinite(rate) ? rate : 0))
  const parts = [form.adCost, form.rechargeCost, form.fixedCost, form.sampleCost, form.shareDaren, form.shareRealname]
  const extra = parts.reduce((acc, raw) => {
    const value = finite(raw)
    return acc + (Number.isFinite(value) ? value : 0)
  }, 0)
  return round2(commission + extra)
})

function moneyError(raw: unknown) {
  const value = finite(raw)
  if (!Number.isFinite(value) || value < 0) return '1001 金额不能为负'
  if (Math.abs(value * 100 - Math.round(value * 100)) > 1e-6) return '1001 金额最多两位小数'
  return ''
}

function blank(raw: unknown) {
  return raw === '' || raw === null || raw === undefined
}

function entryFormError() {
  fieldErrors.commissionRate = ''
  fieldErrors.adCost = ''
  fieldErrors.rechargeCost = ''
  fieldErrors.fixedCost = ''
  fieldErrors.sampleCost = ''
  fieldErrors.shareDaren = ''
  fieldErrors.shareRealname = ''
  const issues: string[] = []
  if (blank(form.commissionRate)) {
    fieldErrors.commissionRate = '必填项，请填写'
    issues.push('必填项，请填写')
  } else {
    const rate = finite(form.commissionRate)
    if (!Number.isFinite(rate) || rate <= 0 || rate > 1) {
      fieldErrors.commissionRate = '1001 佣金率须大于 0 且不超过 1'
      issues.push(fieldErrors.commissionRate)
    }
  }
  const amounts: Array<['adCost' | 'rechargeCost' | 'fixedCost' | 'sampleCost' | 'shareDaren' | 'shareRealname', unknown]> = [
    ['adCost', form.adCost],
    ['rechargeCost', form.rechargeCost],
    ['fixedCost', form.fixedCost],
    ['sampleCost', form.sampleCost],
  ]
  if (form.shareCostType !== 'ENGINE') {
    amounts.push(['shareDaren', form.shareDaren], ['shareRealname', form.shareRealname])
  }
  for (const [key, raw] of amounts) {
    if (blank(raw)) {
      fieldErrors[key] = '必填项，请填写'
      issues.push('必填项，请填写')
      continue
    }
    const msg = moneyError(raw)
    if (msg) {
      fieldErrors[key] = msg
      issues.push(msg)
    }
  }
  return issues.join('；')
}

function failMsg(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'msg' in err) {
    const msg = (err as { msg?: string }).msg
    if (msg) return msg
  }
  return fallback
}

function statusLabel(s: string) {
  const map: Record<string, string> = { DRAFT: '草稿', SUBMITTED: '已提交', CONFIRMED: '已核准' }
  return map[s] || s
}

async function loadRate() {
  const res = await http.get('/fin/cost/complete-rate')
  if (res.data?.code === 0) rate.value = res.data.data
}

function markCostFiltered() {
  costFiltered.value = Boolean(
    query.sessionCode.trim() || (tab.value === 'entered' && (query.entryStatus || query.platform)),
  )
}

function jumpLedger(code: string) {
  const session = code.trim()
  if (!session) return
  router.push({ path: '/ims/fin/ledger', query: { sessionCode: session } })
}

function resetQuery() {
  query.sessionCode = ''
  query.entryStatus = ''
  query.platform = ''
  loadTab()
}

async function loadPending() {
  loading.value = true
  error.value = ''
  pendingFailed.value = false
  markCostFiltered()
  try {
    const res = await http.get('/fin/cost/pending-sessions', {
      params: { pageNo: 1, pageSize: 50, sessionCode: query.sessionCode || undefined },
    })
    pendingRows.value = res.data.data?.list || []
  } catch (err) {
    pendingRows.value = []
    pendingFailed.value = true
    error.value = failMsg(err, '待录入清单加载失败')
  } finally {
    loading.value = false
  }
}

async function loadEntered() {
  loading.value = true
  error.value = ''
  enteredFailed.value = false
  markCostFiltered()
  try {
    const res = await http.get('/fin/cost/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        entryStatus: query.entryStatus || undefined,
        platform: query.platform || undefined,
      },
    })
    enteredRows.value = res.data.data?.list || []
  } catch (err) {
    enteredRows.value = []
    enteredFailed.value = true
    error.value = failMsg(err, '已录入列表加载失败')
  } finally {
    loading.value = false
  }
}

function loadTab() {
  if (tab.value === 'pending') loadPending()
  else loadEntered()
}

function switchTab(next: 'pending' | 'entered') {
  tab.value = next
  loadTab()
}

function openEntry(row: Record<string, unknown>) {
  error.value = ''
  form.sessionCode = String(row.sessionCode)
  form.platform = String(row.platform || '')
  form.accountId = Number(row.accountId || 0)
  form.ipGroupId = Number(row.ipGroupId || 0)
  form.costGmv = Number(row.gmv || 0)
  form.costRefund = Number(row.refund || 0)
  form.commissionRate = ''
  form.adCost = ''
  form.rechargeCost = ''
  form.fixedCost = ''
  form.sampleCost = ''
  form.shareDaren = ''
  form.shareRealname = ''
  form.shareCostType = 'MANUAL'
  entryFormError()
  fieldErrors.commissionRate = ''
  fieldErrors.adCost = ''
  fieldErrors.rechargeCost = ''
  fieldErrors.fixedCost = ''
  fieldErrors.sampleCost = ''
  fieldErrors.shareDaren = ''
  fieldErrors.shareRealname = ''
  error.value = ''
  drawerOpen.value = true
}

async function submitEntry(asDraft: boolean) {
  const invalid = entryFormError()
  if (invalid) {
    error.value = invalid
    return
  }
  const token = crypto.randomUUID().replace(/-/g, '')
  error.value = ''
  try {
  const res = await http.post(
    `/fin/cost/${form.sessionCode}`,
    {
      commissionRate: Number(form.commissionRate),
      adCost: Number(form.adCost || 0),
      rechargeCost: Number(form.rechargeCost || 0),
      fixedCost: Number(form.fixedCost || 0),
      sampleCost: Number(form.sampleCost || 0),
      shareCostType: form.shareCostType,
      shareDaren: form.shareCostType === 'ENGINE' ? 0 : Number(form.shareDaren || 0),
      shareRealname: form.shareCostType === 'ENGINE' ? 0 : Number(form.shareRealname || 0),
      remark: form.remark,
      asDraft,
    },
    { headers: { clientToken: token } },
  )
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '提交失败'
    return
  }
  drawerOpen.value = false
  await loadRate()
  await loadTab()
  } catch (err) {
    error.value = failMsg(err, '提交失败')
  }
}

function assignFormFromCost(d: Record<string, unknown>) {
  Object.assign(form, {
    sessionCode: d.sessionCode,
    costGmv: d.costGmv,
    costRefund: d.costRefund,
    commissionRate: d.commissionRate,
    adCost: d.adCost,
    rechargeCost: d.rechargeCost,
    fixedCost: d.fixedCost,
    sampleCost: d.sampleCost,
    shareDaren: d.shareDaren,
    shareRealname: d.shareRealname,
    shareCostType: d.shareCostType || 'MANUAL',
    platform: d.platform || form.platform,
  })
}

async function viewDetail(sessionCode: string) {
  const res = await http.get(`/fin/cost/${sessionCode}`)
  if (res.data?.code === 0) {
    assignFormFromCost(res.data.data)
    drawerOpen.value = true
  }
}

async function loadPeriod() {
  const month = periodMonth.value.trim()
  if (month !== periodClosedFor.value) periodClosedNote.value = ''
  if (!periodMonthValid.value) {
    periodError.value = '期间格式须为 yyyy-MM'
    periodStatus.value = 'OPEN'
    return
  }
  periodError.value = ''
  try {
    const res = await http.get('/fin/period', { params: { periodMonth: month } })
    const data = res.data?.data || {}
    periodStatus.value = data.financeStatus || 'OPEN'
    periodLockedBy.value = data.lockedByName || ''
    periodLockedAt.value = data.lockedAt || ''
  } catch (err) {
    periodError.value = failMsg(err, '期间状态加载失败')
  }
}

async function closePeriod() {
  const month = periodMonth.value.trim()
  if (!periodMonthValid.value || periodBusy.value || periodStatus.value === 'LOCKED') return
  periodBusy.value = true
  periodError.value = ''
  try {
    const res = await http.post('/fin/period/close', { periodMonth: month })
    const data = res.data?.data || {}
    periodStatus.value = data.financeStatus || 'LOCKED'
    periodLockedBy.value = data.lockedByName || ''
    periodLockedAt.value = data.lockedAt || ''
    periodClosedFor.value = month
    periodClosedNote.value = data.repeated
      ? `本月已结账，无需重复结账 · ${month}`
      : `已结账 · ${month}。录入、核准、更正均冻结`
    error.value = ''
  } catch (err) {
    periodError.value = failMsg(err, '结账失败')
  } finally {
    periodBusy.value = false
  }
}

async function openCorrection(sessionCode: string) {
  correctionReason.value = ''
  correctionPreview.value = null
  correctionError.value = ''
  lockAdjustStatus.value = ''
  lockAdjustTaskId.value = null
  const res = await http.get(`/fin/cost/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '加载失败'
    return
  }
  assignFormFromCost(res.data.data)
  sessionFinanceStatus.value = String(res.data.data?.financeStatus || 'OPEN')
  correctionOpen.value = true
}

async function applyLockAdjust() {
  correctionError.value = ''
  try {
  const listed = await http.get('/flow/template/list', {
    params: { templateName: '费用报销', status: 'PUBLISHED', pageNo: 1, pageSize: 10 },
  })
  const templates = (listed.data?.data?.list || []) as Array<{ id?: number; templateCode?: string }>
  const tpl = templates.find((row) => row.templateCode === 'FL-REIMB')
  if (!tpl?.id) {
    correctionError.value = '未找到已发布的费用报销流程'
    return
  }
  const title = `锁后更正 ${form.sessionCode}`
  const started = await http.post('/flow/instance', {
    templateId: tpl.id,
    businessKey: `FIN-LOCK-${form.sessionCode}`,
    formData: { title, sessionCode: form.sessionCode },
  })
  if (started.data?.code !== 0) {
    correctionError.value = started.data?.msg || '发起审批失败'
    return
  }
  if (started.data.data?.instanceStatus === 'APPROVED') {
    lockAdjustStatus.value = '已通过'
    lockAdjustTaskId.value = null
    return
  }
  const todos = await http.get('/flow/task/my-todo', { params: { pageNo: 1, pageSize: 50 } })
  const hit = (todos.data?.data?.list || []).find(
    (row: { id?: number; formData?: { title?: string }; taskStatus?: string }) =>
      row.taskStatus === 'PENDING' && row.formData?.title === title,
  )
  if (!hit?.id) {
    correctionError.value = '审批任务未出现在待办'
    return
  }
  lockAdjustTaskId.value = hit.id
  lockAdjustStatus.value = '待审批'
  } catch (err) {
    correctionError.value = failMsg(err, '发起审批失败')
  }
}

async function approveLockAdjust() {
  if (!lockAdjustTaskId.value) return
  correctionError.value = ''
  try {
    await http.put(`/flow/task/${lockAdjustTaskId.value}/handle`, {
      action: 'APPROVE',
      comment: 'R4 锁后更正',
    })
    lockAdjustStatus.value = '已通过'
    lockAdjustTaskId.value = null
  } catch (err) {
    correctionError.value = failMsg(err, '审批失败')
  }
}

async function submitCorrection() {
  correctionError.value = ''
  const reason = correctionReason.value.trim()
  if (!reason) {
    correctionError.value = '1144 更正原因必填'
    error.value = '1144 更正原因必填'
    return
  }
  if (reason.length > 512) {
    correctionError.value = '1001 更正原因不超过 512 字'
    error.value = '1001 更正原因不超过 512 字'
    return
  }
  const invalid = entryFormError()
  if (invalid) {
    correctionError.value = invalid
    error.value = invalid
    return
  }
  const token = crypto.randomUUID().replace(/-/g, '')
  try {
  const res = await http.post(
    `/fin/cost/${form.sessionCode}/correction`,
    {
      correctionReason: correctionReason.value.trim(),
      corrected: {
        commissionRate: form.commissionRate,
        adCost: form.adCost,
        rechargeCost: form.rechargeCost,
        fixedCost: form.fixedCost,
        sampleCost: form.sampleCost,
        shareCostType: form.shareCostType,
        shareDaren: form.shareCostType === 'ENGINE' ? Number(form.shareDaren || 0) : Number(form.shareDaren || 0),
        shareRealname: form.shareCostType === 'ENGINE' ? Number(form.shareRealname || 0) : Number(form.shareRealname || 0),
        remark: form.remark,
        asDraft: false,
      },
    },
    { headers: { clientToken: token } },
  )
  if (res.data?.code !== 0) {
    correctionError.value = res.data?.msg || '更正失败'
    error.value = res.data?.msg || '更正失败'
    return
  }
  correctionPreview.value = res.data.data
  lastRed.value = (res.data.data?.redEntries || []) as Array<{ item: string; amount: number }>
  correctionOpen.value = false
  error.value = ''
  await loadEntered()
  } catch (err) {
    const msg = failMsg(err, '更正失败')
    correctionError.value = msg
    error.value = msg
  }
}

function confirmCost(sessionCode: string) {
  const row = enteredRows.value.find((item) => item.sessionCode === sessionCode)
  confirmTarget.value = sessionCode
  confirmTotal.value = Number(row?.totalCost || 0)
  confirmOpen.value = true
}

async function submitConfirm() {
  const sessionCode = confirmTarget.value
  if (!sessionCode) return
  confirmOpen.value = false
  try {
    const res = await http.put(`/fin/cost/${sessionCode}/confirm`)
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '核准失败'
      return
    }
    await loadRate()
    await loadEntered()
  } catch (err) {
    error.value = failMsg(err, '核准失败')
  }
}

watch(
  () => [form.shareCostType, form.commissionRate, form.adCost, form.rechargeCost, form.fixedCost, form.sampleCost, form.costGmv, form.costRefund, form.platform],
  () => {
    if (form.shareCostType === 'ENGINE') void previewEngine()
  },
)

onMounted(async () => {
  await loadPeriod()
  await loadRate()
  await loadPending()
})
</script>
