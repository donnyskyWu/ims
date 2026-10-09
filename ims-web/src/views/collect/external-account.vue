<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品账号配置</h1>
        <div class="sub">UX-M8 §3.2 · 行内不嵌 Cookie（ADR-052） · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="acct-create" @click="openCreate">新增外部账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">配置行不含 Cookie；自有平台账号凭证见公司资产 · 账号详情 · 采集 Tab。本地桩不连接快手或抖音。</p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.configName" data-testid="acct-name" placeholder="账号名称" style="width: 140px" />
      <select v-model="filters.platformType" data-testid="acct-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.status" data-testid="acct-status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <select v-model="filters.collectEnabled" data-testid="acct-collect" style="width: 120px">
        <option value="">是否采集</option>
        <option value="1">只看采集</option>
        <option value="0">只看不采集</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="acct-query">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="acct-reset" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="acct-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>账号名称</th>
              <th>账号标识</th>
              <th>采集</th>
              <th>状态</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8">
                <div class="empty" data-testid="acct-empty">
                  <div class="et">{{ accountEmptyTitle }}</div>
                  <div class="es" data-testid="acct-empty-hint">{{ accountEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="'acct-row-' + row.id">
              <td class="mono">{{ row.id }}</td>
              <td><span class="chip">{{ row.platformType }}</span></td>
              <td>{{ row.configName }}</td>
              <td class="mono">{{ row.accountIdentifier }}</td>
              <td data-testid="acct-collect-cell">{{ row.collectEnabled ? '是' : '否' }}</td>
              <td><span class="chip">{{ statusLabel(row.status) }}</span></td>
              <td class="num" style="font-size: 11px">{{ row.updatedAt || '—' }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn-txt btn" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>
    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑外部账号' : '新增外部账号'" width="480px" @close="drawerOpen = false">
      <form class="drawer-form" @submit.prevent="save">
        <label>
          账号名称
          <input v-model="form.configName" data-testid="acct-form-name" required />
        </label>
        <label>
          平台
          <select v-model="form.platformType" data-testid="acct-form-platform">
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label>
          账号标识
          <input v-model="form.accountIdentifier" data-testid="acct-form-id" class="mono" required />
        </label>
        <label>
          参与采集
          <select v-model="form.collectEnabled" data-testid="acct-form-collect">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </label>
        <label>
          状态
          <select v-model="form.status" data-testid="acct-form-status">
            <option value="ENABLED">启用</option>
            <option value="DISABLED">停用</option>
          </select>
        </label>
        <p v-if="formMsg" class="hint" data-testid="acct-form-msg">{{ formMsg }}</p>
        <div class="drawer-actions">
          <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri" type="submit" data-testid="acct-save">保存</button>
        </div>
      </form>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type AccountRow = {
  id: string
  configName: string
  platformType: string
  accountIdentifier: string
  collectEnabled: boolean
  status: string
  updatedAt: string
}

const STATUS_LABEL: Record<string, string> = { ENABLED: '启用', DISABLED: '停用' }
const platforms = ['DOUYIN', 'KUAISHOU', 'XIAOHONGSHU']
const rows = ref<AccountRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editingId = ref('')
const formMsg = ref('')
const filters = reactive({ configName: '', platformType: '', status: '', collectEnabled: '' })
const form = reactive({
  configName: '',
  platformType: 'DOUYIN',
  accountIdentifier: '',
  collectEnabled: true,
  status: 'ENABLED',
})

const filtersActive = computed(
  () => Boolean(filters.configName.trim() || filters.platformType || filters.status || filters.collectEnabled),
)
const accountEmptyTitle = computed(() => {
  if (error.value) return error.value
  if (filters.collectEnabled === '1') return '没有打开采集的外部账号'
  if (filters.collectEnabled === '0') return '没有关闭采集的外部账号'
  if (filtersActive.value) return '没有符合筛选的外部账号'
  return '暂无外部账号配置'
})
const accountEmptyHint = computed(() => {
  if (filters.collectEnabled) {
    return '只有启用且打开采集的账号会进入外部统一任务。本页不写 Cookie，本地桩也不连快手或抖音。'
  }
  if (filtersActive.value) return '换个名称、平台或状态，或重置筛选。'
  return '新增外部账号后会出现在这里。配置行不填写平台 Cookie。'
})

function statusLabel(code: string) {
  return STATUS_LABEL[code] || code
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.configName.trim()) params.configName = filters.configName.trim()
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.status) params.status = filters.status
    if (filters.collectEnabled) params.collectEnabled = filters.collectEnabled
    const res = await http.get('/collect/external/account/page', { params })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.configName = ''
  filters.platformType = ''
  filters.status = ''
  filters.collectEnabled = ''
  loadList()
}

function openCreate() {
  editingId.value = ''
  form.configName = ''
  form.platformType = 'DOUYIN'
  form.accountIdentifier = ''
  form.collectEnabled = true
  form.status = 'ENABLED'
  formMsg.value = ''
  drawerOpen.value = true
}

function openEdit(row: AccountRow) {
  editingId.value = String(row.id)
  form.configName = String(row.configName || '')
  form.platformType = String(row.platformType || 'DOUYIN')
  form.accountIdentifier = String(row.accountIdentifier || '')
  form.collectEnabled = Boolean(row.collectEnabled)
  form.status = String(row.status || 'ENABLED')
  formMsg.value = ''
  drawerOpen.value = true
}

async function save() {
  formMsg.value = ''
  if (!form.configName.trim() || !form.accountIdentifier.trim()) {
    formMsg.value = '请填写账号名称和账号标识'
    return
  }
  try {
    const body = {
      configName: form.configName.trim(),
      platformType: form.platformType,
      accountIdentifier: form.accountIdentifier.trim(),
      collectEnabled: form.collectEnabled,
      status: form.status,
    }
    if (editingId.value) {
      await http.put(`/collect/external/account/${editingId.value}`, body)
    } else {
      await http.post('/collect/external/account', body)
    }
    drawerOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  }
}

async function remove(row: AccountRow) {
  if (!confirm(`删除外部账号「${row.configName}」？`)) return
  await http.delete(`/collect/external/account/${row.id}`)
  await loadList()
}

onMounted(loadList)
</script>

<style scoped>
.drawer-form label {
  display: block;
  margin-bottom: 12px;
  font-size: 13px;
}
.drawer-form input,
.drawer-form select {
  display: block;
  width: 100%;
  margin-top: 4px;
}
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
