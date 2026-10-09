<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>公推模板库</h1>
        <div class="sub">CONTENT-107 · /content/layout-template · 15 CONTENT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建模板</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/content/list">内容管理</router-link>
      </div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.templateName" placeholder="模板名称" style="width: 140px" />
      <select v-model="filters.status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="DRAFT">DRAFT</option>
        <option value="ENABLED">ENABLED</option>
        <option value="DISABLED">DISABLED</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>名称</th>
              <th>来源</th>
              <th>状态</th>
              <th>使用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无模板' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.templateNo }}</td>
              <td style="font-weight: 500">{{ row.templateName }}</td>
              <td>{{ row.source }}</td>
              <td>{{ row.status }}</td>
              <td class="num">{{ row.usageCount }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" @click="openPreview(row)">预览</button>
                <button
                  v-if="row.source !== 'PRESET'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="openEdit(row)"
                >
                  编辑
                </button>
                <button
                  v-if="row.status === 'DRAFT'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="publish(row.id)"
                >
                  发布
                </button>
                <button
                  v-if="row.status === 'ENABLED'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="setEnabled(row.id, false)"
                >
                  停用
                </button>
                <button
                  v-if="row.status === 'DISABLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="setEnabled(row.id, true)"
                >
                  重新启用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showPreview" class="modal-mask" @click.self="showPreview = false">
      <div class="card" style="width: 520px; padding: 20px">
        <h3 style="margin: 0 0 12px">预览 · {{ previewTitle }}</h3>
        <iframe
          v-if="previewHtml"
          sandbox=""
          :srcdoc="previewHtml"
          title="模板预览"
          style="width: 100%; height: 220px; border: 1px solid var(--line, #ddd); background: #fff"
        />
        <p v-else class="hint">暂无预览</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showPreview = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">编辑公推模板</h3>
        <label class="fld">模板名称</label>
        <input v-model="editForm.templateName" class="fld-in" />
        <label class="fld">预览 HTML</label>
        <textarea v-model="editForm.previewHtml" class="fld-in" rows="4" />
        <p v-if="editError" class="hint" style="color: var(--red)">{{ editError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showEdit = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitEdit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建公推模板</h3>
        <label class="fld">模板名称</label>
        <input v-model="form.templateName" class="fld-in" />
        <label class="fld">预览 HTML（可选）</label>
        <textarea v-model="form.previewHtml" class="fld-in" rows="3" />
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
  templateNo: string
  templateName: string
  source: string
  status: string
  usageCount: number
  previewHtml?: string
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const showEdit = ref(false)
const showPreview = ref(false)
const formError = ref('')
const editError = ref('')
const previewTitle = ref('')
const previewHtml = ref('')
const editingId = ref<number | null>(null)
const filters = reactive({ templateName: '', status: '' })
const form = reactive({ templateName: '', previewHtml: '' })
const editForm = reactive({ templateName: '', previewHtml: '' })

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/content/layout-template/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        templateName: filters.templateName || undefined,
        status: filters.status || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.templateName = ''
  form.previewHtml = ''
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  try {
    const res = await http.post('/content/layout-template', {
      templateName: form.templateName,
      previewHtml: form.previewHtml,
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    showForm.value = false
    await loadList()
  } catch {
    formError.value = '网络错误'
  }
}

function openPreview(row: Row) {
  previewTitle.value = row.templateName
  previewHtml.value = row.previewHtml || ''
  showPreview.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  editForm.templateName = row.templateName
  editForm.previewHtml = row.previewHtml || ''
  editError.value = ''
  showEdit.value = true
}

async function submitEdit() {
  if (editingId.value == null) return
  editError.value = ''
  try {
    const res = await http.put(`/content/layout-template/${editingId.value}`, {
      templateName: editForm.templateName,
      previewHtml: editForm.previewHtml,
    })
    if (res.data.code !== 0) {
      editError.value = res.data.msg || '保存失败'
      return
    }
    showEdit.value = false
    await loadList()
  } catch {
    editError.value = '网络错误'
  }
}

async function publish(id: number) {
  await http.post(`/content/layout-template/${id}/publish`)
  await loadList()
}

async function setEnabled(id: number, enabled: boolean) {
  await http.put(`/content/layout-template/${id}/enable`, null, { params: { enabled } })
  await loadList()
}

onMounted(loadList)
</script>
