<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表管理</h1>
        <div class="sub">
          报表/大屏统一目录 · /ims/bi/report/list · BI-001 首片 · 列表按 BR-212 行级过滤（创建者 ∩ 查看者）
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建报表</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/subscribe">订阅与分享</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/preview">预览与下钻</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report">报表中心</router-link>
      </div>
    </div>

    <div class="qbar">
      <input v-model="filters.keyword" placeholder="名称/编号" style="width: 140px" />
      <select v-model="filters.reportType" style="width: 110px">
        <option value="">全部类型</option>
        <option value="REPORT">报表</option>
        <option value="DASHBOARD">大屏</option>
      </select>
      <select v-model="filters.category" style="width: 120px">
        <option value="">全部分类</option>
        <option v-for="c in categories" :key="c.code" :value="c.name">{{ c.name }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadList">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="viewMode = viewMode === 'card' ? 'table' : 'card'">
        {{ viewMode === 'card' ? '列表' : '卡片' }}
      </button>
    </div>

    <div v-if="viewMode === 'card'" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 12px">
      <div v-for="row in rows" :key="row.id" class="card hov">
        <div class="rowline" style="justify-content: space-between">
          <b>{{ row.reportName }}</b>
          <span class="tag tag-info">{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</span>
        </div>
        <div class="csub" style="margin-top: 6px">{{ row.category }} / {{ row.subCategory || '—' }}</div>
        <div class="csub mono" style="margin-top: 4px">{{ row.reportNo }} · {{ row.status }}</div>
        <button class="btn btn-sec btn-sm" type="button" style="margin-top: 10px" @click="openDesigner(row.id)">编辑设计</button>
      </div>
      <div v-if="!loading && !rows.length" class="card" style="grid-column: 1 / -1">
        <div class="empty"><div class="et">暂无报表，点击新建</div></div>
      </div>
    </div>

    <div v-else class="tbl-block" style="margin-top: 12px">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>名称</th>
              <th>类型</th>
              <th>分类</th>
              <th>状态</th>
              <th>更新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="7"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length"><td colspan="7"><div class="empty"><div class="et">暂无报表</div></div></td></tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.reportNo }}</td>
              <td>{{ row.reportName }}</td>
              <td>{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</td>
              <td>{{ row.category }}</td>
              <td>{{ row.status }}</td>
              <td class="csub">{{ row.updatedAt }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openDesigner(row.id)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建报表</h3>
        <label class="fld">报表类型</label>
        <div class="rowline" style="gap: 8px; margin-bottom: 10px">
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'REPORT' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'REPORT'"
          >
            报表
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="form.reportType === 'DASHBOARD' ? 'btn-pri' : 'btn-sec'"
            @click="form.reportType = 'DASHBOARD'"
          >
            大屏
          </button>
        </div>
        <label class="fld">名称</label>
        <input v-model="form.reportName" class="fld-in" />
        <label class="fld">分类</label>
        <select v-model="form.category" class="fld-in">
          <option v-for="c in categories" :key="c.code" :value="c.name">{{ c.name }}</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存草稿</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()

type Row = {
  id: number
  reportNo: string
  reportName: string
  reportType: string
  category: string
  subCategory: string
  status: string
  updatedAt: string
}

type Cat = { code: string; name: string; children: string[] }

const rows = ref<Row[]>([])
const categories = ref<Cat[]>([])
const loading = ref(false)
const viewMode = ref<'card' | 'table'>('card')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ keyword: '', reportType: '', category: '' })
const form = reactive({ reportName: '', reportType: 'REPORT', category: '内容分析' })

async function loadCategories() {
  const res = await http.get('/bi/report/categories')
  if (res.data.code === 0) categories.value = res.data.data.categories || []
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/bi/report/list', {
      params: {
        keyword: filters.keyword || undefined,
        reportType: filters.reportType || undefined,
        category: filters.category || undefined,
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
  form.reportName = ''
  form.reportType = 'REPORT'
  form.category = categories.value[0]?.name || '内容分析'
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  if (!form.reportName.trim()) {
    formError.value = '请输入名称'
    return
  }
  const res = await http.post('/bi/report', {
    reportName: form.reportName.trim(),
    reportType: form.reportType,
    category: form.category,
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  const rid = res.data.data?.id
  if (rid) {
    await router.push({ path: '/ims/bi/report/designer', query: { reportId: String(rid) } })
    return
  }
  await loadList()
}

function openDesigner(id: number) {
  router.push({ path: '/ims/bi/report/designer', query: { reportId: String(id) } })
}

onMounted(async () => {
  await loadCategories()
  await loadList()
})
</script>
