<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品账号配置</h1>
        <div class="sub">UX-M8 §3.2 · 行内不嵌 Cookie（ADR-052） · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增外部账号</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">配置行不含 Cookie；自有平台账号凭证见公司资产 · 账号详情 · 采集 Tab。</p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.configName" placeholder="账号名称" style="width: 140px" />
      <select v-model="filters.platformType" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">ENABLED</option>
        <option value="DISABLED">DISABLED</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
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
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无外部账号配置' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td><span class="chip">{{ row.platformType }}</span></td>
              <td>{{ row.configName }}</td>
              <td class="mono">{{ row.accountIdentifier }}</td>
              <td>{{ row.collectEnabled ? '是' : '否' }}</td>
              <td><span class="chip">{{ row.status }}</span></td>
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
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer">
        <h3>{{ editingId ? '编辑外部账号' : '新增外部账号' }}</h3>
        <div class="formrow">
          <label>账号名称</label>
          <input v-model="form.configName" />
        </div>
        <div class="formrow">
          <label>平台</label>
          <select v-model="form.platformType">
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="formrow">
          <label>账号标识</label>
          <input v-model="form.accountIdentifier" class="mono" />
        </div>
        <div class="formrow">
          <label>参与采集</label>
          <select v-model="form.collectEnabled">
            <option :value="true">是</option>
            <option :value="false">否</option>
          </select>
        </div>
        <div class="formrow">
          <label>状态</label>
          <select v-model="form.status">
            <option value="ENABLED">ENABLED</option>
            <option value="DISABLED">DISABLED</option>
          </select>
        </div>
        <p v-if="formMsg" class="hint">{{ formMsg }}</p>
        <div class="drawer-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

const platforms = ['DOUYIN', 'KUAISHOU', 'XIAOHONGSHU']
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editingId = ref('')
const formMsg = ref('')
const filters = reactive({ configName: '', platformType: '', status: '' })
const form = reactive({
  configName: '',
  platformType: 'DOUYIN',
  accountIdentifier: '',
  collectEnabled: true,
  status: 'ENABLED',
})

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.configName) params.configName = filters.configName
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.status) params.status = filters.status
    const res = await http.get('/collect/external/account/page', { params })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.configName = ''
  filters.platformType = ''
  filters.status = ''
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

function openEdit(row: Record<string, unknown>) {
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
  try {
    const body = { ...form }
    if (editingId.value) {
      await http.put(`/collect/external/account/${editingId.value}`, body)
    } else {
      await http.post('/collect/external/account', body)
    }
    drawerOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = e instanceof Error ? e.message : '保存失败'
  }
}

async function remove(row: Record<string, unknown>) {
  await http.delete(`/collect/external/account/${row.id}`)
  await loadList()
}

onMounted(loadList)
</script>
