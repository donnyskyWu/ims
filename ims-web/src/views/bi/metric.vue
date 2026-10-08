<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>指标管理</h1>
        <div class="sub">FR-M6-001 · /ims/bi/metric · 17a BI0</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建指标</button>
      </div>
    </div>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" placeholder="指标名称/编码" style="width: 160px" />
      <select v-model="filters.metricType" style="width: 130px">
        <option value="">全部类型</option>
        <option value="BASIC">基础指标</option>
        <option value="COMPOSITE">复合指标</option>
      </select>
      <select v-model="filters.category" style="width: 120px">
        <option value="">全部分类</option>
        <option value="内容表现">内容表现</option>
        <option value="账号经营">账号经营</option>
        <option value="经营转化">经营转化</option>
        <option value="财务效率">财务效率</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>类型</th>
              <th>分类</th>
              <th>频率</th>
              <th>状态</th>
              <th>引用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length"><td colspan="8"><div class="empty"><div class="et">暂无指标</div></div></td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.metricCode }}</td>
              <td style="font-weight: 500">{{ row.metricName }}</td>
              <td>{{ row.metricType === 'COMPOSITE' ? '复合' : '基础' }}</td>
              <td>{{ row.category }}</td>
              <td>{{ row.calcFreq }}</td>
              <td>{{ row.status === 'ENABLED' ? '启用' : '停用' }}</td>
              <td>{{ row.refCount }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="preview(row.id)">试算</button>
                <button class="btn btn-sec btn-sm" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="previewResult" class="card hint" style="margin-top: 12px; padding: 12px">
      试算 · {{ previewResult.metricName }} = {{ previewResult.value }} {{ previewResult.unit }}
      <span class="csub">（{{ previewResult.note }}）</span>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建指标</h3>
        <label class="fld">名称</label>
        <input v-model="form.metricName" class="fld-in" />
        <label class="fld">类型</label>
        <select v-model="form.metricType" class="fld-in">
          <option value="BASIC">基础指标 BASIC</option>
          <option value="COMPOSITE">复合指标 COMPOSITE</option>
        </select>
        <label class="fld">分类</label>
        <select v-model="form.category" class="fld-in">
          <option value="内容表现">内容表现</option>
          <option value="账号经营">账号经营</option>
          <option value="经营转化">经营转化</option>
          <option value="财务效率">财务效率</option>
        </select>
        <label class="fld">公式（复合可选）</label>
        <input v-model="form.formula" class="fld-in" placeholder="如 A + B" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = {
  id: number
  metricCode: string
  metricName: string
  metricType: string
  category: string
  calcFreq: string
  status: string
  refCount: number
}

const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')
const previewResult = ref<{ metricName: string; value: number; unit: string; note: string } | null>(null)
const filters = reactive({ keyword: '', metricType: '', category: '', status: '' })
const form = reactive({ metricName: '', metricType: 'BASIC', category: '内容表现', formula: '' })

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/bi/metric/list', {
      params: {
        keyword: filters.keyword || undefined,
        metricType: filters.metricType || undefined,
        category: filters.category || undefined,
        status: filters.status || undefined,
        pageNo: 1,
        pageSize: 50,
      },
    })
    if (res.data.code === 0) rows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.metricName = ''
  form.metricType = 'BASIC'
  form.category = '内容表现'
  form.formula = ''
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  if (!form.metricName.trim()) {
    formError.value = '请输入指标名称'
    return
  }
  const res = await http.post('/bi/metric', {
    metricName: form.metricName.trim(),
    metricType: form.metricType,
    category: form.category,
    formula: form.formula.trim(),
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadList()
}

async function preview(id: number) {
  const res = await http.post(`/bi/metric/${id}/preview`, {})
  if (res.data.code === 0) previewResult.value = res.data.data
}

async function remove(row: Row) {
  if (row.refCount > 0) {
    formError.value = '指标已被引用，不可删除'
    return
  }
  const res = await http.delete(`/bi/metric/${row.id}`)
  if (res.data.code === 0) await loadList()
  else formError.value = res.data.msg || '删除失败'
}

onMounted(loadList)
</script>
