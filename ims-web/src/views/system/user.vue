<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>用户管理</h1>
        <div class="sub">SYS-001 · 手机号由接口脱敏 · GET /system/user/page</div>
      </div>
      <div class="acts">
        <button v-if="canAddUser" class="btn btn-pri" type="button" data-testid="sys-user-create-open" @click="openCreate">新建用户</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" placeholder="用户名 / 手机" style="width: 160px" />
      <select v-model="status" style="width: 108px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>用户 ID</th>
              <th>用户名</th>
              <th>姓名</th>
              <th>部门</th>
              <th>IMS 角色</th>
              <th>手机</th>
              <th>钉钉</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '没有用户' }}</div>
                  <div class="es">列表只展示接口返回的字段</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" data-testid="sys-user-row">
              <td class="mono num">{{ row.id }}</td>
              <td>{{ row.username || '—' }}</td>
              <td style="font-weight: 500">{{ row.nickname || '—' }}</td>
              <td>{{ deptLabel(row) }}</td>
              <td>{{ roleLabel(row) }}</td>
              <td class="masked">{{ row.mobile || '—' }}</td>
              <td>
                <span class="tag" :style="row.dingtalkUserId ? okStyle : offStyle">
                  <span class="dot"></span>{{ row.dingtalkUserId ? row.dingtalkUserId : '未绑定' }}
                </span>
              </td>
              <td>
                <span class="tag" :style="row.status === 'ENABLED' ? okStyle : offStyle">
                  <span class="dot"></span>{{ statusText(row.status) }}
                </span>
              </td>
              <td>
                <button v-if="canEditUser" class="btn btn-txt" type="button" data-testid="sys-user-edit" @click="openEdit(row)">编辑</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <select class="pg-size" :value="pageSize" @change="changeSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
        <span>条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="goto(pageNo - 1)">‹</span>
        <span v-for="n in pageList" :key="n" class="pg-n" :class="{ on: n === pageNo }" @click="goto(n)">{{ n }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="goto(pageNo + 1)">›</span>
      </div>
    </div>
    <ProtoDrawer :open="drawerOpen" :title="drawerTitle" width="520px" @close="closeDrawer">
      <div v-if="editId" class="formrow one">
        <div class="fld"><label>用户名</label><input :value="form.username" disabled /></div>
      </div>
      <div v-else class="formrow one">
        <div class="fld"><label>用户名<i class="req">*</i></label><input v-model="form.username" data-testid="sys-user-form-username" /></div>
      </div>
      <div class="formrow one"><div class="fld"><label>昵称</label><input v-model="form.nickname" data-testid="sys-user-form-nickname" /></div></div>
      <div class="formrow one"><div class="fld"><label>手机</label><input v-model="form.mobile" data-testid="sys-user-form-mobile" /></div></div>
      <div class="formrow one">
        <div class="fld">
          <label>状态</label>
          <select v-model="form.status" data-testid="sys-user-form-status">
            <option value="ENABLED">启用</option>
            <option value="DISABLED">停用</option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>部门</label>
          <select v-model="form.deptId" data-testid="sys-user-form-dept">
            <option value="">未分配</option>
            <option v-for="dept in deptOptions" :key="String(dept.id)" :value="String(dept.id)">{{ dept.name }}</option>
          </select>
          <div v-if="!deptOptions.length" class="sub">部门选项来自已同步组织人员；也可先不选。</div>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>IMS 角色</label>
          <select v-model="form.roleIds" multiple size="5" data-testid="sys-user-form-roles" style="min-height: 120px">
            <option v-for="role in roleOptions" :key="String(role.id)" :value="String(role.id)">
              {{ roleChoiceLabel(role) }}
            </option>
          </select>
        </div>
      </div>
      <div class="formrow one">
        <div class="fld">
          <label>{{ editId ? '重置密码（选填）' : '初始密码' }}<i v-if="!editId" class="req">*</i></label>
          <input v-model="form.password" type="password" data-testid="sys-user-form-password" autocomplete="new-password" />
        </div>
      </div>
      <div v-if="formError" class="hint bad" data-testid="sys-user-form-error">{{ formError }}</div>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="closeDrawer">取消</button>
        <button class="btn btn-pri" type="button" data-testid="sys-user-form-save" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal, readData } from '../../api/read'
import { roleChoiceLabel } from '../../roleSource'
import { useUserStore } from '../../stores/user'

type UserRow = {
  id: string
  username: string
  nickname: string
  mobile: string
  status: string
  dingtalkUserId?: string
  roleIds?: number[]
  roleNames?: string[]
  deptIds?: number[]
  deptNames?: string[]
}

type RoleOption = { id: number | string; roleName: string; source?: string; status?: string }
type DeptOption = { id: number; name: string }

const okStyle = 'background:rgba(52,199,89,.12);color:#1e8e3e'
const offStyle = 'background:rgba(142,142,147,.12);color:#6d6d72'
const rows = ref<UserRow[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const status = ref('')
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editId = ref('')
const saving = ref(false)
const formError = ref('')
const roleOptions = ref<RoleOption[]>([])
const deptOptions = ref<DeptOption[]>([])
const user = useUserStore()
const canAddUser = computed(() => user.hasPerm('system:user:add') || user.canWrite('system:user:query'))
const canEditUser = computed(() => user.hasPerm('system:user:edit') || user.canWrite('system:user:query'))
const form = reactive({
  username: '',
  nickname: '',
  mobile: '',
  password: '',
  status: 'ENABLED',
  deptId: '',
  roleIds: [] as string[],
})

const drawerTitle = computed(() => (editId.value ? '编辑用户' : '新建用户'))
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})

function statusText(value: string) {
  if (value === 'ENABLED') return '启用'
  if (value === 'DISABLED') return '停用'
  return value || '—'
}

function deptLabel(row: UserRow) {
  const names = row.deptNames?.filter(Boolean)
  if (names?.length) return names.join('、')
  const ids = row.deptIds?.filter((id) => id > 0)
  if (ids?.length) return ids.map((id) => `部门 ${id}`).join('、')
  return '—'
}

function roleLabel(row: UserRow) {
  const names = row.roleNames?.filter(Boolean)
  if (names?.length) return names.join('、')
  return '—'
}

function queryParams() {
  const params: Record<string, string | number> = { pageNo: pageNo.value, pageSize: pageSize.value }
  const text = keyword.value.trim()
  if (text) {
    if (/^\d+$/.test(text)) params.mobile = text
    else params.username = text
  }
  if (status.value) params.status = status.value
  return params
}

function resetForm() {
  form.username = ''
  form.nickname = ''
  form.mobile = ''
  form.password = ''
  form.status = 'ENABLED'
  form.deptId = ''
  form.roleIds = []
  formError.value = ''
}

async function loadMeta() {
  const roleRes = await readData('/system/role/list')
  roleOptions.value = asList(roleRes.data) as RoleOption[]
  const orgRes = await readData('/auth/org/users', { pageNo: 1, pageSize: 100 })
  const catalog = asList(orgRes.data) as UserRow[]
  const map = new Map<number, DeptOption>()
  for (const row of catalog) {
    const ids = Array.isArray(row.deptIds) ? row.deptIds.map((item) => Number(item)).filter((id) => id > 0) : []
    const names = Array.isArray(row.deptNames) ? row.deptNames.map((item) => String(item || '')) : []
    ids.forEach((id, index) => {
      const name = names[index] || names.find((item) => item) || `部门 ${id}`
      if (!map.has(id)) map.set(id, { id, name })
    })
  }
  deptOptions.value = [...map.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh'))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/system/user/page', { params: queryParams() })
    const data = res.data?.data
    rows.value = asList(data) as unknown as UserRow[]
    total.value = asTotal(data, rows.value.length)
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  load()
}

function reset() {
  keyword.value = ''
  status.value = ''
  search()
}

function goto(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  load()
}

function changeSize(event: Event) {
  pageSize.value = Number((event.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

function openCreate() {
  editId.value = ''
  resetForm()
  drawerOpen.value = true
}

async function openEdit(row: UserRow) {
  editId.value = row.id
  resetForm()
  drawerOpen.value = true
  formError.value = ''
  try {
    const res = await http.get(`/system/user/${row.id}`)
    const data = res.data?.data as UserRow
    form.username = data.username || row.username
    form.nickname = data.nickname || ''
    form.mobile = data.mobile || ''
    form.status = data.status || 'ENABLED'
    form.deptId = data.deptIds?.length ? String(data.deptIds[0]) : ''
    form.roleIds = (data.roleIds || []).map((id) => String(id))
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  }
}

function closeDrawer() {
  drawerOpen.value = false
  editId.value = ''
  formError.value = ''
}

function buildPayload() {
  const payload: Record<string, unknown> = {
    nickname: form.nickname.trim() || undefined,
    mobile: form.mobile.trim() || undefined,
    status: form.status,
    roleIds: form.roleIds.map((id) => Number(id)).filter((id) => id > 0),
    deptIds: form.deptId ? [Number(form.deptId)] : [],
  }
  const password = form.password.trim()
  if (password) payload.password = password
  if (!editId.value) {
    payload.username = form.username.trim()
    if (!password) payload.password = undefined
  }
  return payload
}

async function save() {
  formError.value = ''
  if (!editId.value) {
    if (!form.username.trim()) {
      formError.value = '用户名必填'
      return
    }
    if (!form.password.trim()) {
      formError.value = '初始密码必填'
      return
    }
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (editId.value) {
      await http.put(`/system/user/${editId.value}`, payload)
    } else {
      await http.post('/system/user', payload)
    }
    closeDrawer()
    await load()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
</script>
