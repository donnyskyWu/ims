<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>离职归还</h1>
        <div class="sub">ACCT-003 · 归还单未闭环时关闭权限返回 1024</div>
      </div>
      <div class="acts">
        <button v-if="canGenerate" class="btn btn-pri" type="button" data-testid="return-generate-open" @click="openGenerate">手动补建归还单</button>
      </div>
    </div>
    <p class="hint">离职归还单由钉钉离职事件自动生成。名下账号、资产、证件未全部归还或转交时，不能关闭权限。</p>
    <form class="qbar" data-testid="return-filters" @submit.prevent="loadList">
      <input v-model="returnNo" data-testid="return-filter-no" placeholder="归还单号" style="width: 160px" />
      <label>
        离职人
        <input
          v-model="userKeyword"
          data-testid="return-filter-user-search"
          placeholder="搜索姓名"
          style="width: 120px"
        />
        <select v-model="filterUserId" data-testid="return-filter-user" style="width: 160px">
          <option value="">全部</option>
          <option v-for="user in filteredUsers" :key="String(user.id)" :value="String(user.id)">{{ userLabel(user) }}</option>
        </select>
      </label>
      <select v-model="status" data-testid="return-filter-status" style="width: 140px">
        <option value="">全部状态</option>
        <option value="IN_PROGRESS">进行中</option>
        <option value="EXCEPTION_SUSPENDED">异常挂起</option>
        <option value="CLOSED">已闭环</option>
      </select>
      <label>
        生效日起
        <input v-model="timeFrom" data-testid="return-filter-from" type="date" />
      </label>
      <label>
        生效日止
        <input v-model="timeTo" data-testid="return-filter-to" type="date" />
      </label>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="return-filter-search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="return-filter-reset" @click="resetFilters">清空</button>
    </form>
    <p v-if="rangeError" class="hint bad" data-testid="return-filter-msg">{{ rangeError }}</p>
    <p v-if="listError" class="hint bad" data-testid="return-list-error">{{ listError }}</p>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="return-order-table">
          <thead>
            <tr>
              <th>归还单号</th>
              <th>离职人</th>
              <th>部门</th>
              <th>离职生效日</th>
              <th>归还项进度</th>
              <th>状态</th>
              <th>逾期</th>
              <th>闭环时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!orders.length">
              <td colspan="9" style="white-space: normal">
                <div class="empty" data-testid="return-list-empty">
                  <div class="et">{{ returnEmptyTitle }}</div>
                  <div class="es">{{ returnEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in orders" :key="String(row.id)" data-testid="return-order-row">
              <td class="mono" data-testid="return-order-no">{{ row.returnNo }}</td>
              <td>{{ row.userName || row.userNickname }}</td>
              <td data-testid="return-order-dept">{{ row.deptName || '—' }}</td>
              <td>{{ row.resignDate }}</td>
              <td data-testid="return-order-progress">{{ progressText(row) }}</td>
              <td data-testid="return-order-status">
                <span class="tag" :style="statusStyle(String(row.status || ''))">
                  <span class="dot"></span>{{ statusText(String(row.status || '')) }}
                </span>
              </td>
              <td data-testid="return-order-overdue">{{ overdueText(row) }}</td>
              <td data-testid="return-order-closed">{{ closedText(row.closedAt) }}</td>
              <td><button class="btn btn-txt" type="button" data-testid="return-order-open" @click="openOrder(row)">处理</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="generateOpen" title="手动补建归还单" width="480px" @close="generateOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>离职人<i class="req">*</i></label>
          <select v-model="generateUserId" data-testid="return-generate-user">
            <option value="">请选择</option>
            <option v-for="user in users" :key="String(user.id)" :value="String(user.id)">{{ user.nickname || user.username }}</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>离职生效日<i class="req">*</i></label>
          <input v-model="generateDate" data-testid="return-generate-date" type="date" />
        </div>
      </div>
      <p v-if="generateError" class="hint bad" data-testid="return-generate-error">{{ generateError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="generateOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="return-generate-save" :disabled="busy" @click="generate">生成归还单</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" title="归还单处理" width="720px" @close="detailOpen = false">
      <template v-if="detail">
        <p class="hint" data-testid="return-detail-head">
          {{ detail.returnNo }} · {{ detail.userName || detail.userNickname }} · {{ detail.resignDate }} · {{ statusText(String(detail.status || '')) }}
        </p>
        <p class="hint">{{ detail.deptName || '—' }}</p>
        <p v-if="detail.status !== 'CLOSED'" class="hint bad" data-testid="return-freeze-banner">未闭环期间离职人 IMS 登录受限，名下账号/资产冻结</p>
        <div class="acts" style="margin-bottom: 8px">
          <button class="btn btn-sm" :class="itemTab === 'ALL' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="return-item-tab-all" @click="itemTab = 'ALL'">全部</button>
          <button class="btn btn-sm" :class="itemTab === 'ACCOUNT' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="return-item-tab-account" @click="itemTab = 'ACCOUNT'">账号</button>
          <button class="btn btn-sm" :class="itemTab === 'ASSET' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="return-item-tab-asset" @click="itemTab = 'ASSET'">资产</button>
          <button class="btn btn-sm" :class="itemTab === 'CERT' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="return-item-tab-cert" @click="itemTab = 'CERT'">证件</button>
        </div>
        <table data-testid="return-item-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>名称</th>
              <th>当前持有人</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!visibleItems.length">
              <td colspan="5">没有待归还的账号、资产或证件</td>
            </tr>
            <tr v-for="item in visibleItems" :key="String(item.id)" data-testid="return-item-row">
              <td>{{ typeText(String(item.itemType || '')) }}</td>
              <td data-testid="return-item-label">{{ item.itemLabel || item.itemSnapshot }}</td>
              <td data-testid="return-item-holder">{{ item.currentHolder || '—' }}</td>
              <td data-testid="return-item-status">
                <span class="tag" :style="itemStyle(String(item.itemStatus || ''))">{{ itemText(String(item.itemStatus || '')) }}</span>
              </td>
              <td>
                <button class="btn btn-txt" type="button" data-testid="return-item-returned" :disabled="detail.status === 'CLOSED' || item.itemStatus === 'RETURNED'" @click="markReturned(item)">确认归还</button>
                <select v-model="transferUser[String(item.id)]" data-testid="return-item-transfer-user" :disabled="detail.status === 'CLOSED'">
                  <option value="">转交给</option>
                  <option v-for="user in users" :key="String(user.id)" :value="String(user.id)">{{ user.nickname || user.username }}</option>
                </select>
                <button class="btn btn-txt" type="button" data-testid="return-item-transfer" :disabled="detail.status === 'CLOSED'" @click="markTransferred(item)">转交</button>
                <input v-model="disputeRemark[String(item.id)]" data-testid="return-item-dispute-remark" placeholder="争议说明" :disabled="detail.status === 'CLOSED'" />
                <button class="btn btn-txt" type="button" data-testid="return-item-dispute" :disabled="detail.status === 'CLOSED'" @click="markDisputed(item)">标记争议</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="detailError" class="hint bad" data-testid="return-detail-error">{{ detailError }}</p>
      </template>
      <template #foot>
        <button class="btn btn-sec" type="button" data-testid="return-disable-user" :disabled="busy || !detail" @click="disableUser">关闭权限</button>
        <button class="btn btn-pri" type="button" data-testid="return-close" :disabled="busy || !detail || !canClose" :title="closeTitle" @click="closeOrder">全部闭环确认</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type Row = Record<string, unknown>
type UserOpt = { id: number; username?: string; nickname?: string }

const actor = useUserStore()
const canGenerate = ref(actor.profile?.username === 'admin')
const orders = ref<Row[]>([])
const users = ref<UserOpt[]>([])
const userKeyword = ref('')
const listError = ref('')
const returnNo = ref('')
const status = ref('')
const filterUserId = ref('')
const timeFrom = ref('')
const timeTo = ref('')
const rangeError = ref('')
const generateOpen = ref(false)
const generateUserId = ref('')
const generateDate = ref('')
const generateError = ref('')
const detailOpen = ref(false)
const detail = ref<Row | null>(null)
const itemTab = ref('ALL')
const transferUser = reactive<Record<string, string>>({})
const disputeRemark = reactive<Record<string, string>>({})
const detailError = ref('')
const busy = ref(false)

const items = computed(() => ((detail.value?.items as Row[]) || []))
const visibleItems = computed(() => {
  if (itemTab.value === 'ALL') return items.value
  return items.value.filter((item) => item.itemType === itemTab.value)
})
const canClose = computed(() => items.value.every((item) => ['RETURNED', 'TRANSFERRED'].includes(String(item.itemStatus || ''))))
const closeTitle = computed(() => {
  const disputed = items.value.filter((item) => item.itemStatus === 'DISPUTED').length
  return disputed ? `${disputed} 项争议待裁决` : ''
})
const returnFiltered = computed(
  () => !!(returnNo.value.trim() || status.value || filterUserId.value || timeFrom.value || timeTo.value),
)
const returnEmptyTitle = computed(() => (returnFiltered.value ? '没有符合筛选的离职归还单' : '暂无离职归还单'))
const returnEmptyHint = computed(() =>
  returnFiltered.value
    ? '换一个单号或状态，或换离职人、生效日，或清空筛选。'
    : '离职归还单由钉钉离职事件自动生成，异常缺单时使用手动补建。',
)

function statusText(value: string) {
  const labels: Record<string, string> = {
    IN_PROGRESS: '进行中',
    EXCEPTION_SUSPENDED: '异常挂起',
    CLOSED: '已闭环',
  }
  return labels[value] || value || '—'
}

function statusStyle(value: string) {
  if (value === 'IN_PROGRESS') return 'background:rgba(0,113,227,.12);color:#0071e3'
  if (value === 'CLOSED') return 'background:rgba(52,199,89,.12);color:#1e8e3e'
  if (value === 'EXCEPTION_SUSPENDED') return 'background:rgba(255,59,48,.12);color:#c62828'
  return 'background:rgba(142,142,147,.16);color:#6d6d72'
}

function itemStyle(value: string) {
  if (value === 'RETURNED') return 'background:rgba(52,199,89,.12);color:#1e8e3e'
  if (value === 'DISPUTED') return 'background:rgba(255,59,48,.12);color:#c62828'
  if (value === 'TRANSFERRED') return 'background:rgba(0,113,227,.12);color:#0071e3'
  return 'background:rgba(255,149,0,.16);color:#c46a00'
}

function itemText(value: string) {
  const labels: Record<string, string> = {
    PENDING: '待归还',
    RETURNED: '已归还',
    TRANSFERRED: '转交',
    DISPUTED: '争议',
  }
  return labels[value] || value || '—'
}

function typeText(value: string) {
  const labels: Record<string, string> = { ACCOUNT: '账号', ASSET: '资产', CERT: '证件' }
  return labels[value] || value
}

function overdueText(row: Row) {
  if (!row.overdue) return '—'
  const days = Number(row.overdueDays || 0)
  return days > 0 ? `逾期 ${days} 天` : '逾期'
}

function closedText(value: unknown) {
  const text = String(value || '')
  if (!text) return '—'
  return text.replace('T', ' ').slice(0, 16)
}

function progressText(row: Row) {
  const progress = (row.progress || {}) as { done?: number; total?: number; disputed?: number }
  const done = progress.done || 0
  const total = progress.total || row.itemCount || 0
  const disputed = progress.disputed || 0
  return disputed ? `${done}/${total} 已处理 · ${disputed} 争议` : `${done}/${total} 已处理`
}

function rejectText(error: unknown): string {
  if (error && typeof error === 'object' && 'code' in error) {
    const body = error as { code?: number; msg?: string }
    const code = Number(body.code ?? 0)
    if (code !== 0) return `${code} ${body.msg || '操作失败'}`
  }
  return errorMessage(error)
}

function userLabel(user: UserOpt) {
  return String(user.nickname || user.username || user.id || '').trim()
}

const filteredUsers = computed(() => {
  const keyword = userKeyword.value.trim().toLowerCase()
  if (!keyword) return users.value
  return users.value.filter((user) => {
    const name = userLabel(user).toLowerCase()
    const login = String(user.username || '').toLowerCase()
    return name.includes(keyword) || login.includes(keyword)
  })
})

async function loadUsers() {
  const collected: UserOpt[] = []
  let page = 1
  let total = 0
  try {
    do {
      const res = await http.get('/system/user/page', { params: { pageNo: page, pageSize: 100 } })
      const payload = (res.data?.data || {}) as { list?: UserOpt[]; total?: number }
      const batch = payload.list || []
      total = typeof payload.total === 'number' ? payload.total : batch.length
      collected.push(...batch)
      if (!batch.length) break
      page += 1
    } while (collected.length < total && page <= 20)
    users.value = collected
  } catch {
    users.value = collected
  }
}

function rangeProblem() {
  const from = timeFrom.value
  const to = timeTo.value
  if (!from && !to) return ''
  if (!from || !to) return '请同时填写生效日起止'
  if (to < from) return '生效日结束早于开始'
  return ''
}

async function loadList() {
  listError.value = ''
  rangeError.value = rangeProblem()
  if (rangeError.value) return
  const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
  if (returnNo.value.trim()) params.returnNo = returnNo.value.trim()
  if (status.value) params.status = status.value
  if (filterUserId.value) params.userId = Number(filterUserId.value)
  if (timeFrom.value && timeTo.value) {
    params.timeFrom = timeFrom.value
    params.timeTo = timeTo.value
  }
  try {
    const res = await http.get('/account/return/list', { params })
    orders.value = (res.data?.data?.list || []) as Row[]
  } catch (error) {
    listError.value = rejectText(error)
    orders.value = []
  }
}

function resetFilters() {
  returnNo.value = ''
  status.value = ''
  filterUserId.value = ''
  timeFrom.value = ''
  timeTo.value = ''
  rangeError.value = ''
  return loadList()
}

function today() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

function openGenerate() {
  generateOpen.value = true
  generateError.value = ''
  generateDate.value = today()
  generateUserId.value = ''
}

async function generate() {
  generateError.value = ''
  if (!generateUserId.value || !generateDate.value) {
    generateError.value = '必填项，请填写'
    return
  }
  busy.value = true
  try {
    const res = await http.post('/account/return/generate', {
      userId: Number(generateUserId.value),
      dingtalkResignDate: generateDate.value,
      manual: true,
    })
    generateOpen.value = false
    await loadList()
    const created = res.data?.data as Row
    if (created?.id) await openOrder(created)
  } catch (error) {
    generateError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function openOrder(row: Row) {
  detailError.value = ''
  itemTab.value = 'ALL'
  detailOpen.value = true
  try {
    const res = await http.get(`/account/return/${row.id}`)
    detail.value = (res.data?.data || null) as Row | null
  } catch (error) {
    detailError.value = rejectText(error)
    detail.value = row
  }
}

async function markReturned(item: Row) {
  if (!detail.value) return
  detailError.value = ''
  busy.value = true
  try {
    await http.put(`/account/return/item/${item.id}`, { itemStatus: 'RETURNED' })
    await openOrder(detail.value)
    await loadList()
  } catch (error) {
    detailError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function markTransferred(item: Row) {
  if (!detail.value) return
  const target = transferUser[String(item.id)]
  detailError.value = ''
  if (!target) {
    detailError.value = '必填项，请填写'
    return
  }
  busy.value = true
  try {
    await http.put(`/account/return/item/${item.id}`, { itemStatus: 'TRANSFERRED', transferToUserId: Number(target) })
    await openOrder(detail.value)
    await loadList()
  } catch (error) {
    detailError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function markDisputed(item: Row) {
  if (!detail.value) return
  const remark = (disputeRemark[String(item.id)] || '').trim()
  detailError.value = ''
  if (!remark) {
    detailError.value = '必填项，请填写'
    return
  }
  busy.value = true
  try {
    await http.put(`/account/return/item/${item.id}`, { itemStatus: 'DISPUTED', remark })
    await openOrder(detail.value)
    await loadList()
  } catch (error) {
    detailError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function closeOrder() {
  if (!detail.value) return
  detailError.value = ''
  busy.value = true
  try {
    await http.put(`/account/return/${detail.value.id}/close`, {})
    await openOrder(detail.value)
    await loadList()
  } catch (error) {
    detailError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function disableUser() {
  if (!detail.value) return
  detailError.value = ''
  busy.value = true
  try {
    await http.put(`/system/user/${detail.value.userId}`, { status: 'DISABLED' })
    detailError.value = '权限已关闭'
  } catch (error) {
    detailError.value = rejectText(error)
  } finally {
    busy.value = false
  }
}

async function loadActor() {
  const id = actor.profile?.userId
  if (!id || actor.profile?.username === 'admin') {
    canGenerate.value = true
    return
  }
  try {
    const res = await http.get(`/system/user/${id}`)
    const names = ((res.data?.data?.roleNames as string[]) || []).join(' ')
    canGenerate.value = /管理员|行政/.test(names)
  } catch {
    canGenerate.value = false
  }
}

onMounted(async () => {
  await loadActor()
  await loadUsers()
  await loadList()
})
</script>
