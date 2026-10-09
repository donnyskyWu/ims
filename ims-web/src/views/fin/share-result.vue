<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>分成单管理</h1>
        <div class="sub">FIN-003 · 财务审 + 业务审 → 发放 · 负向调整在发放接口红冲（1150 / 1144）· #90</div>
      </div>
    </div>

    <form class="qbar" @submit.prevent="search">
      <input
        v-model="query.sessionCode"
        placeholder="场次 ID"
        style="width: 220px"
        data-testid="fin-share-filter-session"
      />
      <select v-model="query.shareTarget" style="width: 120px" data-testid="fin-share-filter-target">
        <option value="">全部对象</option>
        <option value="DAREN">达人</option>
        <option value="REALNAME">实名人</option>
        <option value="TEAM">团队</option>
      </select>
      <select v-model="query.status" style="width: 140px" data-testid="fin-share-filter-status">
        <option value="">全部状态</option>
        <option value="PENDING_AUDIT">待审</option>
        <option value="AUDITED">已审</option>
        <option value="PAID_OFF">已发放</option>
        <option value="REVERSED">已冲销</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" data-testid="fin-share-filter-query" @click="search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="fin-share-filter-reset" @click="resetQuery">重置</button>
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
              <td colspan="9">
                <div class="empty" data-testid="fin-share-empty">
                  <div class="et">{{ shareEmptyText }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.ruleName }}</td>
              <td>{{ targetLabel(row.shareTarget) }}</td>
              <td>{{ row.targetRefName }}</td>
              <td class="num">¥{{ fmt(row.shareBase) }}</td>
              <td class="num">¥{{ fmt(row.shareAmount) }}</td>
              <td>{{ auditProgress(row) }}</td>
              <td>{{ statusLabel(row.status, row) }}</td>
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
      <div class="pager" data-testid="fin-share-pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" data-testid="fin-share-page-prev" @click="gotoPage(pageNo - 1)">‹</span>
        <span
          v-for="n in pageList"
          :key="n"
          class="pg-n"
          :class="{ on: n === pageNo }"
          @click="gotoPage(n)"
        >
          {{ n }}
        </span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" data-testid="fin-share-page-next" @click="gotoPage(pageNo + 1)">›</span>
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
          <span>发放备注</span>
          <input v-model="payoffNote" data-testid="fin-share-payoff-note" maxlength="256" />
        </label>
        <p v-if="payoffError" class="hint" data-testid="fin-share-payoff-error" style="color: var(--red)">
          {{ payoffError }}
        </p>
        <div class="drawer-f">
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="fin-share-payoff-submit"
            :disabled="payoffBusy"
            @click="submitPayoff"
          >
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
import { errorMessage, http } from '../../api/http'

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
}

const loading = ref(false)
const error = ref('')
const rows = ref<ShareRow[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = 20
const query = reactive({ sessionCode: '', shareTarget: '', status: '' })
const payoffOpen = ref(false)
const payoffRow = ref<ShareRow | null>(null)
const payoffNote = ref('')
const payoffError = ref('')
const payoffBusy = ref(false)
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
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const pages: number[] = []
  for (let n = start; n <= Math.min(pageCount.value, start + 4); n += 1) pages.push(n)
  return pages
})
const shareFiltered = computed(() => Boolean(query.sessionCode.trim() || query.shareTarget || query.status))
const shareEmptyText = computed(() => (shareFiltered.value ? '当前筛选无分成单' : '暂无分成单（需先核准成本）'))

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
        pageNo: pageNo.value,
        pageSize,
        sessionCode: query.sessionCode.trim() || undefined,
        shareTarget: query.shareTarget || undefined,
        status: query.status || undefined,
      },
    })
    rows.value = res.data.data?.list || []
    total.value = Number(res.data.data?.total || 0)
  } catch (err) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  return loadList()
}

function resetQuery() {
  query.sessionCode = ''
  query.shareTarget = ''
  query.status = ''
  pageNo.value = 1
  return loadList()
}

function gotoPage(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  return loadList()
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
  payoffError.value = ''
  payoffBusy.value = false
  payoffOpen.value = true
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
  if (!payoffRow.value || payoffBusy.value) return
  payoffBusy.value = true
  payoffError.value = ''
  try {
    await http.put(`/fin/share/result/${payoffRow.value.id}/payoff`, {
      payoffNote: payoffNote.value.trim(),
    })
    payoffOpen.value = false
    await loadList()
  } catch (err) {
    const body = err as { code?: number; msg?: string }
    payoffError.value = `${body?.code ?? ''} ${body?.msg || errorMessage(err)}`.trim()
  } finally {
    payoffBusy.value = false
  }
}

onMounted(loadList)
</script>
