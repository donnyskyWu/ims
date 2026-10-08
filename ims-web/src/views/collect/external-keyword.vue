<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品关键字配置</h1>
        <div class="sub">UX-M8 §3.3 · Channel-D 关键词 · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增关键词</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" placeholder="关键词" style="width: 140px" />
      <select v-model="filters.platformType" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>平台</th>
              <th>关键词</th>
              <th>匹配类型</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length && !loading">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无关键词' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td><span class="chip">{{ row.platformType }}</span></td>
              <td>{{ row.keyword }}</td>
              <td>{{ row.matchType }}</td>
              <td>{{ row.status }}</td>
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
        <h3>{{ editingId ? '编辑关键词' : '新增关键词' }}</h3>
        <div class="formrow">
          <label>平台</label>
          <select v-model="form.platformType">
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="formrow">
          <label>关键词</label>
          <input v-model="form.keyword" />
        </div>
        <div class="formrow">
          <label>匹配类型</label>
          <select v-model="form.matchType">
            <option value="EXACT">EXACT</option>
            <option value="CONTAINS">CONTAINS</option>
            <option value="FUZZY">FUZZY</option>
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
const filters = reactive({ keyword: '', platformType: '' })
const form = reactive({
  platformType: 'DOUYIN',
  keyword: '',
  matchType: 'CONTAINS',
  status: 'ENABLED',
})

async function loadList() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.platformType) params.platformType = filters.platformType
    const res = await http.get('/collect/external/keyword/page', { params })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = ''
  form.platformType = 'DOUYIN'
  form.keyword = ''
  form.matchType = 'CONTAINS'
  form.status = 'ENABLED'
  formMsg.value = ''
  drawerOpen.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingId.value = String(row.id)
  form.platformType = String(row.platformType || '')
  form.keyword = String(row.keyword || '')
  form.matchType = String(row.matchType || 'CONTAINS')
  form.status = String(row.status || 'ENABLED')
  drawerOpen.value = true
}

async function save() {
  formMsg.value = ''
  try {
    if (editingId.value) {
      await http.put(`/collect/external/keyword/${editingId.value}`, form)
    } else {
      await http.post('/collect/external/keyword', form)
    }
    drawerOpen.value = false
    await loadList()
  } catch (e) {
    formMsg.value = e instanceof Error ? e.message : '保存失败'
  }
}

async function remove(row: Record<string, unknown>) {
  await http.delete(`/collect/external/keyword/${row.id}`)
  await loadList()
}

onMounted(loadList)
</script>
