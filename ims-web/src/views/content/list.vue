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
      契约 GET/POST/PUT <code>/admin-api/ims/content</code> · Football
      <code>GET|POST …/{id}/fb-sync</code>（CONTENT-109）。保存成功即 200，HTTP 失败进
      <router-link to="/ims/content/fb-sync">补偿队列</router-link> · 审核通过后
      <router-link to="/ims/content/publish">发布管理</router-link>（回填/督办）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="titleKw" placeholder="标题" style="width: 160px" />
      <input v-model="statusKw" placeholder="状态" style="width: 120px" />
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

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑内容' : '新增内容'" width="880px" @close="drawerOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="form.title" />
        </div>
        <div class="fld">
          <label>内容类型</label>
          <input v-model="form.contentType" placeholder="SHORT_VIDEO" />
        </div>
        <div class="fld">
          <label>matchType</label>
          <input v-model.number="form.matchType" type="number" />
        </div>
        <div class="fld">
          <label>matchScheme JSON</label>
          <textarea v-model="form.matchSchemeJson" rows="5" />
        </div>
        <div class="fld">
          <label>正文</label>
          <textarea v-model="form.body" rows="4" />
        </div>
        <ContentLayoutPanel
          :content-id="editingId"
          :body="form.body"
          :body-format="form.bodyFormat"
          :layout-html="form.layoutHtml"
          @applied="onLayoutApplied"
        />
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
import ContentLayoutPanel from '../../components/ContentLayoutPanel.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const titleKw = ref('')
const statusKw = ref('')
const drawerOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const emptyForm = () => ({
  title: '',
  contentType: 'SHORT_VIDEO',
  matchType: 1,
  matchSchemeJson: '[]',
  body: '',
  layoutHtml: '',
  layoutJson: '',
  bodyFormat: 'PLAIN',
  layoutTemplateId: null as number | null,
})
const form = ref(emptyForm())

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

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  drawerOpen.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  form.value = {
    title: row.title,
    contentType: row.contentType || 'SHORT_VIDEO',
    matchType: row.matchType || 1,
    matchSchemeJson: JSON.stringify(row.matchScheme || [], null, 2),
    body: row.body || '',
    layoutHtml: row.layoutHtml || '',
    layoutJson: typeof row.layoutJson === 'string' ? row.layoutJson : JSON.stringify(row.layoutJson || ''),
    bodyFormat: row.bodyFormat || 'PLAIN',
    layoutTemplateId: row.layoutTemplateId ?? null,
  }
  drawerOpen.value = true
}

function onLayoutApplied(payload: {
  layoutHtml: string
  layoutJson: string
  bodyFormat: string
  layoutTemplateId: number | null
  body: string
}) {
  form.value.layoutHtml = payload.layoutHtml
  form.value.layoutJson = payload.layoutJson
  form.value.bodyFormat = payload.bodyFormat
  form.value.layoutTemplateId = payload.layoutTemplateId
  form.value.body = payload.body
}

async function saveContent() {
  if (!form.value.title.trim()) {
    window.alert('请填写标题')
    return
  }
  let scheme: unknown[] = []
  try {
    scheme = JSON.parse(form.value.matchSchemeJson || '[]')
  } catch {
    window.alert('matchScheme JSON 无效')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.value.title,
      contentType: form.value.contentType,
      matchType: form.value.matchType,
      matchScheme: scheme,
      body: form.value.body,
      layoutHtml: form.value.layoutHtml,
      layoutJson: form.value.layoutJson,
      bodyFormat: form.value.bodyFormat,
      layoutTemplateId: form.value.layoutTemplateId,
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
