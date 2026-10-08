<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>成本核算</h1>
        <div class="sub">FIN-001 · 场次成本录入 · 11 FIN（与账号财务 COST 分菜单）</div>
      </div>
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
      <div class="card stat">
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
              <td colspan="8"><div class="empty"><div class="et">暂无待录入场次</div></div></td>
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
            <tr v-for="row in enteredRows" :key="row.id">
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.platform }}</td>
              <td class="num">¥{{ fmt(row.totalCost) }}</td>
              <td>{{ statusLabel(row.entryStatus) }}</td>
              <td>{{ row.entryUserName || row.entryUserId }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="viewDetail(row.sessionCode)">详情</button>
                <button
                  v-if="row.entryStatus === 'SUBMITTED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  @click="confirmCost(row.sessionCode)"
                >
                  核准
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer" style="width: 720px">
        <div class="drawer-h">
          <b>成本录入 · {{ form.sessionCode }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <p class="hint">GMV / 退款来自 LIVE 下播核准数据，财务侧只读（FIN-C-R2）</p>
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
        <div class="drawer-f">
          <button class="btn btn-sec" type="button" @click="submitEntry(true)">保存草稿</button>
          <button class="btn btn-pri" type="button" @click="submitEntry(false)">提交</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

const tab = ref<'pending' | 'entered'>('pending')
const loading = ref(false)
const error = ref('')
const rate = ref<Record<string, unknown> | null>(null)
const pendingRows = ref<Record<string, unknown>[]>([])
const enteredRows = ref<Record<string, unknown>[]>([])
const drawerOpen = ref(false)
const query = reactive({ sessionCode: '', entryStatus: '' })

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

function statusLabel(s: string) {
  const map: Record<string, string> = { DRAFT: '草稿', SUBMITTED: '已提交', CONFIRMED: '已核准' }
  return map[s] || s
}

async function loadRate() {
  const res = await http.get('/fin/cost/complete-rate')
  if (res.data?.code === 0) rate.value = res.data.data
}

async function loadPending() {
  loading.value = true
  error.value = ''
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
}

async function viewDetail(sessionCode: string) {
  const res = await http.get(`/fin/cost/${sessionCode}`)
  if (res.data?.code === 0) {
    const d = res.data.data
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
    drawerOpen.value = true
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
  await loadRate()
  await loadPending()
})
</script>
