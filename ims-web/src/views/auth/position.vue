<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>岗位-角色供给规则</h1>
        <div class="sub">AUTH-003 · 只挂角色，权限明细在角色页</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="pos-create-open" @click="openCreate">新建规则</button>
      </div>
    </div>
    <form class="qbar" data-testid="pos-filters" @submit.prevent="search">
      <input v-model="filterKeyword" data-testid="pos-filter-keyword" placeholder="规则名 / 岗位" style="width: 160px" />
      <input
        v-model="filterPosition"
        data-testid="pos-filter-position"
        list="pos-filter-position-list"
        placeholder="钉钉岗位（精确）"
        style="width: 160px"
      />
      <datalist id="pos-filter-position-list">
        <option v-for="pos in positionOptions" :key="'f-' + pos" :value="pos" />
      </datalist>
      <select v-model="filterRoleId" data-testid="pos-filter-role" style="width: 180px">
        <option value="">全部角色</option>
        <option v-for="role in filterRoles" :key="String(role.id)" :value="String(role.id)">
          {{ roleChoiceLabel(role) }}
        </option>
      </select>
      <select v-model="filterStatus" data-testid="pos-filter-status" style="width: 120px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="pos-filter-search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="pos-filter-reset" @click="resetFilters">重置</button>
    </form>
    <p v-if="filterNote" class="hint" data-testid="pos-filter-summary">{{ filterNote }}</p>
    <p v-if="msg && !drawerOpen" class="hint" data-testid="pos-form-error" style="margin-bottom: 10px">{{ msg }}</p>
    <div v-if="confirmId" class="card" data-testid="pos-delete-card" style="margin-bottom: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">确认删除</div>
      <div class="sub">请输入规则名「{{ confirmRuleName }}」后删除。在用人数不为 0 时直接拒绝，不打开本确认。</div>
      <input v-model="confirmName" data-testid="pos-delete-name" placeholder="输入规则名" style="width: 220px; margin-top: 8px" />
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="pos-delete-confirm" @click="remove">确认删除</button>
        <button class="btn btn-sec btn-sm" type="button" @click="closeDelete">取消</button>
      </div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>岗位</th>
              <th>版本</th>
              <th>授予角色</th>
              <th>在用</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!ready">
              <td colspan="7" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7" style="white-space: normal">
                <div class="empty" data-testid="pos-list-empty">
                  <div class="et">{{ error || (hasFilters ? '没有符合条件的供给规则' : '没有供给规则') }}</div>
                  <div v-if="hasFilters" class="es">换规则名、岗位、角色或状态后再查。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)" data-testid="pos-rule-row">
              <td style="font-weight: 500">{{ cell(row, ['ruleName']) }}</td>
              <td>{{ cell(row, ['dingtalkPosition']) }}</td>
              <td class="mono">{{ cell(row, ['version']) }}</td>
              <td>{{ roleNames(row) }}</td>
              <td class="num">{{ cell(row, ['appliedUserCount']) }}</td>
              <td>{{ row.status === 'ENABLED' ? '启用' : '停用' }}</td>
              <td>
                <button class="btn btn-txt" type="button" data-testid="pos-edit" @click="openEdit(row)">编辑</button>
                <button class="btn btn-txt" type="button" data-testid="pos-delete" @click="askRemove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer
      :open="drawerOpen"
      :title="editingId ? `编辑供给规则 · v${editingVersion}` : '新建供给规则'"
      width="560px"
      @close="closeDrawer"
    >
      <p v-if="editingId" class="hint">保存后将生成 v{{ editingVersion + 1 }}；已套用用户权限不变。</p>
      <div class="fld">
        <label>规则名称 <span class="req">*</span></label>
        <input v-model="name" data-testid="pos-create-name" maxlength="64" placeholder="≤64 字" />
      </div>
      <div class="fld">
        <label>钉钉岗位 <span class="req">*</span></label>
        <input
          v-model="position"
          data-testid="pos-create-position"
          list="pos-create-position-list"
          placeholder="组织同步后可下拉选择"
          :readonly="Boolean(editingId)"
        />
        <datalist id="pos-create-position-list">
          <option v-for="pos in drawerPositionOptions" :key="pos" :value="pos" />
        </datalist>
        <p v-if="!positionOptions.length" class="hint">暂无岗位字典，请先在「组织架构同步」完成钉钉同步或手输岗位名。</p>
      </div>
      <div class="fld">
        <label>说明</label>
        <textarea v-model="description" data-testid="pos-create-desc" rows="3" placeholder="选填，≤200 字" />
      </div>
      <div class="fld">
        <label>授予角色 <span class="req">*</span></label>
        <p class="hint">权限由角色决定；本规则不配置权限明细。</p>
        <select v-model="roleId" data-testid="pos-create-role">
          <option value="">请选择角色</option>
          <option v-for="role in roles" :key="String(role.id)" :value="String(role.id)">
            {{ roleChoiceLabel(role) }}
          </option>
        </select>
      </div>
      <p v-if="msg && drawerOpen" class="hint" data-testid="pos-form-error">{{ msg }}</p>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="closeDrawer">取消</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="pos-create-submit" @click="saveDrawer">
          {{ editingId ? '保存为新版本' : '保存' }}
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal, cell, readData } from '../../api/read'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { roleChoiceLabel } from '../../roleSource'

const rows = ref<Record<string, unknown>[]>([])
const roles = ref<Record<string, unknown>[]>([])
const filterRoles = ref<Record<string, unknown>[]>([])
const positionOptions = ref<string[]>([])
const ready = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editingId = ref(0)
const editingVersion = ref(1)
const name = ref('')
const position = ref('')
const description = ref('')
const roleId = ref('')
const filterKeyword = ref('')
const filterPosition = ref('')
const filterRoleId = ref('')
const filterStatus = ref('')
const appliedKeyword = ref('')
const appliedPosition = ref('')
const appliedRoleId = ref('')
const appliedStatus = ref('')
const msg = ref('')
const total = ref(0)
const confirmId = ref(0)
const confirmName = ref('')
const confirmRuleName = ref('')

const hasFilters = computed(() => Boolean(appliedKeyword.value || appliedPosition.value || appliedRoleId.value || appliedStatus.value))

const drawerPositionOptions = computed(() => {
  const set = new Set(positionOptions.value)
  const cur = position.value.trim()
  if (cur) set.add(cur)
  return [...set].sort()
})

const filterNote = computed(() => {
  const bits: string[] = []
  if (appliedKeyword.value) bits.push(`关键词「${appliedKeyword.value}」`)
  if (appliedPosition.value) bits.push(`岗位「${appliedPosition.value}」`)
  if (appliedRoleId.value) {
    const role = filterRoles.value.find((item) => String(item.id) === appliedRoleId.value)
    bits.push(`角色「${role?.roleName || appliedRoleId.value}」`)
  }
  if (appliedStatus.value) bits.push(appliedStatus.value === 'ENABLED' ? '启用' : '停用')
  if (!bits.length) return ''
  return `供给规则按${bits.join('、')}筛选。`
})

function roleNames(row: Record<string, unknown>) {
  const grants = row.grantRoles
  if (!Array.isArray(grants) || !grants.length) return '—'
  return grants.map((item) => roleChoiceLabel(item as { roleName?: string; source?: string; status?: string })).filter(Boolean).join('、') || '—'
}

function captureFilters() {
  appliedKeyword.value = filterKeyword.value.trim()
  appliedPosition.value = filterPosition.value.trim()
  appliedRoleId.value = filterRoleId.value
  appliedStatus.value = filterStatus.value
}

function resetDrawerForm() {
  name.value = ''
  position.value = ''
  description.value = ''
  roleId.value = ''
  editingId.value = 0
  editingVersion.value = 1
  msg.value = ''
}

async function openCreate() {
  resetDrawerForm()
  drawerOpen.value = true
  await loadPositions()
}

function openEdit(row: Record<string, unknown>) {
  resetDrawerForm()
  editingId.value = Number(row.id)
  editingVersion.value = Number(row.version || 1)
  name.value = String(row.ruleName || '')
  position.value = String(row.dingtalkPosition || '')
  description.value = String(row.description || '')
  const grants = Array.isArray(row.grantRoles) ? row.grantRoles : []
  const first = grants[0] as { roleId?: number } | undefined
  roleId.value = first?.roleId ? String(first.roleId) : ''
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  msg.value = ''
}

async function loadPositions() {
  const res = await readData('/auth/org/positions')
  const raw = asList(res.data)
  const fromStrings =
    raw.length && typeof raw[0] !== 'object'
      ? raw.map((item) => String(item))
      : ((res.data as { list?: unknown[] } | null)?.list || []).map((item) => String(item))
  positionOptions.value = fromStrings.filter(Boolean)
}

async function load() {
  captureFilters()
  await loadPositions()
  const roleRes = await readData('/system/role/list')
  filterRoles.value = asList(roleRes.data)
  roles.value = filterRoles.value

  const params: Record<string, unknown> = { pageNo: 1, pageSize: 20 }
  if (appliedKeyword.value) params.keyword = appliedKeyword.value
  if (appliedPosition.value) params.dingtalkPosition = appliedPosition.value
  if (appliedRoleId.value) params.grantRoleId = Number(appliedRoleId.value)
  if (appliedStatus.value) params.status = appliedStatus.value
  const res = await readData('/auth/position/rules', params)
  ready.value = true
  error.value = res.error
  rows.value = asList(res.data)
  total.value = asTotal(res.data, rows.value.length)
}

function search() {
  ready.value = false
  load()
}

function resetFilters() {
  filterKeyword.value = ''
  filterPosition.value = ''
  filterRoleId.value = ''
  filterStatus.value = ''
  search()
}

function formError() {
  const ruleName = name.value.trim()
  const pos = position.value.trim()
  const desc = description.value.trim()
  if (!ruleName || !pos || !roleId.value) return '请填写规则名、岗位和角色'
  if ([...ruleName].length > 64) return '规则名不能超过 64 字'
  if ([...pos].length > 64) return '钉钉岗位不能超过 64 字'
  if ([...desc].length > 200) return '说明不能超过 200 字'
  const role = roles.value.find((item) => String(item.id) === roleId.value)
  if (role?.status === 'PENDING_CONFIG') {
    return `角色「${role.roleName}」尚未配置权限，用户将无任何权限`
  }
  if (!editingId.value) {
    const clash = rows.value.some((row) => row.status === 'ENABLED' && String(row.dingtalkPosition || '') === pos)
    if (clash) return '该岗位已有启用版本'
  }
  return ''
}

async function saveDrawer() {
  msg.value = ''
  const invalid = formError()
  if (invalid) {
    msg.value = invalid
    return
  }
  const grantRoleIds = [Number(roleId.value)]
  const body = {
    ruleName: name.value.trim(),
    dingtalkPosition: position.value.trim(),
    description: description.value.trim(),
    grantRoleIds,
  }
  try {
    const wasEdit = editingId.value
    if (wasEdit) {
      await http.put(`/auth/position/rule/${wasEdit}`, body)
    } else {
      await http.post('/auth/position/rule', body)
    }
    closeDrawer()
    msg.value = wasEdit ? '已生成新版本，已套用用户未改' : '已新建，版本 1'
    await load()
  } catch (e: unknown) {
    msg.value = errorMessage(e)
  }
}

function closeDelete() {
  confirmId.value = 0
  confirmName.value = ''
  confirmRuleName.value = ''
}

function askRemove(row: Record<string, unknown>) {
  msg.value = ''
  if (Number(row.appliedUserCount || 0) > 0) {
    msg.value = '在用用户非零，不能删除'
    closeDelete()
    return
  }
  confirmId.value = Number(row.id)
  confirmRuleName.value = String(row.ruleName || '')
  confirmName.value = ''
}

async function remove() {
  msg.value = ''
  if (confirmName.value.trim() !== confirmRuleName.value) {
    msg.value = '请输入规则名以确认删除'
    return
  }
  try {
    await http.delete(`/auth/position/rule/${confirmId.value}`, { params: { confirmText: 'DELETE' } })
    msg.value = '已删除'
    closeDelete()
    await load()
  } catch (e: unknown) {
    msg.value = errorMessage(e)
  }
}

onMounted(load)
</script>
