<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>离职归还</h1>
        <div class="sub">ACCT-003 · 归还单未闭环时关闭权限返回 1024</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" data-testid="return-generate-open" @click="openGenerate">手动补建</button>
      </div>
    </div>
    <p class="hint">离职归还单由钉钉离职事件自动生成。名下账号、资产、证件未全部归还或转交时，不能关闭权限。</p>
    <form class="qbar" data-testid="return-filters" @submit.prevent="loadList">
      <input v-model="returnNo" data-testid="return-filter-no" placeholder="归还单号" style="width: 160px" />
      <label>
        离职人
        <select v-model="filterUserId" data-testid="return-filter-user" style="width: 140px">
          <option value="">全部</option>
          <option v-for="user in users" :key="String(user.id)" :value="String(user.id)">{{ user.nickname || user.username }}</option>
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
              <th>离职生效日</th>
              <th>进度</th>
              <th>状态</th>
              <th>逾期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!orders.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty" data-testid="return-list-empty">
                  <div class="et">{{ returnEmptyTitle }}</div>
                  <div class="es">{{ returnEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in orders" :key="String(row.id)" data-testid="return-order-row">
              <td class="mono" data-testid="return-order-no">{{ row.returnNo }}</td>
              <td>{{ row.userName || row.userNickname }}</td>
              <td>{{ row.resignDate }}</td>
              <td data-testid="return-order-progress">{{ progressText(row) }}</td>
              <td data-testid="return-order-status">{{ statusText(String(row.status || '')) }}</td>
              <td data-testid="return-order-overdue">{{ row.overdue ? '逾期' : '—' }}</td>
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
        <p v-if="detail.status !== 'CLOSED'" class="hint bad">未闭环期间不能关闭该离职人的权限。名下账号保持冻结。</p>
        <table data-testid="return-item-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>名称</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!items.length">
              <td colspan="4">没有待归还的账号、资产或证件</td>
            </tr>
            <tr v-for="item in items" :key="String(item.id)" data-testid="return-item-row">
              <td>{{ typeText(String(item.itemType || '')) }}</td>
              <td data-testid="return-item-label">{{ item.itemLabel || item.itemSnapshot }}</td>
              <td data-testid="return-item-status">{{ itemText(String(item.itemStatus || '')) }}</td>
              <td>
                <button class="btn btn-txt" type="button" data-testid="return-item-returned" :disabled="detail.status === 'CLOSED' || item.itemStatus === 'RETURNED'" @click="markReturned(item)">确认归还</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="detailError" class="hint bad" data-testid="return-detail-error">{{ detailError }}</p>
      </template>
      <template #foot>
        <button class="btn btn-sec" type="button" data-testid="return-disable-user" :disabled="busy || !detail" @click="disableUser">关闭权限</button>
        <button class="btn btn-pri" type="button" data-testid="return-close" :disabled="busy || !detail" @click="closeOrder">全部闭环确认</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

type Row = Record<string, unknown>
type UserOpt = { id: number; username?: string; nickname?: string }

const orders = ref<Row[]>([])
const users = ref<UserOpt[]>([])
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
const detailError = ref('')
const busy = ref(false)

const items = computed(() => ((detail.value?.items as Row[]) || []))
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

async function loadUsers() {
  const firstRes = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100 } })
  const payload = (firstRes.data?.data || {}) as { list?: UserOpt[]; total?: number }
  const first = payload.list || []
  const total = payload.total || first.length
  if (total <= first.length) {
    users.value = first
    return
  }
  const lastPage = Math.ceil(total / 100)
  const lastRes = await http.get('/system/user/page', { params: { pageNo: lastPage, pageSize: 100 } })
  const last = ((lastRes.data?.data || {}) as { list?: UserOpt[] }).list || []
  const seen = new Set(first.map((user) => String(user.id)))
  users.value = first.concat(last.filter((user) => !seen.has(String(user.id))))
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
    generateError.value = '离职人和离职日期必填'
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

onMounted(async () => {
  await loadUsers()
  await loadList()
})
</script>
