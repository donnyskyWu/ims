<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>角色权限</h1>
        <div class="sub">SYS-002 · 角色=权限唯一载体 · 菜单 + 功能点 R/W/D + 数据范围 + 钉钉岗位</div>
      </div>
      <div class="acts">
        <input v-model="positionName" data-testid="role-position-input" placeholder="钉钉岗位" style="height: 34px; border: 1px solid var(--line2); border-radius: 8px; padding: 0 10px" />
        <button class="btn btn-pri" type="button" @click="fromPosition">从岗位生成角色</button>
      </div>
    </div>
    <div class="hint" style="margin-bottom: 10px">本部门不含下级。待配置角色不放行任何权限。权限预览走角色接口。</div>
    <form class="qbar" data-testid="role-filters" style="margin-bottom: 10px" @submit.prevent>
      <input v-model="keyword" data-testid="role-filter-keyword" placeholder="角色名 / 编码 / 岗位" style="width: 180px" />
      <select v-model="sourceFilter" data-testid="role-filter-source" style="width: 140px">
        <option value="">全部来源</option>
        <option value="MANUAL">自建</option>
        <option value="DINGTALK_AUTO">自动创建</option>
      </select>
      <button class="btn btn-sec btn-sm" type="button" data-testid="role-filter-reset" @click="resetFilters">重置</button>
    </form>
    <p v-if="filterNote" class="hint" data-testid="role-filter-summary">{{ filterNote }}</p>
    <p v-if="error" class="hint bad">{{ error }}</p>
    <div class="g4">
      <div class="card stat"><span class="l">角色总数</span><div class="n">{{ ready && !error ? rows.length : '—' }}</div><div class="d">{{ error || 'GET /system/role/list' }}</div></div>
      <div class="card stat"><span class="l">待配置</span><div class="n">{{ ready && !error ? pending : '—' }}</div><div class="d">PENDING_CONFIG</div></div>
      <div class="card stat"><span class="l">自动创建</span><div class="n">{{ ready && !error ? autoCount : '—' }}</div><div class="d">DINGTALK_AUTO</div></div>
      <div class="card stat"><span class="l">已启用</span><div class="n">{{ ready && !error ? enabled : '—' }}</div><div class="d">ENABLED</div></div>
    </div>
    <div class="cattabs" data-testid="role-status-tabs">
      <button class="cattab" :class="{ on: statusFilter === '' }" type="button" @click="statusFilter = ''">全部</button>
      <button class="cattab" :class="{ on: statusFilter === 'PENDING_CONFIG' }" type="button" data-testid="role-status-pending" @click="statusFilter = 'PENDING_CONFIG'">待配置</button>
      <button class="cattab" :class="{ on: statusFilter === 'ENABLED' }" type="button" @click="statusFilter = 'ENABLED'">启用</button>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>角色编码</th>
              <th>名称</th>
              <th>菜单数</th>
              <th>功能点 R/W/D</th>
              <th>数据范围</th>
              <th>钉钉岗位</th>
              <th>来源</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!ready">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!filtered.length">
              <td colspan="9">
                <div class="empty" data-testid="role-list-empty">
                  <div class="et">{{ error || roleEmpty }}</div>
                  <div v-if="statusFilter === 'PENDING_CONFIG' && !keyword.trim() && !sourceFilter" class="es">从钉钉岗位生成的角色会停在待配置，权限矩阵为空时不放行。</div>
                  <div v-else-if="keyword.trim() || sourceFilter || statusFilter" class="es">换角色名、来源或状态后再筛。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in filtered" v-else :key="String(row.id)" data-testid="role-row">
              <td class="mono">{{ cell(row, ['roleKey']) }}</td>
              <td>{{ cell(row, ['roleName']) }}</td>
              <td class="num">{{ menuCount(row) }}</td>
              <td class="num">{{ permCount(row) }}</td>
              <td><span class="tag">{{ scopeLabel(String(row.dataScope || '')) }}</span></td>
              <td>{{ cell(row, ['dingtalkPosition']) }}</td>
              <td><span class="tag">{{ sourceLabel(String(row.source || '')) }}</span></td>
              <td>
                <span class="tag" :style="row.status === 'PENDING_CONFIG' ? 'background:rgba(255,149,0,.12);color:#c46a00' : 'background:rgba(52,199,89,.12);color:#1e8e3e'">
                  {{ row.status === 'PENDING_CONFIG' ? '待配置' : '启用' }}
                </span>
              </td>
              <td>
                <button class="btn btn-txt" type="button" data-testid="role-edit" @click="openEdit(row)">编辑权限</button>
                <button class="btn btn-txt" type="button" @click="preview(row)">预览</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="diff || previewError" class="card" style="margin-top: 14px">
      <h3>权限差异</h3>
      <p v-if="previewError" class="hint bad">{{ previewError }}</p>
      <pre v-else class="mono" style="white-space: pre-wrap; margin: 8px 0 0">{{ diff }}</pre>
    </div>
    <ProtoDrawer :open="drawer" title="编辑角色权限" @close="drawer = false">
      <div v-if="!draft.menuIds.length && !permQuery.trim()" class="empty" data-testid="role-matrix-empty" style="margin-bottom: 12px">
        <div class="et">权限矩阵为空</div>
        <div class="es">待配置角色在勾选功能点并保存前不放行任何权限。</div>
      </div>
      <div class="fld" style="margin-bottom: 12px">
        <label>筛选权限</label>
        <input v-model="permQuery" data-testid="role-perm-filter" placeholder="权限名称或权限码" />
      </div>
      <div v-if="permQuery.trim() && !visibleMenus.length" class="empty" data-testid="role-perm-empty" style="margin-bottom: 12px">
        <div class="et">没有匹配的权限码</div>
        <div class="es">换一个名称或权限码再筛。已勾选的权限仍会保存。</div>
      </div>
      <div class="fld" style="margin-bottom: 12px">
        <label>数据范围（本部门不含下级）</label>
        <select v-model="draft.scope">
          <option value="ALL">全部</option>
          <option value="DEPT">本部门</option>
          <option value="IP_GROUP">IP 组</option>
          <option value="SELF">仅本人</option>
        </select>
      </div>
      <div class="fld" style="margin-bottom: 12px">
        <label>钉钉岗位</label>
        <input v-model="draft.position" />
      </div>
      <div v-for="menu in visibleMenus" :key="String(menu.id)" class="fld" style="margin-bottom: 8px" data-testid="role-perm-row">
        <label :style="{ paddingLeft: `${Number(menu.depth) * 12}px` }">
          <input v-model="draft.menuIds" type="checkbox" :value="menu.id" :disabled="!menu.permCode" />
          {{ menu.name }}
          <span v-if="menu.permCode" class="mono">{{ menu.permCode }}</span>
        </label>
        <select v-if="menu.permCode && draft.menuIds.includes(menu.id)" v-model="draft.levels[String(menu.permCode)]">
          <option value="R">R</option>
          <option value="W">W</option>
          <option value="D">D</option>
          <option value="RW">RW</option>
          <option value="RWD">RWD</option>
        </select>
      </div>
      <p v-if="saveError" class="hint bad">{{ saveError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="drawer = false">取消</button>
        <button class="btn btn-pri" type="button" @click="save">保存</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'
import { asList, cell, readData } from '../../api/read'
import { useUserStore } from '../../stores/user'

type MenuNode = { id: number; name: string; permCode?: string; children?: MenuNode[]; depth?: number }

const rows = ref<Record<string, unknown>[]>([])
const ready = ref(false)
const error = ref('')
const diff = ref('')
const previewError = ref('')
const positionName = ref('')
const statusFilter = ref('')
const keyword = ref('')
const sourceFilter = ref('')
const permQuery = ref('')
const drawer = ref(false)
const saveError = ref('')
const editingId = ref<number | string>('')
const flatMenus = ref<MenuNode[]>([])
const draft = reactive({ scope: 'SELF', position: '', menuIds: [] as number[], levels: {} as Record<string, string> })
const user = useUserStore()

const pending = computed(() => rows.value.filter((row) => row.status === 'PENDING_CONFIG').length)
const autoCount = computed(() => rows.value.filter((row) => row.source === 'DINGTALK_AUTO').length)
const enabled = computed(() => rows.value.filter((row) => row.status === 'ENABLED').length)
const filtered = computed(() => {
  const query = keyword.value.trim()
  return rows.value.filter((row) => {
    if (statusFilter.value && row.status !== statusFilter.value) return false
    if (sourceFilter.value && row.source !== sourceFilter.value) return false
    if (!query) return true
    const blob = [row.roleName, row.roleKey, row.dingtalkPosition].map((item) => String(item || '')).join(' ')
    return blob.includes(query)
  })
})

const filterNote = computed(() => {
  const bits: string[] = []
  if (keyword.value.trim()) bits.push(`关键词「${keyword.value.trim()}」`)
  if (sourceFilter.value) bits.push(sourceFilter.value === 'MANUAL' ? '自建' : '自动创建')
  if (statusFilter.value === 'PENDING_CONFIG') bits.push('待配置')
  if (statusFilter.value === 'ENABLED') bits.push('启用')
  if (!bits.length) return ''
  return `角色列表按${bits.join('、')}筛选。`
})

const roleEmpty = computed(() => {
  if (error.value) return error.value
  if (keyword.value.trim() || sourceFilter.value || statusFilter.value) return '没有符合条件的角色'
  return '没有角色'
})

const visibleMenus = computed(() => {
  const query = permQuery.value.trim().toLowerCase()
  if (!query) return flatMenus.value
  return flatMenus.value.filter((menu) => `${menu.name} ${menu.permCode || ''}`.toLowerCase().includes(query))
})

function resetFilters() {
  keyword.value = ''
  sourceFilter.value = ''
  statusFilter.value = ''
}

function menuCount(row: Record<string, unknown>) {
  return Array.isArray(row.menuIds) ? row.menuIds.length : 0
}
function permCount(row: Record<string, unknown>) {
  const detail = row.permDetail
  return detail && typeof detail === 'object' ? Object.keys(detail as object).length : 0
}
function scopeLabel(value: string) {
  return { ALL: '全部', DEPT: '本部门', IP_GROUP: 'IP组', SELF: '本人' }[value] || value || '—'
}
function sourceLabel(value: string) {
  return { MANUAL: '自建', DINGTALK_AUTO: '自动创建' }[value] || value || '—'
}

function flatten(nodes: MenuNode[], depth = 0): MenuNode[] {
  const out: MenuNode[] = []
  for (const node of nodes) {
    out.push({ ...node, depth })
    out.push(...flatten(node.children || [], depth + 1))
  }
  return out
}

async function load() {
  const res = await readData('/system/role/list')
  ready.value = true
  error.value = res.error
  rows.value = asList(res.data)
}

async function loadMenus() {
  const res = await readData('/system/menu/tree')
  flatMenus.value = flatten((res.data as MenuNode[]) || [])
}

async function fromPosition() {
  error.value = ''
  if (!positionName.value.trim()) {
    error.value = '请填写钉钉岗位'
    return
  }
  try {
    await http.post('/system/role/from-position', { dingtalkPosition: positionName.value.trim() })
    positionName.value = ''
    await load()
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
}

function openEdit(row: Record<string, unknown>) {
  editingId.value = row.id as number
  draft.scope = String(row.dataScope || 'SELF')
  draft.position = String(row.dingtalkPosition || '')
  draft.menuIds = Array.isArray(row.menuIds) ? (row.menuIds as number[]).map((id) => Number(id)) : []
  const detail = (row.permDetail || {}) as Record<string, string>
  draft.levels = { ...detail }
  saveError.value = ''
  permQuery.value = ''
  drawer.value = true
}

async function save() {
  saveError.value = ''
  const id = editingId.value
  const permDetail: Record<string, string> = {}
  for (const menu of flatMenus.value) {
    if (menu.permCode && draft.menuIds.includes(Number(menu.id))) {
      permDetail[String(menu.permCode)] = draft.levels[String(menu.permCode)] || 'R'
    }
  }
  try {
    const menuIds = draft.menuIds
      .map((menuId) => Number(menuId))
      .filter((menuId) => flatMenus.value.some((menu) => Number(menu.id) === menuId && menu.permCode))
    await http.put(`/system/role/${id}/menus`, { menuIds })
    await http.put(`/system/role/${id}/perm-detail`, { permDetail })
    await http.put(`/system/role/${id}/data-scope`, { dataScope: draft.scope })
    await http.put(`/system/role/${id}/dingtalk-position`, { dingtalkPosition: draft.position })
    drawer.value = false
    await load()
  } catch (e: unknown) {
    saveError.value = errorMessage(e)
  }
}

async function preview(row: Record<string, unknown>) {
  diff.value = ''
  previewError.value = ''
  try {
    const res = await http.post(`/system/role/${row.id}/preview`, { userId: user.profile?.userId || '1' })
    diff.value = JSON.stringify(res.data?.data ?? null, null, 2)
  } catch (e: unknown) {
    previewError.value = errorMessage(e)
  }
}

onMounted(async () => {
  await loadMenus()
  await load()
})
</script>
