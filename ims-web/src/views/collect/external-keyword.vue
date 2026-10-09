<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品关键字配置</h1>
        <div class="sub">UX-M8 §3.3 · 开启采集后进入外部统一任务成员 · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="kw-create" @click="openCreate">新增关键词</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      「是否采集」打开且状态为启用的关键词，会出现在采集任务 · 外部统一任务的「外部成员」里。本页不填写 Cookie。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" data-testid="kw-keyword" placeholder="关键词" style="width: 140px" />
      <select v-model="filters.platformType" data-testid="kw-platform" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.status" data-testid="kw-status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <select v-model="filters.collectEnabled" data-testid="kw-collect-filter" style="width: 120px">
        <option value="">是否采集</option>
        <option value="1">只看采集</option>
        <option value="0">只看不采集</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="kw-query">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="kw-reset" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="kw-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>关键词</th>
              <th>是否采集</th>
              <th>匹配类型</th>
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
                <div class="empty" data-testid="kw-empty">
                  <div class="et">{{ error || keywordEmptyTitle }}</div>
                  <div class="es" data-testid="kw-empty-hint">{{ keywordEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="'kw-row-' + row.id">
              <td class="mono">{{ row.id }}</td>
              <td><span class="chip">{{ row.platformType }}</span></td>
              <td>{{ row.keyword }}</td>
              <td>
                <button
                  class="sw"
                  :class="{ on: row.collectEnabled }"
                  type="button"
                  data-testid="kw-collect"
                  :aria-pressed="row.collectEnabled ? 'true' : 'false'"
                  :disabled="togglingId === row.id"
                  @click="toggleCollect(row)"
                >
                  <i></i>
                </button>
              </td>
              <td>{{ matchLabel(row.matchType) }}</td>
              <td><span class="chip">{{ statusLabel(row.status) }}</span></td>
              <td class="num" data-testid="kw-updated" style="font-size: 11px">{{ row.updatedAt || '—' }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn-txt btn btn-danger-txt" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>
    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑关键词' : '新增关键词'" width="480px" @close="drawerOpen = false">
      <form class="drawer-form" @submit.prevent="save">
        <label>
          平台
          <select v-model="form.platformType" data-testid="kw-form-platform">
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label>
          关键词
          <input v-model="form.keyword" data-testid="kw-form-keyword" required />
        </label>
        <label>
          匹配类型
          <select v-model="form.matchType" data-testid="kw-form-match">
            <option value="EXACT">精确</option>
            <option value="CONTAINS">包含</option>
            <option value="FUZZY">模糊</option>
          </select>
        </label>
        <label>
          是否采集
          <select v-model="form.collectEnabled" data-testid="kw-form-collect">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </label>
        <label>
          状态
          <select v-model="form.status" data-testid="kw-form-status">
            <option value="ENABLED">启用</option>
            <option value="DISABLED">停用</option>
          </select>
        </label>
        <p v-if="formMsg" class="hint" data-testid="kw-form-msg">{{ formMsg }}</p>
        <div class="drawer-actions">
          <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri" type="submit" data-testid="kw-save">保存</button>
        </div>
      </form>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type KeywordRow = {
  id: string
  platformType: string
  keyword: string
  matchType: string
  collectEnabled: boolean
  status: string
  updatedAt: string
}

const MATCH_LABEL: Record<string, string> = {
  EXACT: '精确',
  CONTAINS: '包含',
  FUZZY: '模糊',
}
const STATUS_LABEL: Record<string, string> = {
  ENABLED: '启用',
  DISABLED: '停用',
}

const platforms = ['DOUYIN', 'KUAISHOU', 'XIAOHONGSHU']
const rows = ref<KeywordRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editingId = ref('')
const formMsg = ref('')
const togglingId = ref('')
const filters = reactive({ keyword: '', platformType: '', status: '', collectEnabled: '' })
const keywordFiltered = computed(() => Boolean(filters.keyword.trim() || filters.platformType || filters.status || filters.collectEnabled))
const keywordEmptyTitle = computed(() => (keywordFiltered.value ? '没有符合筛选的关键词' : '暂无关键词'))
const keywordEmptyHint = computed(() => {
  if (filters.collectEnabled === '1') {
    return '暂无关键词。当前只看已打开采集的关键词。停用或未打开的不会进入外部统一任务，本地桩不需要平台 Cookie。'
  }
  if (filters.collectEnabled === '0') {
    return '暂无关键词。当前只看未打开采集的关键词。它们不会进入外部统一任务。'
  }
  if (filters.keyword.trim() || filters.platformType || filters.status) {
    return '暂无关键词。换个关键词、平台或状态后再查。重置后可看全部。'
  }
  return '新增一条并打开「是否采集」，外部统一任务才会带上它'
})
const form = reactive({
  platformType: 'DOUYIN',
  keyword: '',
  matchType: 'CONTAINS',
  collectEnabled: true,
  status: 'ENABLED',
})

function matchLabel(code: string) {
  return MATCH_LABEL[code] || code
}
function statusLabel(code: string) {
  return STATUS_LABEL[code] || code
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.status) params.status = filters.status
    if (filters.collectEnabled) params.collectEnabled = filters.collectEnabled
    const res = await http.get('/collect/external/keyword/page', { params })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      rows.value = []
      return
    }
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
  filters.keyword = ''
  filters.platformType = ''
  filters.status = ''
  filters.collectEnabled = ''
  loadList()
}

function openCreate() {
  editingId.value = ''
  form.platformType = 'DOUYIN'
  form.keyword = ''
  form.matchType = 'CONTAINS'
  form.collectEnabled = true
  form.status = 'ENABLED'
  formMsg.value = ''
  drawerOpen.value = true
}

function openEdit(row: KeywordRow) {
  editingId.value = String(row.id)
  form.platformType = String(row.platformType || 'DOUYIN')
  form.keyword = String(row.keyword || '')
  form.matchType = String(row.matchType || 'CONTAINS')
  form.collectEnabled = Boolean(row.collectEnabled)
  form.status = String(row.status || 'ENABLED')
  formMsg.value = ''
  drawerOpen.value = true
}

function payload() {
  return {
    platformType: form.platformType,
    keyword: form.keyword.trim(),
    matchType: form.matchType,
    collectEnabled: form.collectEnabled,
    status: form.status,
  }
}

async function save() {
  formMsg.value = ''
  if (!form.keyword.trim()) {
    formMsg.value = '请填写关键词'
    return
  }
  try {
    const res = editingId.value
      ? await http.put(`/collect/external/keyword/${editingId.value}`, payload())
      : await http.post('/collect/external/keyword', payload())
    if (res.data?.code !== 0) {
      formMsg.value = res.data?.msg || '保存失败'
      return
    }
    drawerOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = errorMessage(e)
  }
}

async function toggleCollect(row: KeywordRow) {
  togglingId.value = row.id
  try {
    const res = await http.put(`/collect/external/keyword/${row.id}`, {
      platformType: row.platformType,
      keyword: row.keyword,
      matchType: row.matchType,
      collectEnabled: !row.collectEnabled,
      status: row.status,
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '更新是否采集失败'
      return
    }
    await loadList()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    togglingId.value = ''
  }
}

async function remove(row: KeywordRow) {
  if (!confirm(`删除关键词「${row.keyword}」？`)) return
  await http.delete(`/collect/external/keyword/${row.id}`)
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
