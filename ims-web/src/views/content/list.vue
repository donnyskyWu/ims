<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>内容管理</h1>
        <div class="sub">内容 CRUD · 玩法 matchScheme（CONTENT-106）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新增内容</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      契约 GET/POST/PUT/DELETE <code>/admin-api/ims/content</code> · Football
      <code>GET|POST …/{id}/fb-sync</code>（CONTENT-109）。保存成功即 200，HTTP 失败进
      <router-link to="/ims/content/fb-sync">补偿队列</router-link> · 审核通过后
      <router-link to="/ims/content/publish">发布管理</router-link>（回填/督办）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="titleKw" placeholder="标题" style="width: 160px" />
      <select v-model="statusKw" style="width: 160px">
        <option value="">全部状态</option>
        <option value="DRAFT">DRAFT</option>
        <option value="REJECTED">REJECTED</option>
        <option value="PENDING_REVIEW">PENDING_REVIEW</option>
        <option value="PENDING_PUBLISH">PENDING_PUBLISH</option>
        <option value="PUBLISHED">PUBLISHED</option>
      </select>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>状态</th>
              <th>赛事摘要</th>
              <th>文档类型</th>
              <th>Football 同步</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无内容' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td><b>{{ row.title }}</b></td>
              <td>{{ row.contentStatus }}</td>
              <td>{{ row.matchSummary || row.competitionName || '—' }}</td>
              <td>{{ row.documentType || '—' }}</td>
              <td>{{ row.fbSyncStatusLabel || row.fbSyncStatus || '—' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button
                  v-if="row.contentStatus === 'DRAFT' || row.contentStatus === 'REJECTED'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="removeContent(row)"
                >
                  删除
                </button>
                <button
                  v-if="row.fbSyncStatus === 'COMPENSATING' || row.fbSyncStatus === 'FAILED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="retrySync(row.id)"
                >
                  重同步
                </button>
                <button
                  v-if="row.contentStatus === 'DRAFT' || row.contentStatus === 'REJECTED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="submitReview(row.id)"
                >
                  提审
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑内容' : '新增内容'" width="720px" @close="drawerOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="editTitle" />
        </div>
        <div class="fld">
          <label>内容类型</label>
          <select v-model="editContentType">
            <option value="SHORT_VIDEO">SHORT_VIDEO</option>
            <option value="ARTICLE">ARTICLE</option>
          </select>
        </div>
        <div class="fld">
          <label>文档类型</label>
          <select v-model="editDocType">
            <option value="COPY">COPY</option>
            <option value="SCRIPT">SCRIPT</option>
          </select>
        </div>
        <MatchSchemeEditor v-model:match-type="editMatchType" v-model:scheme="editScheme" :seed-key="editorSeed" />
        <div class="fld">
          <label>正文</label>
          <textarea v-model="editBody" rows="4" placeholder="正文" />
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="saveContent">保存</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import MatchSchemeEditor, { type MatchSchemeItem } from './MatchSchemeEditor.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const titleKw = ref('')
const statusKw = ref('')
const drawerOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const editorSeed = ref(0)
const editTitle = ref('')
const editContentType = ref('SHORT_VIDEO')
const editDocType = ref('COPY')
const editMatchType = ref(1)
const editScheme = ref<MatchSchemeItem[]>([])
const editBody = ref('')

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (titleKw.value.trim()) params.title = titleKw.value.trim()
    if (statusKw.value.trim()) params.status = statusKw.value.trim()
    const { data } = await http.get('/content', { params })
    rows.value = data.data?.list || []
    total.value = data.data?.total || 0
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editTitle.value = ''
  editContentType.value = 'SHORT_VIDEO'
  editDocType.value = 'COPY'
  editMatchType.value = 1
  editScheme.value = []
  editBody.value = ''
}

function openCreate() {
  editingId.value = null
  resetForm()
  editorSeed.value += 1
  drawerOpen.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  editTitle.value = row.title || ''
  editContentType.value = row.contentType || 'SHORT_VIDEO'
  editDocType.value = row.documentType || 'COPY'
  editMatchType.value = row.matchType || 1
  editScheme.value = Array.isArray(row.matchScheme) ? row.matchScheme : []
  editBody.value = row.body || ''
  editorSeed.value += 1
  drawerOpen.value = true
}

async function saveContent() {
  if (!editTitle.value.trim()) {
    window.alert('请填写标题')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: editTitle.value.trim(),
      contentType: editContentType.value,
      documentType: editDocType.value,
      matchType: editMatchType.value,
      matchScheme: editScheme.value,
      body: editBody.value,
    }
    if (editingId.value) {
      await http.put(`/content/${editingId.value}`, payload)
    } else {
      await http.post('/content', payload)
    }
    drawerOpen.value = false
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function removeContent(row: any) {
  if (!window.confirm(`确认删除「${row.title}」？`)) return
  try {
    await http.delete(`/content/${row.id}`)
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function submitReview(id: number) {
  try {
    await http.post(`/content/${id}/submit-review`)
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function retrySync(id: number) {
  try {
    await http.post(`/content/${id}/fb-sync`)
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

loadList()
</script>
