<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>岗位-角色供给规则</h1>
        <div class="sub">AUTH-003 · 只挂角色，权限明细在角色页</div>
      </div>
    </div>
    <form class="qbar" @submit.prevent="create">
      <input v-model="name" placeholder="规则名" style="width: 160px" />
      <input v-model="position" placeholder="钉钉岗位" style="width: 160px" />
      <select v-model="roleId" style="width: 180px">
        <option value="">授予角色</option>
        <option v-for="role in roles" :key="String(role.id)" :value="String(role.id)">
          {{ role.roleName }}{{ role.status === 'PENDING_CONFIG' ? '（待配置）' : '' }}
        </option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">新建</button>
    </form>
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
                <div class="empty"><div class="et">{{ error || '没有供给规则' }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
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
import { onMounted, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal, cell, readData } from '../../api/read'

const rows = ref<Record<string, unknown>[]>([])
const roles = ref<Record<string, unknown>[]>([])
const ready = ref(false)
const error = ref('')
const name = ref('')
const position = ref('')
const roleId = ref('')
const msg = ref('')
const total = ref(0)
const confirmId = ref(0)

function roleNames(row: Record<string, unknown>) {
  const grants = row.grantRoles
  if (!Array.isArray(grants) || !grants.length) return '—'
  return grants.map((item) => String((item as { roleName?: string }).roleName || '')).filter(Boolean).join('、') || '—'
}

async function load() {
  const roleRes = await readData('/system/role/list')
  roles.value = asList(roleRes.data).filter((role) => role.status === 'ENABLED')
  if (!roleId.value && roles.value.length) roleId.value = String(roles.value[0].id)

  const res = await readData('/auth/position/rules', { pageNo: 1, pageSize: 10 })
  ready.value = true
  error.value = res.error
  rows.value = asList(res.data)
  total.value = asTotal(res.data, rows.value.length)
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
