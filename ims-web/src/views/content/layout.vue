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
                <button
                  v-if="row.status === 'DRAFT'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="publish(row.id)"
                >
                  发布
                </button>
                <button
                  v-if="row.status === 'ENABLED'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  @click="setEnabled(row.id, false)"
                >
                  停用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ templateName: '', status: '' })
const form = reactive({ templateName: '', previewHtml: '' })

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
