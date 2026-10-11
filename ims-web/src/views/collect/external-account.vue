<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品账号配置</h1>
        <div class="sub">UX-M8 §3.2 · 行内不嵌 Cookie（ADR-052） · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-import-open" @click="openImport">导入</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-batch-delete" @click="askBatchDelete">批量删除</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-credential-open" @click="openCredential">租户采集凭账号</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="acct-source-open" @click="openSource">外部 HTTP 数据源</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="acct-create" @click="openCreate">新增外部账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">配置行不含 Cookie；自有平台账号凭证见公司资产 · 账号详情 · 采集 Tab。本地桩不连接快手或抖音。</p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.configName" data-testid="acct-name" placeholder="账号名称" style="width: 140px" />
      <select v-model="filters.platformType" data-testid="acct-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
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
              <th></th>
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
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="acct-empty">
                  <div class="et">{{ accountEmptyTitle }}</div>
                  <div class="es" data-testid="acct-empty-hint">{{ accountEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="'acct-row-' + row.id">
              <td><input type="checkbox" data-testid="acct-check" :checked="selected.has(row.id)" @change="toggleSelect(row.id)" /></td>
              <td class="mono">{{ row.id }}</td>
              <td><span class="chip">{{ platformLabel(row.platformType) }}</span></td>
              <td>{{ row.configName }}</td>
              <td class="mono">{{ row.accountIdentifier }}</td>
              <td data-testid="acct-collect-cell">
                <button
                  class="sw"
                  :class="{ on: row.collectEnabled }"
                  type="button"
                  data-testid="acct-collect-switch"
                  :aria-pressed="row.collectEnabled ? 'true' : 'false'"
                  @click="toggleCollect(row)"
                >
                  <i></i>
                </button>
              </td>
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
        <FormField label="账号名称" required :error="errors.configName">
          <input v-model="form.configName" data-testid="acct-form-name" />
        </FormField>
        <FormField label="平台" required>
          <select v-model="form.platformType" data-testid="acct-form-platform">
            <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </FormField>
        <FormField label="账号标识" required :error="errors.accountIdentifier">
          <input v-model="form.accountIdentifier" data-testid="acct-form-id" class="mono" />
        </FormField>
        <FormField label="参与采集">
          <select v-model="form.collectEnabled" data-testid="acct-form-collect">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </FormField>
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

    <ProtoDrawer :open="importOpen" title="导入竞品账号" width="480px" @close="importOpen = false">
      <p class="hint">模板列：platform,nick,url,keyword,enabled。导入后进入候选池，待启用。</p>
      <p><button class="btn btn-sec btn-sm" type="button" data-testid="acct-template" @click="downloadTemplate">下载模板</button></p>
      <FormField label="文件" required :error="importError">
        <input data-testid="acct-import-file" type="file" accept=".csv,text/csv" @change="onImportFile" />
      </FormField>
      <p v-if="importMsg" class="hint" data-testid="acct-import-msg">{{ importMsg }}</p>
      <div class="drawer-actions">
        <button class="btn btn-sec" type="button" @click="importOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="acct-import-submit" @click="submitImport">导入</button>
      </div>
    </ProtoDrawer>

    <ProtoDrawer :open="credentialOpen" title="租户采集凭账号" width="640px" @close="credentialOpen = false">
      <form class="drawer-form" @submit.prevent="saveCredential">
        <FormField label="平台" required :error="credErrors.platformType">
          <select v-model="credForm.platformType" data-testid="cred-platform">
            <option v-for="p in platforms" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
        </FormField>
        <FormField label="profile" required :error="credErrors.profile">
          <input v-model="credForm.profile" data-testid="cred-profile" />
        </FormField>
        <FormField label="展示名" required :error="credErrors.displayName">
          <input v-model="credForm.displayName" data-testid="cred-name" />
        </FormField>
        <FormField label="Cookie / Token" required :error="credErrors.secret">
          <input v-model="credForm.secret" data-testid="cred-secret" type="password" autocomplete="new-password" />
        </FormField>
        <FormField label="过期时间">
          <input v-model="credForm.expireAt" data-testid="cred-expire" placeholder="YYYY-MM-DD" />
        </FormField>
        <p v-if="credMsg" class="hint">{{ credMsg }}</p>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="cred-save">保存凭账号</button>
      </form>
      <table data-testid="cred-table" style="margin-top: 12px">
        <thead>
          <tr>
            <th>平台</th>
            <th>profile</th>
            <th>展示名</th>
            <th>连接状态</th>
            <th>过期时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!credentials.length"><td colspan="7"><div class="empty"><div class="et">暂无凭账号</div></div></td></tr>
          <tr v-for="row in credentials" :key="row.id">
            <td>{{ platformLabel(row.platformType) }}</td>
            <td>{{ row.profile }}</td>
            <td>{{ row.displayName }}</td>
            <td>{{ row.connStatus }}</td>
            <td>{{ row.expireAt || '—' }}</td>
            <td>{{ row.status }}</td>
            <td>
              <span class="mono" data-testid="cred-mask">{{ row.secretMask }}</span>
              <button class="btn-txt btn" type="button" data-testid="cred-probe" @click="probeCredential(row)">探活</button>
            </td>
          </tr>
        </tbody>
      </table>
    </ProtoDrawer>

    <ProtoDrawer :open="sourceOpen" title="外部 HTTP 数据源" width="520px" @close="sourceOpen = false">
      <form class="drawer-form" @submit.prevent="saveSource">
        <FormField label="名称" required :error="sourceErrors.sourceName">
          <input v-model="sourceForm.sourceName" data-testid="source-name" />
        </FormField>
        <FormField label="Base URL" required :error="sourceErrors.baseUrl">
          <input v-model="sourceForm.baseUrl" data-testid="source-url" placeholder="https://" />
        </FormField>
        <p v-if="sourceMsg" class="hint" data-testid="source-msg">{{ sourceMsg }}</p>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="source-save">保存数据源</button>
      </form>
      <table style="margin-top: 12px">
        <thead><tr><th>名称</th><th>地址</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-if="!sources.length"><td colspan="3"><div class="empty"><div class="et">暂无数据源</div></div></td></tr>
          <tr v-for="row in sources" :key="row.id">
            <td>{{ row.sourceName }}</td>
            <td class="mono">{{ row.baseUrl }}</td>
            <td>{{ row.status }}</td>
          </tr>
        </tbody>
      </table>
    </ProtoDrawer>
    <ConfirmDialog
      :open="batchOpen"
      title="批量删除"
      message="删除后历史采集数据保留，但停止更新"
      @cancel="batchOpen = false"
      @confirm="confirmBatchDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ConfirmDialog from '../../components/form/ConfirmDialog.vue'
import FormField from '../../components/form/FormField.vue'
import { requiredError } from '../../components/form/required'
import { showToast } from '../../components/form/toast'
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
const platforms = [
  { value: 'DOUYIN', label: '抖音' },
  { value: 'KUAISHOU', label: '快手' },
  { value: 'XIAOHONGSHU', label: '小红书' },
]
const PLATFORM_LABEL: Record<string, string> = Object.fromEntries(platforms.map((item) => [item.value, item.label]))
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
const errors = reactive<Record<string, string>>({})
const selected = ref(new Set<string>())
const importOpen = ref(false)
const importError = ref('')
const importMsg = ref('')
const importText = ref('')
const credentialOpen = ref(false)
const sourceOpen = ref(false)
const batchOpen = ref(false)
const credentials = ref<any[]>([])
const sources = ref<any[]>([])
const credMsg = ref('')
const sourceMsg = ref('')
const credErrors = reactive<Record<string, string>>({})
const sourceErrors = reactive<Record<string, string>>({})
const credForm = reactive({ platformType: 'DOUYIN', profile: 'default', displayName: '', secret: '', expireAt: '', status: 'ENABLED' })
const sourceForm = reactive({ sourceName: '', baseUrl: '', status: 'ENABLED' })

function platformLabel(code: string) {
  return PLATFORM_LABEL[code] || code
}

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
  errors.configName = ''
  errors.accountIdentifier = ''
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
  errors.configName = requiredError(form.configName)
  errors.accountIdentifier = requiredError(form.accountIdentifier)
  if (errors.configName || errors.accountIdentifier) return
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
    showToast('采集配置已保存')
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  }
}

function toggleSelect(id: string) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

async function toggleCollect(row: AccountRow) {
  try {
    await http.put(`/collect/external/account/${row.id}`, {
      configName: row.configName,
      platformType: row.platformType,
      accountIdentifier: row.accountIdentifier,
      collectEnabled: !row.collectEnabled,
      status: row.status,
    })
    showToast('是否采集已更新')
    await loadList()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function openImport() {
  importError.value = ''
  importMsg.value = ''
  importText.value = ''
  importOpen.value = true
}

function downloadTemplate() {
  const blob = new Blob(['platform,nick,url,keyword,enabled\n'], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'competitor-accounts.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

function onImportFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  importError.value = ''
  importMsg.value = ''
  importText.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importText.value = String(reader.result || '')
  }
  reader.readAsText(file)
}

async function submitImport() {
  if (!importText.value.trim()) {
    importError.value = '请先选择文件'
    return
  }
  try {
    const res = await http.post('/collect/external/account/import', { csvText: importText.value })
    importMsg.value = res.data?.data?.message || '已进入候选池，待启用'
    showToast(importMsg.value)
    await loadList()
  } catch (e) {
    importMsg.value = errorMessage(e)
  }
}

function askBatchDelete() {
  if (!selected.value.size) {
    showToast('请先勾选账号', 'warn')
    return
  }
  batchOpen.value = true
}

async function confirmBatchDelete() {
  batchOpen.value = false
  try {
    const res = await http.post('/collect/external/account/batch-delete', { ids: [...selected.value].map(Number) })
    showToast(res.data?.data?.message || '历史采集数据保留，已停止更新')
    selected.value = new Set()
    await loadList()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function loadCredentials() {
  const res = await http.get('/collect/external/credential/page')
  credentials.value = res.data?.data?.list || []
}

function openCredential() {
  credMsg.value = ''
  credentialOpen.value = true
  loadCredentials()
}

async function saveCredential() {
  credErrors.platformType = requiredError(credForm.platformType)
  credErrors.profile = requiredError(credForm.profile)
  credErrors.displayName = requiredError(credForm.displayName)
  credErrors.secret = requiredError(credForm.secret)
  if (Object.values(credErrors).some(Boolean)) return
  try {
    await http.post('/collect/external/credential', { ...credForm })
    credForm.secret = ''
    credMsg.value = '凭账号已保存，页面只显示掩码'
    showToast('采集配置已保存')
    await loadCredentials()
  } catch (e) {
    credMsg.value = errorMessage(e)
  }
}

async function probeCredential(row: { id: string }) {
  try {
    const res = await http.post(`/collect/external/credential/${row.id}/probe`)
    showToast(res.data?.data?.message || '探活完成')
    await loadCredentials()
  } catch (e) {
    credMsg.value = errorMessage(e)
  }
}

async function loadSources() {
  const res = await http.get('/collect/external/source/page')
  sources.value = res.data?.data?.list || []
}

function openSource() {
  sourceMsg.value = ''
  sourceOpen.value = true
  loadSources()
}

async function saveSource() {
  sourceErrors.sourceName = requiredError(sourceForm.sourceName)
  sourceErrors.baseUrl = requiredError(sourceForm.baseUrl)
  if (sourceErrors.sourceName || sourceErrors.baseUrl) return
  try {
    await http.post('/collect/external/source', { ...sourceForm })
    sourceForm.sourceName = ''
    sourceForm.baseUrl = ''
    showToast('采集配置已保存')
    await loadSources()
  } catch (e) {
    sourceMsg.value = errorMessage(e)
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
button.sw {
  border: 0;
  padding: 2px;
}
</style>
