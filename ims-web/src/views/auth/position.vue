<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>岗位-角色供给规则</h1>
        <div class="sub">AUTH-003 · 只挂角色，权限明细在角色页</div>
      </div>
    </div>
    <form class="qbar" data-testid="pos-create" @submit.prevent="create">
      <input v-model="name" data-testid="pos-create-name" placeholder="规则名" style="width: 160px" />
      <input v-model="position" data-testid="pos-create-position" placeholder="钉钉岗位" style="width: 160px" />
      <select v-model="roleId" data-testid="pos-create-role" style="width: 180px">
        <option value="">授予角色</option>
        <option v-for="role in roles" :key="String(role.id)" :value="String(role.id)">
          {{ role.roleName }}{{ role.status === 'PENDING_CONFIG' ? '（待配置）' : '' }}
        </option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="pos-create-submit">新建</button>
    </form>
    <form class="qbar" data-testid="pos-filters" @submit.prevent="search">
      <input v-model="filterKeyword" data-testid="pos-filter-keyword" placeholder="规则名 / 岗位" style="width: 160px" />
      <input v-model="filterPosition" data-testid="pos-filter-position" placeholder="钉钉岗位（精确）" style="width: 160px" />
      <select v-model="filterRoleId" data-testid="pos-filter-role" style="width: 180px">
        <option value="">全部角色</option>
        <option v-for="role in filterRoles" :key="String(role.id)" :value="String(role.id)">
          {{ role.roleName }}{{ role.status === 'PENDING_CONFIG' ? '（待配置）' : '' }}
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
    <p v-if="msg" class="hint" style="margin-bottom: 10px">{{ msg }}</p>
    <div v-if="confirmId" class="card" style="margin-bottom: 12px">
      <div style="font-weight: 600; margin-bottom: 6px">确认删除</div>
      <div class="sub">在用用户不为 0 时会拒绝。删除后列表不再显示该版本。</div>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-pri btn-sm" type="button" @click="remove">确认删除</button>
        <button class="btn btn-sec btn-sm" type="button" @click="confirmId = 0">取消</button>
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
                <button class="btn btn-txt" type="button" @click="edit(row)">新版本</button>
                <button class="btn btn-txt" type="button" @click="confirmId = Number(row.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal, cell, readData } from '../../api/read'

const rows = ref<Record<string, unknown>[]>([])
const roles = ref<Record<string, unknown>[]>([])
const filterRoles = ref<Record<string, unknown>[]>([])
const ready = ref(false)
const error = ref('')
const name = ref('')
const position = ref('')
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

const hasFilters = computed(() => Boolean(appliedKeyword.value || appliedPosition.value || appliedRoleId.value || appliedStatus.value))

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
  return grants.map((item) => String((item as { roleName?: string }).roleName || '')).filter(Boolean).join('、') || '—'
}

function captureFilters() {
  appliedKeyword.value = filterKeyword.value.trim()
  appliedPosition.value = filterPosition.value.trim()
  appliedRoleId.value = filterRoleId.value
  appliedStatus.value = filterStatus.value
}

async function load() {
  captureFilters()
  const roleRes = await readData('/system/role/list')
  filterRoles.value = asList(roleRes.data)
  roles.value = filterRoles.value.filter((role) => role.status === 'ENABLED')
  if (!roleId.value && roles.value.length) roleId.value = String(roles.value[0].id)

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

async function create() {
  msg.value = ''
  if (!name.value || !position.value || !roleId.value) {
    msg.value = '请填写规则名、岗位和角色'
    return
  }
  try {
    await http.post('/auth/position/rule', {
      ruleName: name.value,
      dingtalkPosition: position.value,
      grantRoleIds: [Number(roleId.value)],
    })
    name.value = ''
    position.value = ''
    msg.value = '已新建，版本 1'
    await load()
  } catch (e: unknown) {
    msg.value = errorMessage(e)
  }
}

async function edit(row: Record<string, unknown>) {
  msg.value = ''
  const grants = Array.isArray(row.grantRoles) ? row.grantRoles : []
  const ids = grants.map((item) => Number((item as { roleId?: number }).roleId)).filter((id) => id)
  try {
    await http.put(`/auth/position/rule/${row.id}`, {
      ruleName: row.ruleName,
      dingtalkPosition: row.dingtalkPosition,
      grantRoleIds: ids,
    })
    msg.value = '已生成新版本，已套用用户未改'
    await load()
  } catch (e: unknown) {
    msg.value = errorMessage(e)
  }
}

async function remove() {
  msg.value = ''
  try {
    await http.delete(`/auth/position/rule/${confirmId.value}`, { params: { confirmText: 'DELETE' } })
    msg.value = '已删除'
    confirmId.value = 0
    await load()
  } catch (e: unknown) {
    msg.value = errorMessage(e)
  }
}

onMounted(load)
</script>
