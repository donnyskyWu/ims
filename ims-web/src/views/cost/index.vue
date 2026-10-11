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
          <div class="qbar" style="margin-top: 10px; padding: 0; align-items: flex-start">
            <div class="fld" style="width: 160px; margin-bottom: 0">
              <label for="cost-purchase-amount">金额<i class="req">*</i></label>
              <input
                id="cost-purchase-amount"
                v-model="purchaseForm.amount"
                type="number"
                step="0.01"
                placeholder="金额"
                data-testid="cost-purchase-amount"
                :class="{ err: purchaseErrors.amount }"
              />
              <div v-if="purchaseErrors.amount" class="ferr" data-testid="cost-purchase-amount-error">{{ purchaseErrors.amount }}</div>
            </div>
            <div class="fld" style="width: 160px; margin-bottom: 0">
              <label for="cost-purchase-period">期间<i class="req">*</i></label>
              <input
                id="cost-purchase-period"
                v-model="purchaseForm.period"
                placeholder="YYYY-MM"
                data-testid="cost-purchase-period"
                :class="{ err: purchaseErrors.period }"
              />
              <div v-if="purchaseErrors.period" class="ferr" data-testid="cost-purchase-period-error">{{ purchaseErrors.period }}</div>
            </div>
            <div class="fld" style="width: 140px; margin-bottom: 0">
              <label for="cost-purchase-pay">支付方式</label>
              <input id="cost-purchase-pay" v-model="purchaseForm.payMethod" placeholder="支付方式" />
            </div>
          </div>
          <p v-if="purchaseHint" class="hint" style="margin-top: 8px; color: var(--green)" data-testid="cost-purchase-hint">{{ purchaseHint }}</p>
          <p v-if="costDetail.purchase" class="hint" style="margin-top: 8px">
            当前 ¥{{ fmt(costDetail.purchase.amount) }} · {{ costDetail.purchase.period || '—' }}
          </p>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>类型</th>
                <th>金额</th>
                <th>周期</th>
                <th>经办人</th>
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
                <td>{{ row.processSubtypeLabel || subtypeLabel(row.processSubtype) }}</td>
                <td class="num">¥{{ fmt(row.amount) }}</td>
                <td class="num">{{ row.period || '—' }}</td>
                <td>{{ row.handlerUserName || '—' }}</td>
                <td>
                  <button class="btn-txt btn" type="button" @click="editProcess(row)">编辑</button>
                  <button class="btn-txt btn" type="button" @click="removeProcess(row.id)">删除</button>
                </td>
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

    <ProtoDrawer
      :open="processOpen"
      :title="processEditingId ? '编辑过程成本' : '登记过程成本'"
      width="480px"
      @close="processOpen = false"
    >
      <div class="fld">
        <label for="cost-process-type">类型<i class="req">*</i></label>
        <select id="cost-process-type" v-model="processForm.processSubtype" data-testid="cost-process-type" :class="{ err: processErrors.type }">
          <option value="">请选择</option>
          <option v-for="opt in processTypes" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <div v-if="processErrors.type" class="ferr">{{ processErrors.type }}</div>
      </div>
      <div class="fld">
        <label for="cost-process-amount">金额<i class="req">*</i></label>
        <input
          id="cost-process-amount"
          v-model="processForm.amount"
          type="number"
          step="0.01"
          min="0"
          placeholder="金额"
          data-testid="cost-process-amount"
          :class="{ err: processErrors.amount }"
        />
        <div v-if="processErrors.amount" class="ferr">{{ processErrors.amount }}</div>
      </div>
      <div class="fld">
        <label for="cost-process-period">周期<i class="req">*</i></label>
        <input
          id="cost-process-period"
          v-model="processForm.period"
          placeholder="YYYY-MM"
          data-testid="cost-process-period"
          :class="{ err: processErrors.period }"
        />
        <div v-if="processErrors.period" class="ferr">{{ processErrors.period }}</div>
      </div>
      <div class="fld">
        <label for="cost-process-handler">经办人<i class="req">*</i></label>
        <select id="cost-process-handler" v-model="processForm.handlerUserId" data-testid="cost-process-handler" :class="{ err: processErrors.handler }">
          <option value="">请选择</option>
          <option v-for="u in handlerOptions" :key="u.id" :value="u.id">{{ u.label }}</option>
        </select>
        <div v-if="processErrors.handler" class="ferr">{{ processErrors.handler }}</div>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="processOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="cost-process-save" @click="saveProcess">保存</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { useUserStore } from '../../stores/user'

const processTypes = [
  { value: 'PROCESS_RENT', label: '租赁' },
  { value: 'PROCESS_CERT', label: '注册认证' },
  { value: 'PROCESS_RECHARGE', label: '充值投流' },
  { value: 'PROCESS_HUMAN', label: '人力' },
  { value: 'PROCESS_DEVICE', label: '设备' },
  { value: 'PROCESS_OPS', label: '运营' },
  { value: 'PROCESS_OTHER', label: '其他' },
] as const

function subtypeLabel(code: string | null | undefined) {
  return processTypes.find((item) => item.value === code)?.label || code || '—'
}

const user = useUserStore()
const tab = ref<'cost' | 'roi' | 'orders'>('cost')
const hint = ref('')
const accountOptions = ref<{ id: string; label: string }[]>([])
const selectedAccountId = ref('')
const costDetail = ref<any>(null)
const purchaseForm = ref<{ amount: string | number; period: string; payMethod: string }>({
  amount: '',
  period: '',
  payMethod: '',
})
const purchaseErrors = ref({ amount: '', period: '' })
const purchaseHint = ref('')
const processOpen = ref(false)
const processEditingId = ref('')
const processForm = ref({ amount: '' as string | number, period: '', processSubtype: '', handlerUserId: '' })
const processErrors = ref({ type: '', amount: '', period: '', handler: '' })
const handlerOptions = ref<{ id: string; label: string }[]>([])
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
  } else {
    purchaseForm.value = { amount: '', period: '', payMethod: '' }
  }
}

function validatePurchase() {
  const errors = { amount: '', period: '' }
  const raw = purchaseForm.value.amount
  if (raw === '' || raw === null || raw === undefined || Number.isNaN(Number(raw))) {
    errors.amount = '必填项，请填写'
  } else if (Number(raw) < 0) {
    errors.amount = '金额须为非负数'
  }
  if (!String(purchaseForm.value.period || '').trim()) errors.period = '必填项，请填写'
  purchaseErrors.value = errors
  return !errors.amount && !errors.period
}

async function savePurchase() {
  if (!selectedAccountId.value) return
  purchaseHint.value = ''
  if (!validatePurchase()) return
  const res = await apiPut(`/cost/account/${selectedAccountId.value}/purchase`, {
    amount: Number(purchaseForm.value.amount),
    period: purchaseForm.value.period,
    payMethod: purchaseForm.value.payMethod,
  })
  if (res.code === 0) {
    await loadAccountCost()
    purchaseHint.value = '采购成本已保存'
    purchaseErrors.value = { amount: '', period: '' }
    return
  }
  if (res.code === 1001 && String(res.msg || '').includes('非负')) {
    purchaseErrors.value = { ...purchaseErrors.value, amount: '金额须为非负数' }
  }
  purchaseHint.value = ''
  hint.value = res.msg
}

function blankProcessForm() {
  processEditingId.value = ''
  processForm.value = { amount: '', period: '', processSubtype: '', handlerUserId: '' }
  processErrors.value = { type: '', amount: '', period: '', handler: '' }
}

async function loadHandlers() {
  if (handlerOptions.value.length) return
  const res = await apiGet('/system/user/page', { pageNo: 1, pageSize: 100, status: 'ENABLED' })
  if (res.code !== 0) return
  handlerOptions.value = (res.data?.list || []).map((row: any) => ({
    id: String(row.id),
    label: row.nickname ? `${row.nickname}（${row.username}）` : row.username,
  }))
}

async function openProcess() {
  if (!selectedAccountId.value) {
    hint.value = '请先选择账号'
    return
  }
  blankProcessForm()
  await loadHandlers()
  processOpen.value = true
}

function editProcess(row: any) {
  processEditingId.value = String(row.id)
  processForm.value = {
    amount: row.amount,
    period: row.period || '',
    processSubtype: row.processSubtype || '',
    handlerUserId: row.handlerUserId ? String(row.handlerUserId) : '',
  }
  processErrors.value = { type: '', amount: '', period: '', handler: '' }
  void loadHandlers().then(() => {
    processOpen.value = true
  })
}

function validateProcess() {
  const errors = { type: '', amount: '', period: '', handler: '' }
  if (!processForm.value.processSubtype) errors.type = '必填项，请填写'
  const raw = processForm.value.amount
  if (raw === '' || raw === null || raw === undefined || Number.isNaN(Number(raw))) {
    errors.amount = '必填项，请填写'
  } else if (Number(raw) < 0) {
    errors.amount = '金额须为非负数'
  }
  if (!String(processForm.value.period || '').trim()) errors.period = '必填项，请填写'
  if (!processForm.value.handlerUserId) errors.handler = '必填项，请填写'
  processErrors.value = errors
  return !errors.type && !errors.amount && !errors.period && !errors.handler
}

async function saveProcess() {
  if (!selectedAccountId.value || !validateProcess()) return
  const payload = {
    amount: Number(processForm.value.amount),
    period: processForm.value.period,
    processSubtype: processForm.value.processSubtype,
    handlerUserId: Number(processForm.value.handlerUserId),
  }
  const res = processEditingId.value
    ? await apiPut(`/cost/account/${selectedAccountId.value}/process`, { ...payload, id: Number(processEditingId.value) })
    : await apiPost(`/cost/account/${selectedAccountId.value}/process`, payload)
  hint.value = res.code === 0 ? '过程成本已登记' : res.msg
  if (res.code === 0) {
    processOpen.value = false
    await loadAccountCost()
  }
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

<style scoped>
.fld { margin-bottom: 12px; }
</style>
