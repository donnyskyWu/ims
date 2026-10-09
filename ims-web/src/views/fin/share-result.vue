<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>分成单管理</h1>
        <div class="sub">FIN-003 · 财务审 + 业务审 → 发放 · 负向调整在发放接口红冲（1150 / 1144）· #90</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 220px" />
      <select v-model="query.shareTarget" style="width: 120px">
        <option value="">全部对象</option>
        <option value="DAREN">达人</option>
        <option value="REALNAME">实名人</option>
      </select>
      <select v-model="query.status" style="width: 140px">
        <option value="">全部状态</option>
        <option value="PENDING_AUDIT">待审</option>
        <option value="AUDITED">已审</option>
        <option value="PAID_OFF">已发放</option>
        <option value="REVERSED">已冲销</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadList">查询</button>
    </form>

    <p v-if="rows.length" class="hint" data-testid="fin-share-split-sum" style="margin: 8px 0">
      拆分合计 {{ fmt(splitSum) }} = 总额 {{ fmt(shareTotal) }}
      <span v-if="splitMatches"> · 金额拆分累计等于总额</span>
    </p>

    <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次号</th>
              <th>规则</th>
              <th>分成对象</th>
              <th>对象名</th>
              <th>基数</th>
              <th>分成金额</th>
              <th>双审</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9"><div class="empty"><div class="et">暂无分成单（需先核准成本）</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.ruleName }}</td>
              <td>{{ targetLabel(row.shareTarget) }}</td>
              <td>{{ row.targetRefName }}</td>
              <td class="num">¥{{ fmt(row.shareBase) }}</td>
              <td class="num">¥{{ fmt(row.shareAmount) }}</td>
              <td>{{ auditProgress(row) }}</td>
              <td>
                {{ statusLabel(row.status, row) }}
                <div v-if="row.payoffVoucher?.fileName" class="hint" data-testid="fin-share-voucher-name">
                  {{ row.payoffVoucher.fileName }}
                </div>
              </td>
              <td>
                <button
                  v-if="row.status === 'PENDING_AUDIT' && !row.finAuditPassed"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-audit-finance"
                  @click="audit(row, 'FINANCE', 'APPROVE')"
                >
                  财务审
                </button>
                <button
                  v-if="row.status === 'PENDING_AUDIT' && !row.bizAuditPassed"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-audit-business"
                  @click="audit(row, 'BUSINESS', 'APPROVE')"
                >
                  业务审
                </button>
                <button
                  v-if="row.status === 'AUDITED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="fin-share-payoff-open"
                  @click="openPayoff(row)"
                >
                  发放登记
                </button>
                <button
                  v-if="row.status === 'AUDITED' || row.status === 'PAID_OFF'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-reverse-open"
                  @click="openReverse(row)"
                >
                  冲销
                </button>
                <button
                  v-if="row.status === 'REVERSED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="fin-share-reverse-detail-open"
                  @click="openReverseDetail(row)"
                >
                  冲销明细
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="payoffOpen && payoffRow" class="drawer-mask" @click.self="payoffOpen = false">
      <div class="drawer on" data-testid="fin-share-payoff-drawer" style="width: 480px">
        <div class="drawer-h">
          <b>发放登记 · {{ targetLabel(payoffRow.shareTarget) }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="payoffOpen = false">关闭</button>
        </div>
        <p class="hint">场次 {{ payoffRow.sessionCode }} · 金额 ¥{{ fmt(payoffRow.shareAmount) }}</p>
        <label class="fld">
          <span>发放凭证</span>
          <input type="file" data-testid="fin-share-payoff-voucher" @change="onVoucher" />
        </label>
        <p v-if="voucherFile" class="hint" data-testid="fin-share-payoff-voucher-name">{{ voucherFile.fileName }}</p>
        <label class="fld">
          <span>发放备注</span>
          <input v-model="payoffNote" data-testid="fin-share-payoff-note" maxlength="256" />
        </label>
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-payoff-submit" @click="submitPayoff">
            确认发放
          </button>
        </div>
      </div>
    </div>

    <div v-if="reverseOpen && reverseRow" class="drawer-mask" @click.self="reverseOpen = false">
      <div class="drawer on" data-testid="fin-share-reverse-drawer" style="width: 520px">
        <div class="drawer-h">
          <b>冲销 · {{ targetLabel(reverseRow.shareTarget) }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="reverseOpen = false">关闭</button>
        </div>
        <p class="hint">场次 {{ reverseRow.sessionCode }} · 原金额 ¥{{ fmt(reverseRow.shareAmount) }} · 红冲不改原金额</p>
        <label class="fld">
          <span>冲销原因</span>
          <input v-model="reverseReason" data-testid="fin-share-reverse-reason" maxlength="512" />
        </label>
        <p v-if="reverseError" class="hint" data-testid="fin-share-reverse-error" style="color: var(--red)">
          {{ reverseError }}
        </p>
        <div v-if="reverseRed.length" data-testid="fin-share-red-entries">
          <p v-for="entry in reverseRed" :key="entry.item" class="hint" style="color: var(--red)">
            {{ entry.item }} <span data-testid="fin-share-red-amount">{{ redText(entry.amount) }}</span>
          </p>
          <p v-if="reverseAudit" class="hint" data-testid="fin-share-reverse-audit">
            {{ reverseAudit.actorName }} · {{ reverseAudit.reversedAt }} · {{ reverseAudit.reason }} ·
            {{ reverseAudit.fromStatus }}
          </p>
        </div>
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-reverse-submit" @click="submitReverse">
            确认冲销
          </button>
        </div>
      </div>
    </div>

    <div v-if="detailOpen && detailRow" class="drawer-mask" @click.self="detailOpen = false">
      <div class="drawer on" data-testid="fin-share-reverse-detail" style="width: 560px">
        <div class="drawer-h">
          <b>冲销明细 · {{ targetLabel(detailRow.shareTarget) }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="detailOpen = false">关闭</button>
        </div>
        <p class="hint">{{ detailRow.replaced ? '已冲销（新单已补）' : '已冲销' }} · 场次 {{ detailRow.sessionCode }}</p>
        <p v-for="entry in detailRow.redEntries || []" :key="entry.item" class="hint" style="color: var(--red)">
          {{ entry.item }} {{ redText(entry.amount) }}
        </p>
        <p v-if="detailRow.reverseAudit" class="hint" data-testid="fin-share-reverse-detail-audit">
          {{ detailRow.reverseAudit.actorName }} · {{ detailRow.reverseAudit.reversedAt }} ·
          {{ detailRow.reverseAudit.reason }}
        </p>
        <p v-if="detailRow.replaced" class="hint">补发金额 ¥{{ fmt(detailRow.replacementAmount) }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type RedEntry = { item: string; amount: number }
type ReverseAudit = { actorName?: string; reversedAt?: string; reason?: string; fromStatus?: string }
type ShareRow = {
  id: number
  sessionCode: string
  ruleName: string
  shareTarget: string
  targetRefName: string
  shareBase: number
  shareAmount: number
  status: string
  finAuditPassed?: boolean
  bizAuditPassed?: boolean
  calcDetail?: { shareTotal?: number }
  redEntries?: RedEntry[]
  reverseAudit?: ReverseAudit | null
  replaced?: boolean
  replacementAmount?: number
  payoffVoucher?: { fileName?: string; fileKey?: string } | null
}

const loading = ref(false)
const error = ref('')
const rows = ref<ShareRow[]>([])
const query = reactive({ sessionCode: '', shareTarget: '', status: '' })
const payoffOpen = ref(false)
const payoffRow = ref<ShareRow | null>(null)
const payoffNote = ref('')
const voucherFile = ref<{ fileName: string; fileKey: string } | null>(null)
const reverseOpen = ref(false)
const reverseRow = ref<ShareRow | null>(null)
const reverseReason = ref('')
const reverseError = ref('')
const reverseRed = ref<RedEntry[]>([])
const reverseAudit = ref<ReverseAudit | null>(null)
const detailOpen = ref(false)
const detailRow = ref<ShareRow | null>(null)

const splitSum = computed(() => rows.value.reduce((acc, row) => acc + Number(row.shareAmount || 0), 0))
const shareTotal = computed(() => {
  const totals = rows.value.map((row) => Number(row.calcDetail?.shareTotal ?? NaN)).filter((n) => !Number.isNaN(n))
  if (!totals.length) return splitSum.value
  return totals[0]
})
const splitMatches = computed(() => Math.abs(splitSum.value - shareTotal.value) < 0.01)

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function targetLabel(value: string) {
  const map: Record<string, string> = { DAREN: '达人', REALNAME: '实名人', TEAM: '团队' }
  return map[value] || value
}

function statusLabel(value: string, row?: ShareRow) {
  if (value === 'REVERSED' && row?.replaced) return '已冲销（新单已补）'
  const map: Record<string, string> = {
    PENDING_AUDIT: '待审',
    AUDITED: '已审',
    PAID_OFF: '已发放',
    REVERSED: '已冲销',
  }
  return map[value] || value
}

function redText(amount: number) {
  return `（${fmt(Math.abs(Number(amount || 0)))}）`
}

function auditProgress(row: ShareRow) {
  const fin = row.finAuditPassed ? '财务✓' : '财务—'
  const biz = row.bizAuditPassed ? '业务✓' : '业务—'
  return `${fin} / ${biz}`
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/fin/share/results', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        shareTarget: query.shareTarget || undefined,
        status: query.status || undefined,
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

async function audit(row: ShareRow, auditRole: 'FINANCE' | 'BUSINESS', conclusion: 'APPROVE' | 'REJECT') {
  error.value = ''
  const res = await http.put(`/fin/share/result/${row.id}/audit`, { conclusion, auditRole })
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '审批失败'
    return
  }
  await loadList()
}

function openPayoff(row: ShareRow) {
  payoffRow.value = row
  payoffNote.value = ''
  voucherFile.value = null
  payoffOpen.value = true
}

function onVoucher(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) {
    voucherFile.value = null
    return
  }
  const safe = file.name.replace(/[^\w.\-]+/g, '_') || 'voucher'
  voucherFile.value = { fileName: file.name, fileKey: `voucher/${safe}` }
}

function openReverse(row: ShareRow) {
  reverseRow.value = row
  reverseReason.value = ''
  reverseError.value = ''
  reverseRed.value = []
  reverseAudit.value = null
  reverseOpen.value = true
}

function openReverseDetail(row: ShareRow) {
  detailRow.value = row
  detailOpen.value = true
}

async function submitReverse() {
  if (!reverseRow.value) return
  reverseError.value = ''
  try {
    const res = await http.put(`/fin/share/result/${reverseRow.value.id}/payoff`, {
      reverse: true,
      reverseReason: reverseReason.value,
    })
    reverseRed.value = res.data.data?.redEntries || []
    reverseAudit.value = res.data.data?.reverseAudit || null
    await loadList()
  } catch (err) {
    const body = err as { code?: number; msg?: string }
    reverseError.value = `${body?.code ?? ''} ${body?.msg || '冲销失败'}`.trim()
  }
}

async function submitPayoff() {
  if (!payoffRow.value) return
  error.value = ''
  const res = await http.put(`/fin/share/result/${payoffRow.value.id}/payoff`, {
    payoffNote: payoffNote.value,
    payoffVoucher: voucherFile.value || undefined,
  })
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '发放失败'
    return
  }
  payoffOpen.value = false
  await loadList()
}

onMounted(loadList)
</script>
