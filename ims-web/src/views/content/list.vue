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

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑内容' : '新增内容'" width="720px" @close="drawerOpen = false">
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
        <div v-if="showLayoutPanel" class="fld">
          <label>排版</label>
          <p class="hint">AI 语义排版只生成版式，不改写纯文本，也不调用文案生成。</p>
          <button
            class="btn btn-sec btn-sm"
            type="button"
            :disabled="!canAiLayout"
            :title="aiLayoutTip"
            @click="openAiLayout"
          >
            AI 语义排版
          </button>
          <div v-if="aiPanelOpen" class="ai-layout-panel">
            <p class="hint">按正文语义自动选择决策扫读版或情报分析版。</p>
            <button class="btn btn-pri btn-sm" type="button" :disabled="aiBusy || !canAiLayout" @click="previewAi">
              AI 排版预览
            </button>
            <template v-if="aiPreview">
              <div class="tabs" style="margin-top: 10px">
                <div class="tab" :class="{ on: aiTab === 'before' }" @click="aiTab = 'before'">排版前</div>
                <div class="tab" :class="{ on: aiTab === 'after' }" @click="aiTab = 'after'">排版后</div>
              </div>
              <pre v-if="aiTab === 'before'" class="layout-viewer">{{ form.body }}</pre>
              <div v-else class="layout-viewer" v-html="aiPreview.layoutHtml"></div>
              <p class="hint">已选版式：{{ aiPreview.selectedTemplateName }}</p>
              <p v-if="segmentSummary" class="hint">分段：{{ segmentSummary }}</p>
              <button class="btn btn-pri btn-sm" type="button" :disabled="aiBusy" @click="applyAi">写回版式</button>
            </template>
            <p v-if="aiNote" class="hint">{{ aiNote }}</p>
          </div>
          <div v-if="savedLayoutHtml" class="layout-viewer" style="margin-top: 8px" v-html="savedLayoutHtml"></div>
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
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const titleKw = ref('')
const statusKw = ref('')
const drawerOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  title: '',
  contentType: 'SHORT_VIDEO',
  matchType: 1,
  matchSchemeJson: '[]',
  body: '',
})
const aiPanelOpen = ref(false)
const aiBusy = ref(false)
const aiPreview = ref<any>(null)
const aiTab = ref<'before' | 'after'>('after')
const aiNote = ref('')
const savedLayoutHtml = ref('')
const savedBodyFormat = ref('PLAIN')

const showLayoutPanel = computed(() => (form.value.contentType || '').trim().toUpperCase() === 'ARTICLE')
const aiLayoutTip = computed(() => {
  if (!editingId.value) return '请先保存内容'
  if (!showLayoutPanel.value) return '仅文章类型可语义排版'
  if (!form.value.body.trim()) return '请先输入正文'
  return ''
})
const canAiLayout = computed(() => aiLayoutTip.value === '')
const segmentSummary = computed(() => {
  const counts = aiPreview.value?.segmentationReport?.segmentTypeCounts || {}
  const labels: Record<string, string> = {
    ARTICLE_TITLE: '标题',
    ANALYSIS_PARAGRAPH: '分析',
    PLAIN_PARAGRAPH: '段落',
    TEAM_VS: '对阵',
    SUBHEADING: '小标题',
    DISCLAIMER: '声明',
  }
  return Object.entries(counts)
    .map(([key, count]) => `${labels[key] || key}×${count}`)
    .join(' · ')
})

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

function resetLayoutState() {
  aiPanelOpen.value = false
  aiPreview.value = null
  aiNote.value = ''
  aiTab.value = 'after'
  savedLayoutHtml.value = ''
  savedBodyFormat.value = 'PLAIN'
}

function openCreate() {
  editingId.value = null
  form.value = { title: '', contentType: 'SHORT_VIDEO', matchType: 1, matchSchemeJson: '[]', body: '' }
  resetLayoutState()
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
  }
  resetLayoutState()
  savedLayoutHtml.value = row.layoutHtml || ''
  savedBodyFormat.value = row.bodyFormat || 'PLAIN'
  drawerOpen.value = true
}

function openAiLayout() {
  if (!canAiLayout.value) return
  aiPanelOpen.value = true
  aiPreview.value = null
  aiNote.value = ''
}

async function previewAi() {
  if (!editingId.value) return
  aiBusy.value = true
  aiNote.value = ''
  try {
    const { data } = await http.post(`/content/${editingId.value}/typeset/preview`, {
      mode: 'AUTO',
      body: form.value.body,
    })
    aiPreview.value = data.data
    aiTab.value = 'after'
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    aiBusy.value = false
  }
}

async function applyAi() {
  if (!editingId.value) return
  const hasLayout = savedBodyFormat.value === 'LAYOUT' || !!savedLayoutHtml.value
  if (hasLayout && !window.confirm('将覆盖当前版式，正文文字不会改动')) return
  aiBusy.value = true
  try {
    const { data } = await http.post(`/content/${editingId.value}/typeset/apply`, {
      mode: 'AUTO',
      body: form.value.body,
      overwrite: hasLayout,
    })
    savedLayoutHtml.value = data.data?.layoutHtml || ''
    savedBodyFormat.value = data.data?.bodyFormat || 'LAYOUT'
    if (typeof data.data?.body === 'string') form.value.body = data.data.body
    aiNote.value = 'AI 排版已写回，正文未改动'
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    aiBusy.value = false
  }
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
