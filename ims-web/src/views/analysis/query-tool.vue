<template>
  <div class="page page-query-tool">
    <div class="pg-h">
      <div>
        <h1>查询工具</h1>
        <div class="sub">QT-001 · /ims/analysis/query-tool · DRILL|TRACE · 17c QT</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/collect/metadata">元数据维护</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/dc/trace">穿透查询 L3</router-link>
      </div>
    </div>

    <div class="card bi0-mine-card">
      <div class="bi0-mine-hd">
        <div class="hd-row" style="justify-content: space-between; align-items: center; gap: 12px">
          <div>
            <h3 style="font-size: 17px; font-weight: 600; margin: 0">查询模板</h3>
            <span class="csub">共 {{ total }} 条 · 列表默认落地</span>
          </div>
          <button class="btn btn-pri btn-sm" type="button" @click="openCreate">+ 新增查询模板</button>
        </div>
      </div>
      <div class="bi0-mine-body">
        <form class="qbar" @submit.prevent="loadList">
          <input v-model="filters.keyword" placeholder="名称" style="width: 180px" />
          <select v-model="filters.status" class="qt-qctl" style="width: 120px">
            <option value="">全部状态</option>
            <option value="DRAFT">草稿</option>
            <option value="PUBLISHED">已发布</option>
          </select>
          <select v-model="filters.mode" style="width: 110px">
            <option value="">全部模式</option>
            <option value="DRILL">DRILL</option>
            <option value="TRACE">TRACE</option>
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
                  <th>查询名称</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>更新时间</th>
                  <th>菜单路径</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
                </tr>
                <tr v-else-if="!rows.length">
                  <td colspan="6"><div class="empty"><div class="et">暂无模板</div></div></td>
                </tr>
                <tr v-for="row in rows" v-else :key="row.templateCode">
                  <td style="font-weight: 500">{{ row.name }}</td>
                  <td><span class="tag" :style="modeStyle(row.mode)"><span class="dot"></span>{{ row.mode }}</span></td>
                  <td><span class="tag" :style="statusStyle(row.status)"><span class="dot"></span>{{ statusLabel(row.status) }}</span></td>
                  <td class="num">{{ formatTime(row.updatedAt) }}</td>
                  <td>{{ row.menuPathLabel || '—' }}</td>
                  <td>
                    <span class="btn-txt btn" @click="runRow(row)">执行</span>
                    <span v-if="row.status === 'DRAFT'" class="btn-txt btn" @click="publishRow(row)">发布</span>
                    <span v-else class="btn-txt btn" @click="unpublishRow(row)">取消发布</span>
                    <span class="btn-txt btn btn-danger-txt" @click="deleteRow(row)">删除</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="runResult" class="card bi0-result-card" style="margin-top: 16px; padding: 16px">
      <h3 style="margin: 0 0 8px">执行结果 · {{ runResult.templateCode || 'inline' }}</h3>
      <p class="csub">queryCostMs={{ runResult.queryCostMs }} · {{ runResult.note }}</p>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr><th v-for="c in runResult.columns" :key="c.key">{{ c.label }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, idx) in runResult.rows" :key="idx">
              <td v-for="c in runResult.columns" :key="c.key">{{ r[c.key] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新增查询模板</h3>
        <div class="fld"><label>名称</label><input v-model="form.name" /></div>
        <div class="fld">
          <label>模式</label>
          <select v-model="form.mode">
            <option value="DRILL">DRILL</option>
            <option value="TRACE">TRACE</option>
          </select>
        </div>
        <div class="fld"><label>说明</label><input v-model="form.desc" /></div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">存草稿</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = {
  templateCode: string
  name: string
  mode: string
  status: string
  updatedAt: string
  menuPathLabel?: string
}

const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const filters = reactive({ keyword: '', status: '', mode: '' })
const showForm = ref(false)
const form = reactive({ name: '', mode: 'DRILL', desc: '' })
const runResult = ref<Record<string, unknown> | null>(null)

function statusLabel(s: string) {
  return s === 'PUBLISHED' ? '已发布' : '草稿'
}

function statusStyle(s: string) {
  return s === 'PUBLISHED'
    ? { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
    : { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}

function modeStyle(m: string) {
  return m === 'TRACE'
    ? { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
    : { background: 'rgba(175,82,218,.12)', color: '#8944ab' }
}

function formatTime(iso: string) {
  return iso ? iso.replace('T', ' ').slice(0, 16) : '—'
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/analysis/query-tool/template/page', {
      params: {
        keyword: filters.keyword || undefined,
        status: filters.status || undefined,
        mode: filters.mode || undefined,
        pageNo: 1,
        pageSize: 20,
      },
    })
    if (res.data?.code === 0) {
      rows.value = res.data.data.list || []
      total.value = res.data.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.mode = ''
  loadList()
}

function openCreate() {
  form.name = ''
  form.mode = 'DRILL'
  form.desc = ''
  showForm.value = true
}

async function submitCreate() {
  const res = await http.post('/analysis/query-tool/template', {
    name: form.name,
    mode: form.mode,
    desc: form.desc,
    payloadJson: {},
  })
  if (res.data?.code !== 0) {
    alert(res.data?.msg || '创建失败')
    return
  }
  showForm.value = false
  loadList()
}

async function publishRow(row: Row) {
  await http.post(`/analysis/query-tool/template/${row.templateCode}/publish`)
  loadList()
}

async function unpublishRow(row: Row) {
  await http.post(`/analysis/query-tool/template/${row.templateCode}/unpublish`)
  loadList()
}

async function deleteRow(row: Row) {
  if (!confirm(`删除模板「${row.name}」？`)) return
  const res = await http.delete(`/analysis/query-tool/template/${row.templateCode}`)
  if (res.data?.code !== 0) {
    alert(res.data?.msg || '删除失败')
    return
  }
  loadList()
}

async function runRow(row: Row) {
  const res = await http.post('/analysis/query-tool/run', {
    mode: row.mode,
    templateCode: row.status === 'PUBLISHED' ? row.templateCode : undefined,
    runtime: {},
  })
  if (res.data?.code !== 0) {
    alert(res.data?.msg || '执行失败')
    return
  }
  runResult.value = res.data.data
}

onMounted(loadList)
</script>
