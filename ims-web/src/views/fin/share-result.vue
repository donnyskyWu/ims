<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>分成单管理</h1>
        <div class="sub">FIN-003 · 利润核算后自动生成 · 财务审 + 业务审 → 发放 PAID_OFF · #57</div>
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
              <td>{{ statusLabel(row.status) }}</td>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

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
}

const loading = ref(false)
const error = ref('')
const rows = ref<ShareRow[]>([])
const query = reactive({ sessionCode: '', shareTarget: '', status: '' })
const payoffOpen = ref(false)
const payoffRow = ref<ShareRow | null>(null)
const payoffNote = ref('')

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

function statusLabel(value: string) {
  const map: Record<string, string> = {
    PENDING_AUDIT: '待审',
    AUDITED: '已审',
    PAID_OFF: '已发放',
    REVERSED: '已冲销',
  }
  return map[value] || value
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
  payoffOpen.value = true
}

async function submitPayoff() {
  if (!payoffRow.value) return
  error.value = ''
  const res = await http.put(`/fin/share/result/${payoffRow.value.id}/payoff`, {
    payoffNote: payoffNote.value,
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
