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
          @click="closePeriod"
        >
          结账
        </button>
        <span class="hint">结账后该月场次录入/核准/重算冻结；锁后更正须 R4 审批</span>
      </div>
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
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadTab">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-cost-filter-reset" @click="resetQuery">重置</button>
    </form>

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

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
        <label>GMV（只读）<input :value="'¥' + fmt(form.costGmv)" disabled /></label>
        <label>退款（只读）<input :value="'¥' + fmt(form.costRefund)" disabled /></label>
        <label>佣金率<input v-model.number="form.commissionRate" type="number" step="0.0001" min="0" max="1" /></label>
        <label>投放成本<input v-model.number="form.adCost" type="number" step="0.01" min="0" /></label>
        <label>冲话费摊销<input v-model.number="form.rechargeCost" type="number" step="0.01" min="0" /></label>
        <label>固定成本<input v-model.number="form.fixedCost" type="number" step="0.01" min="0" /></label>
        <label>样品成本<input v-model.number="form.sampleCost" type="number" step="0.01" min="0" /></label>
        <label>达人分成<input v-model.number="form.shareDaren" type="number" step="0.01" min="0" /></label>
        <label>实名人分成<input v-model.number="form.shareRealname" type="number" step="0.01" min="0" /></label>
      </div>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http } from '../../api/http'

const router = useRouter()

const tab = ref<'pending' | 'entered'>('pending')
const loading = ref(false)
const error = ref('')
const rate = ref<Record<string, unknown> | null>(null)
const pendingRows = ref<Record<string, unknown>[]>([])
const enteredRows = ref<Record<string, unknown>[]>([])
const drawerOpen = ref(false)
const correctionOpen = ref(false)
const correctionReason = ref('')
const correctionPreview = ref<Record<string, unknown> | null>(null)
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
const periodMonthValid = computed(() => /^\d{4}-(0[1-9]|1[0-2])$/.test(periodMonth.value.trim()))
const query = reactive({ sessionCode: '', entryStatus: '' })
const costFiltered = ref(false)
const pendingEmptyText = computed(() => (costFiltered.value ? '当前筛选无待录入场次' : '暂无待录入场次'))
const enteredEmptyText = computed(() => (costFiltered.value ? '当前筛选无已录入成本' : '暂无已录入成本'))

const sessionLocked = computed(() => sessionFinanceStatus.value === 'LOCKED')

function currentPeriodMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const form = reactive({
  sessionCode: '',
  costGmv: 0,
  costRefund: 0,
  commissionRate: 0.05,
  adCost: 0,
  rechargeCost: 0,
  fixedCost: 0,
  sampleCost: 0,
  shareDaren: 0,
  shareRealname: 0,
  shareCostType: 'MANUAL',
  remark: '',
})

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  costFiltered.value = Boolean(query.sessionCode.trim() || (tab.value === 'entered' && query.entryStatus))
}

function jumpLedger(code: string) {
  const session = code.trim()
  if (!session) return
  router.push({ path: '/ims/fin/ledger', query: { sessionCode: session } })
}

function resetQuery() {
  query.sessionCode = ''
  query.entryStatus = ''
  loadTab()
}

async function loadPending() {
  loading.value = true
  error.value = ''
  markCostFiltered()
  try {
    const res = await http.get('/fin/cost/pending-sessions', {
      params: { pageNo: 1, pageSize: 50, sessionCode: query.sessionCode || undefined },
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      pendingRows.value = []
      return
    }
    pendingRows.value = res.data.data?.list || []
  } finally {
    loading.value = false
  }
}

async function loadEntered() {
  loading.value = true
  error.value = ''
  markCostFiltered()
  try {
    const res = await http.get('/fin/cost/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        entryStatus: query.entryStatus || undefined,
      },
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      enteredRows.value = []
      return
    }
    enteredRows.value = res.data.data?.list || []
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
  form.sessionCode = String(row.sessionCode)
  form.costGmv = Number(row.gmv || 0)
  form.costRefund = Number(row.refund || 0)
  form.adCost = Number(row.adCost || 0)
  drawerOpen.value = true
}

async function submitEntry(asDraft: boolean) {
  const token = crypto.randomUUID().replace(/-/g, '')
  try {
  const res = await http.post(
    `/fin/cost/${form.sessionCode}`,
    {
      commissionRate: form.commissionRate,
      adCost: form.adCost,
      rechargeCost: form.rechargeCost,
      fixedCost: form.fixedCost,
      sampleCost: form.sampleCost,
      shareCostType: 'MANUAL',
      shareDaren: form.shareDaren,
      shareRealname: form.shareRealname,
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
  if (!periodMonthValid.value) {
    periodError.value = '期间格式须为 yyyy-MM'
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
  if (!correctionReason.value.trim()) {
    correctionError.value = '更正原因必填'
    error.value = '更正原因必填'
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
        shareCostType: 'MANUAL',
        shareDaren: form.shareDaren,
        shareRealname: form.shareRealname,
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

async function confirmCost(sessionCode: string) {
  const res = await http.put(`/fin/cost/${sessionCode}/confirm`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '核准失败'
    return
  }
  await loadRate()
  await loadEntered()
}

onMounted(async () => {
  await loadPeriod()
  await loadRate()
  await loadPending()
})
</script>
