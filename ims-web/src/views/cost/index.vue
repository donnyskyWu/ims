<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>账号成本与 ROI</h1>
        <div class="sub">采购/过程成本；营收来自 Football 订单 WebAPI · 08b COST</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec" type="button" disabled>导出</button>
        <button v-if="tab === 'cost'" class="btn btn-pri" type="button" @click="openProcess">登记过程成本</button>
      </div>
    </div>
    <p v-if="hint" class="hint" style="margin-bottom: 8px">{{ hint }}</p>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'cost' }" @click="tab = 'cost'">成本登记</div>
      <div class="tab" :class="{ on: tab === 'roi' }" @click="tab = 'roi'; loadRoi()">账号 ROI</div>
      <div class="tab" :class="{ on: tab === 'orders' }" @click="tab = 'orders'; loadOrders()">Football 订单</div>
    </div>

    <template v-if="tab === 'cost'">
      <form class="qbar" @submit.prevent="loadAccountCost">
        <select v-model="selectedAccountId" style="width: 220px" required>
          <option value="">选择账号</option>
          <option v-for="a in accountOptions" :key="a.id" :value="a.id">{{ a.label }}</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div v-if="costDetail" class="tbl-block">
        <div class="card" style="padding: 14px 16px; margin-bottom: 12px">
          <div class="rowline" style="justify-content: space-between; flex-wrap: wrap; gap: 8px">
            <div>
              <b>采购成本</b>
              <span class="hint" style="margin-left: 8px">单行 · PUT purchase</span>
            </div>
            <button class="btn btn-sec btn-sm" type="button" @click="savePurchase">保存采购</button>
          </div>
          <div class="qbar" style="margin-top: 10px; padding: 0">
            <input v-model.number="purchaseForm.amount" type="number" step="0.01" placeholder="金额" style="width: 120px" />
            <input v-model="purchaseForm.period" placeholder="期间 YYYY-MM" style="width: 120px" />
            <input v-model="purchaseForm.payMethod" placeholder="支付方式" style="width: 100px" />
          </div>
          <p v-if="costDetail.purchase" class="hint" style="margin-top: 8px">
            当前 ¥{{ fmt(costDetail.purchase.amount) }} · {{ costDetail.purchase.period || '—' }}
          </p>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>类型</th>
                <th>子类</th>
                <th>金额</th>
                <th>期间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!costDetail.processCosts.length">
                <td colspan="5" style="white-space: normal">
                  <div class="empty"><div class="et">暂无过程成本</div></div>
                </td>
              </tr>
              <tr v-for="row in costDetail.processCosts" v-else :key="row.id">
                <td>过程成本</td>
                <td>{{ row.processSubtype || '—' }}</td>
                <td class="num">¥{{ fmt(row.amount) }}</td>
                <td class="num">{{ row.period || '—' }}</td>
                <td><button class="btn-txt btn" type="button" @click="removeProcess(row.id)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="hint" style="margin-top: 8px">
          合计成本 ¥{{ fmt(costDetail.totalCost) }}（与场次财务 FIN 分菜单，禁止混读）
        </p>
      </div>
      <div v-else class="empty" style="margin-top: 24px">
        <div class="et">请选择账号查看成本</div>
      </div>
    </template>

    <template v-else-if="tab === 'roi'">
      <form class="qbar" @submit.prevent="loadRoi">
        <input v-model="roiRange.start" type="date" style="width: 140px" />
        <input v-model="roiRange.end" type="date" style="width: 140px" />
        <select v-model="roiRange.dimension" style="width: 120px">
          <option value="ACCOUNT">账号</option>
          <option value="IP_GROUP">IP 组</option>
          <option value="COMPANY">公司</option>
          <option value="PERSON">人员</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <p class="hint">账号粒度；营收来自 Football 订单 WebAPI 日汇总</p>
      <div v-if="roi?.revenueDelayed" class="hint" style="color: var(--orange); margin-bottom: 8px">
        {{ roi.revenueDelayHint || '数据延迟' }}（营收不可用，未写入 0）
      </div>
      <div v-if="roi" class="card" style="padding: 14px 16px; margin-bottom: 12px">
        <div class="rowline" style="gap: 24px; flex-wrap: wrap">
          <span>成本 <b class="num">¥{{ fmt(roi.totalCost) }}</b></span>
          <span>
            营收
            <b class="num">{{ roi.revenueDelayed ? '数据延迟' : `¥${fmt(roi.totalRevenue)}` }}</b>
          </span>
          <span>ROI <b>{{ roi.roi ?? '—' }}</b></span>
        </div>
      </div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>成本</th>
                <th>营收</th>
                <th>ROI</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!roi?.details?.length">
                <td colspan="4"><div class="empty"><div class="et">暂无数据</div></div></td>
              </tr>
              <tr v-for="row in roi?.details || []" :key="row.name">
                <td>{{ row.name }}</td>
                <td class="num">¥{{ fmt(row.cost) }}</td>
                <td class="num">{{ row.revenueDelayed ? '数据延迟' : `¥${fmt(row.revenue)}` }}</td>
                <td class="num">{{ row.roi ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else>
      <form class="qbar" @submit.prevent="loadOrders">
        <input v-model="orderRange.start" type="date" style="width: 140px" />
        <input v-model="orderRange.end" type="date" style="width: 140px" />
        <input v-model="orderRange.authorId" placeholder="authorId" style="width: 100px" />
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div v-if="ordersDelay" class="hint" style="color: var(--orange); margin-bottom: 8px">数据延迟</div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>订单号</th>
                <th>实付</th>
                <th>状态</th>
                <th>类型</th>
                <th>支付时间</th>
                <th>authorId</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="ordersDelay">
                <td colspan="6"><div class="empty"><div class="et">Football 订单源不可用</div></div></td>
              </tr>
              <tr v-else-if="!orderRows.length">
                <td colspan="6"><div class="empty"><div class="et">暂无订单</div></div></td>
              </tr>
              <tr v-for="row in orderRows" v-else :key="row.id">
                <td class="mono">{{ row.orderNo }}</td>
                <td class="num">¥{{ fmt(row.payAmount) }}</td>
                <td>{{ row.status }}</td>
                <td>{{ row.orderType }}</td>
                <td>{{ row.payTime || '—' }}</td>
                <td>{{ row.authorId }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useUserStore } from '../../stores/user'

const user = useUserStore()
const tab = ref<'cost' | 'roi' | 'orders'>('cost')
const hint = ref('')
const accountOptions = ref<{ id: string; label: string }[]>([])
const selectedAccountId = ref('')
const costDetail = ref<any>(null)
const purchaseForm = ref({ amount: 0, period: '', payMethod: '' })
const processForm = ref({ amount: 860, period: '2026-09', processSubtype: 'PROCESS_RECHARGE' })
const roiRange = ref({ start: '2026-09-01', end: '2026-09-30', dimension: 'ACCOUNT' })
const roi = ref<any>(null)
const orderRange = ref({ start: '2026-09-01', end: '2026-09-30', authorId: '' })
const orderRows = ref<any[]>([])
const ordersDelay = ref(false)

function authHeaders() {
  return { Authorization: `Bearer ${user.accessToken}` }
}

async function apiGet(url: string, params?: Record<string, unknown>) {
  const res = await axios.get(`/admin-api/ims${url}`, { params, headers: authHeaders() })
  return res.data
}

async function apiPut(url: string, body?: unknown) {
  const res = await axios.put(`/admin-api/ims${url}`, body, { headers: authHeaders() })
  return res.data
}

async function apiPost(url: string, body?: unknown) {
  const res = await axios.post(`/admin-api/ims${url}`, body, { headers: authHeaders() })
  return res.data
}

async function apiDelete(url: string) {
  const res = await axios.delete(`/admin-api/ims${url}`, { headers: authHeaders() })
  return res.data
}

function fmt(n: unknown) {
  const v = Number(n)
  if (Number.isNaN(v)) return '—'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAccounts() {
  const res = await apiGet('/corp/account/page', { platformType: 'DOUYIN', pageNo: 1, pageSize: 100 })
  if (res.code !== 0) {
    hint.value = res.msg || '账号列表加载失败'
    return
  }
  accountOptions.value = (res.data?.list || []).map((row: any) => ({
    id: String(row.id),
    label: `${row.accountNo} ${row.nickname || row.accountName || ''}`.trim(),
  }))
}

async function loadAccountCost() {
  if (!selectedAccountId.value) return
  hint.value = ''
  const res = await apiGet(`/cost/account/${selectedAccountId.value}`)
  if (res.code !== 0) {
    hint.value = res.msg
    costDetail.value = null
    return
  }
  costDetail.value = res.data
  if (res.data.purchase) {
    purchaseForm.value = {
      amount: res.data.purchase.amount,
      period: res.data.purchase.period || '',
      payMethod: res.data.purchase.payMethod || '',
    }
  }
}

async function savePurchase() {
  if (!selectedAccountId.value) return
  const res = await apiPut(`/cost/account/${selectedAccountId.value}/purchase`, purchaseForm.value)
  hint.value = res.code === 0 ? '采购成本已保存' : res.msg
  if (res.code === 0) await loadAccountCost()
}

function openProcess() {
  if (!selectedAccountId.value) {
    hint.value = '请先选择账号'
    return
  }
  void createProcess()
}

async function createProcess() {
  const res = await apiPost(`/cost/account/${selectedAccountId.value}/process`, processForm.value)
  hint.value = res.code === 0 ? '过程成本已登记' : res.msg
  if (res.code === 0) await loadAccountCost()
}

async function removeProcess(id: string) {
  const res = await apiDelete(`/cost/account/${selectedAccountId.value}/process?id=${id}`)
  if (res.code === 0) await loadAccountCost()
  else hint.value = res.msg
}

async function loadRoi() {
  const res = await apiGet('/cost/roi', {
    startDate: roiRange.value.start,
    endDate: roiRange.value.end,
    dimension: roiRange.value.dimension,
    pageNo: 1,
    pageSize: 50,
  })
  if (res.code !== 0) {
    hint.value = res.msg
    roi.value = null
    return
  }
  roi.value = res.data
}

async function loadOrders() {
  ordersDelay.value = false
  orderRows.value = []
  const res = await apiGet('/cost/football-order/list', {
    startDate: orderRange.value.start,
    endDate: orderRange.value.end,
    authorId: orderRange.value.authorId || undefined,
    pageNum: 1,
    pageSize: 20,
  })
  if (res.code === 1232) {
    ordersDelay.value = true
    return
  }
  if (res.code !== 0) {
    hint.value = res.msg
    return
  }
  orderRows.value = res.data?.list || []
}

onMounted(() => {
  void loadAccounts()
})
</script>
