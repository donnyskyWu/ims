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
      <select v-model="typeKw" data-testid="filter-content-type" style="width: 140px">
        <option value="">全部类型</option>
        <option value="SHORT_VIDEO">短视频</option>
        <option value="ARTICLE">图文</option>
      </select>
      <select v-model="platformKw" data-testid="filter-platform" style="width: 120px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="WECHAT_CHANNELS">视频号</option>
      </select>
      <select v-model="docKw" data-testid="filter-document-type" style="width: 120px">
        <option value="">全部文档</option>
        <option value="COPY">文案</option>
        <option value="SCRIPT">脚本</option>
      </select>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>状态</th>
              <th>类型</th>
              <th>平台</th>
              <th>赛事摘要</th>
              <th>文档类型</th>
              <th>AI 文案</th>
              <th>视频</th>
              <th>Football 同步</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="11"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="11"><div class="empty"><div class="et">{{ error || '暂无内容' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td><b>{{ row.title }}</b></td>
              <td>{{ row.contentStatus }}</td>
              <td data-testid="row-content-type">{{ typeLabel(row.contentType) }}</td>
              <td data-testid="row-platform">{{ platformLabel(row.platformType) }}</td>
              <td>{{ row.matchSummary || row.competitionName || '—' }}</td>
              <td>{{ row.documentType || '—' }}</td>
              <td data-testid="row-ai-status">{{ copyLabel(row.aiGenerateStatus) }}</td>
              <td data-testid="row-video-status">{{ videoLabel(row.videoJobStatus) }}</td>
              <td>{{ row.fbSyncStatusLabel || row.fbSyncStatus || '—' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="content-view" @click="openView(row)">查看</button>
                <button class="btn btn-sec btn-sm" type="button" style="margin-left: 6px" @click="openEdit(row)">编辑</button>
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

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑内容' : '新增内容'" width="880px" @close="drawerOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="editTitle" />
        </div>
        <div class="fld">
          <label>内容类型</label>
          <select v-model="editContentType">
            <option value="SHORT_VIDEO">短视频</option>
            <option value="ARTICLE">图文</option>
          </select>
        </div>
        <div class="fld">
          <label>平台</label>
          <select v-model="editPlatform" data-testid="edit-platform">
            <option value="">未指定</option>
            <option value="DOUYIN">抖音</option>
            <option value="KUAISHOU">快手</option>
            <option value="WECHAT_CHANNELS">视频号</option>
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
          <div class="rowline" style="justify-content: space-between; margin-bottom: 6px">
            <label style="margin: 0">正文</label>
            <button class="btn btn-sec btn-sm" type="button" @click="aiOpen = true">AI 文案</button>
          </div>
          <textarea v-model="editBody" rows="4" placeholder="正文" />
        </div>
        <div class="fld">
          <label>版式图片</label>
          <p class="hint">POST /content/file/upload · scene=content_image，写入 layout_html</p>
          <input
            data-testid="content-image-file"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            :disabled="uploading"
            @change="onPickImage"
          />
          <p v-if="uploadError" class="hint" style="color: var(--red)">{{ uploadError }}</p>
        </div>
        <div class="fld">
          <label>layout_html</label>
          <textarea v-model="editLayoutHtml" data-testid="content-layout-html" rows="4" readonly />
        </div>
        <div class="fld">
          <label>版式预览</label>
          <div data-testid="content-layout-preview" class="content-layout-preview">
            <figure v-for="img in previewImages" :key="img.fileKey">
              <img :src="img.objectUrl" :alt="img.alt" />
              <figcaption>{{ img.alt }}</figcaption>
            </figure>
            <div v-if="!previewImages.length" class="hint">{{ previewHint }}</div>
          </div>
        </div>
        <div class="fld">
          <label>版式 HTML</label>
          <textarea
            v-model="editLayoutHtml"
            rows="4"
            data-testid="content-layout-html-input"
            placeholder="查看与审核按此 HTML 只读渲染；留空则显示正文"
          />
        </div>
        <ContentLayoutPanel
          :content-id="editingId"
          :body="editBody"
          :body-format="editBodyFormat"
          :layout-html="editLayoutHtml"
          @applied="onLayoutApplied"
        />
        <div v-if="editContentType === 'ARTICLE'" class="fld">
          <label>排版</label>
          <p class="hint">AI 语义排版只生成版式，不改写纯文本，也不调用文案生成。</p>
          <button class="btn btn-sec btn-sm" type="button" :disabled="!canAiLayout" @click="openAiLayout">
            AI 语义排版
          </button>
          <div v-if="aiPanelOpen" class="ai-layout-panel">
            <p class="hint">按正文语义自动选择决策扫读版或情报分析版。</p>
            <button class="btn btn-pri btn-sm" type="button" :disabled="aiBusy || !canAiLayout" @click="previewAi">
              AI 排版预览
            </button>
            <template v-if="aiPreview">
              <pre v-if="aiTab === 'before'" class="layout-viewer">{{ editBody }}</pre>
              <div v-else class="layout-viewer" v-html="aiPreview.layoutHtml"></div>
              <p class="hint">已选版式：{{ aiPreview.selectedTemplateName }}</p>
              <button class="btn btn-pri btn-sm" type="button" :disabled="aiBusy" @click="applyAi">写回版式</button>
            </template>
            <p v-if="aiNote" class="hint">{{ aiNote }}</p>
          </div>
        </div>
      </div>
      <p v-if="!editingId" class="hint">保存草稿后可 AI 生成文案与视频。</p>
      <ContentAiPanel v-else-if="editingRow" :content="editingRow" @refresh="reloadEditing" />
      <AiCopyDrawer :open="aiOpen" :content-id="editingId" @close="aiOpen = false" @adopt="adoptAi" />
      <template #footer>
        <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="saveContent">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="viewOpen" title="查看内容" width="720px" @close="viewOpen = false">
      <p><b data-testid="content-view-title">{{ viewRow?.title }}</b></p>
      <p class="hint">
        状态 {{ viewRow?.contentStatus || '—' }} · 文档类型 {{ viewRow?.documentType || '—' }} · 内容类型
        {{ viewRow?.contentType || '—' }}
      </p>
      <p v-if="viewRow?.matchSummary" class="hint">赛事摘要 {{ viewRow.matchSummary }}</p>
      <div class="dsec">正文</div>
      <ContentLayoutPreview :layout-html="viewRow?.layoutHtml || ''" :body="viewRow?.body || ''" />
      <template #footer>
        <button class="btn btn-sec" type="button" @click="viewOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ContentLayoutPanel from '../../components/ContentLayoutPanel.vue'
import ContentLayoutPreview from '../../components/ContentLayoutPreview.vue'
import AiCopyDrawer from '../../components/AiCopyDrawer.vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import ContentAiPanel from './ContentAiPanel.vue'
import MatchSchemeEditor, { type MatchSchemeItem } from './MatchSchemeEditor.vue'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const titleKw = ref('')
const statusKw = ref('')
const typeKw = ref('')
const platformKw = ref('')
const docKw = ref('')
const drawerOpen = ref(false)
const viewOpen = ref(false)
const viewRow = ref<any>(null)
const aiOpen = ref(false)
const aiPanelOpen = ref(false)
const aiBusy = ref(false)
const aiPreview = ref<any>(null)
const aiNote = ref('')
const aiTab = ref<'before' | 'after'>('after')
const canAiLayout = computed(() => editContentType.value === 'ARTICLE' && editBody.value.trim().length > 0)
const saving = ref(false)
const editingId = ref<number | null>(null)
const editingRow = ref<any>(null)
const editorSeed = ref(0)
const editTitle = ref('')
const editContentType = ref('SHORT_VIDEO')
const editPlatform = ref('')
const editDocType = ref('COPY')
const editMatchType = ref(1)
const editScheme = ref<MatchSchemeItem[]>([])
const editBody = ref('')
const editLayoutHtml = ref('')
const editLayoutJson = ref('')
const editBodyFormat = ref('PLAIN')
const editLayoutTemplateId = ref<number | null>(null)
const uploading = ref(false)
const uploadError = ref('')
const previewHint = ref('插入图片后在此预览')
const previewImages = ref<{ fileKey: string; objectUrl: string; alt: string }[]>([])
let previewToken = 0

const copyLabels: Record<string, string> = { QUEUED: '生成中', GENERATING: '生成中', SUCCESS: '成功', FAILED: '失败' }
const videoLabels: Record<string, string> = {
  WAITING: '待生成',
  GENERATING: '生成中',
  PENDING_FINAL_REVIEW: '待终审',
  REVIEW_PASSED: '终审通过',
  REVIEW_REJECTED: '终审打回',
  FAILED: '失败',
}
function copyLabel(status: string | null | undefined) {
  if (!status) return '未生成'
  if (status === 'GENERATED') return '已生成'
  return copyLabels[status] || status
}
function videoLabel(status: string | null | undefined) {
  if (!status) return '未生成'
  return videoLabels[status] || status
}
const typeLabels: Record<string, string> = { SHORT_VIDEO: '短视频', ARTICLE: '图文' }
const platformLabels: Record<string, string> = { DOUYIN: '抖音', KUAISHOU: '快手', WECHAT_CHANNELS: '视频号' }
function typeLabel(value: string | null | undefined) {
  if (!value) return '—'
  return typeLabels[value] || value
}
function platformLabel(value: string | null | undefined) {
  if (!value) return '—'
  return platformLabels[value] || value
}

function escapeAttr(value: string) {
  return value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function parseLayoutImages(html: string) {
  const found: { fileKey: string; src: string; alt: string }[] = []
  const tags = html.match(/<img\b[^>]*>/gi) || []
  for (const tag of tags) {
    const src = /src="([^"]*)"/.exec(tag)?.[1] || ''
    const fileKey = /data-file-key="([^"]*)"/.exec(tag)?.[1] || ''
    const alt = /alt="([^"]*)"/.exec(tag)?.[1] || ''
    if (fileKey && src.startsWith('/admin-api/ims/file/')) found.push({ fileKey, src, alt })
  }
  return found
}

function revokePreviews() {
  for (const img of previewImages.value) {
    if (img.objectUrl.startsWith('blob:')) URL.revokeObjectURL(img.objectUrl)
  }
  previewImages.value = []
}

async function refreshPreview() {
  const token = ++previewToken
  const parsed = parseLayoutImages(editLayoutHtml.value)
  if (!parsed.length) {
    revokePreviews()
    previewHint.value = '插入图片后在此预览'
    return
  }
  previewHint.value = '预览加载中'
  const next: { fileKey: string; objectUrl: string; alt: string }[] = []
  for (const item of parsed) {
    const path = item.src.startsWith('/admin-api/ims') ? item.src.slice('/admin-api/ims'.length) : item.src
    try {
      const res = await http.get(path, { responseType: 'blob' })
      next.push({ fileKey: item.fileKey, objectUrl: URL.createObjectURL(res.data as Blob), alt: item.alt || item.fileKey })
    } catch {
      /* 单张失败时保留其余预览 */
    }
  }
  if (token !== previewToken) {
    for (const img of next) URL.revokeObjectURL(img.objectUrl)
    return
  }
  revokePreviews()
  previewImages.value = next
  previewHint.value = next.length ? '' : '图片预览失败'
}

async function onPickImage(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    body.append('scene', 'content_image')
    const { data } = await http.post('/content/file/upload', body)
    const fileKey = String(data.data?.fileKey || '')
    const fileUrl = String(data.data?.fileUrl || '')
    const fileName = String(data.data?.fileName || file.name)
    if (!fileKey || !fileUrl) {
      uploadError.value = '上传回执缺少 fileKey'
      return
    }
    const tag = `<img src="${escapeAttr(fileUrl)}" alt="${escapeAttr(fileName)}" data-file-key="${escapeAttr(fileKey)}" />`
    editLayoutHtml.value = editLayoutHtml.value ? `${editLayoutHtml.value}\n${tag}` : tag
    await refreshPreview()
  } catch (e) {
    uploadError.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (titleKw.value.trim()) params.title = titleKw.value.trim()
    if (statusKw.value.trim()) params.status = statusKw.value.trim()
    if (typeKw.value) params.contentType = typeKw.value
    if (platformKw.value) params.platformType = platformKw.value
    if (docKw.value) params.documentType = docKw.value
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

function resetFilters() {
  titleKw.value = ''
  statusKw.value = ''
  typeKw.value = ''
  platformKw.value = ''
  docKw.value = ''
  loadList()
}

function resetForm() {
  editTitle.value = ''
  editContentType.value = 'SHORT_VIDEO'
  editPlatform.value = ''
  editDocType.value = 'COPY'
  editMatchType.value = 1
  editScheme.value = []
  editBody.value = ''
  editLayoutHtml.value = ''
  editLayoutJson.value = ''
  editBodyFormat.value = 'PLAIN'
  editLayoutTemplateId.value = null
}

function openCreate() {
  editingId.value = null
  editingRow.value = null
  resetForm()
  editorSeed.value += 1
  uploadError.value = ''
  revokePreviews()
  previewHint.value = '插入图片后在此预览'
  aiOpen.value = false
  aiPanelOpen.value = false
  aiPreview.value = null
  aiNote.value = ''
  drawerOpen.value = true
}

function adoptAi(payload: { markdown: string }) {
  editBody.value = payload.markdown
  aiOpen.value = false
}

function openEdit(row: any) {
  editingId.value = row.id
  editingRow.value = row
  editTitle.value = row.title || ''
  editContentType.value = row.contentType || 'SHORT_VIDEO'
  editPlatform.value = row.platformType || ''
  editDocType.value = row.documentType || 'COPY'
  editMatchType.value = row.matchType || 1
  editScheme.value = Array.isArray(row.matchScheme) ? row.matchScheme : []
  editBody.value = row.body || ''
  editLayoutHtml.value = row.layoutHtml || ''
  editLayoutJson.value = typeof row.layoutJson === 'string' ? row.layoutJson : JSON.stringify(row.layoutJson || '')
  editBodyFormat.value = row.bodyFormat || 'PLAIN'
  editLayoutTemplateId.value = row.layoutTemplateId ?? null
  editorSeed.value += 1
  uploadError.value = ''
  aiOpen.value = false
  aiPanelOpen.value = false
  aiPreview.value = null
  aiNote.value = ''
  drawerOpen.value = true
  void refreshPreview()
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
      body: editBody.value,
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
  const hasLayout = editBodyFormat.value === 'LAYOUT' || !!editLayoutHtml.value.trim()
  if (hasLayout && !window.confirm('将覆盖当前版式，正文文字不会改动')) return
  aiBusy.value = true
  try {
    const { data } = await http.post(`/content/${editingId.value}/typeset/apply`, {
      mode: 'AUTO',
      body: editBody.value,
      overwrite: hasLayout,
    })
    editLayoutHtml.value = data.data?.layoutHtml || ''
    editBodyFormat.value = data.data?.bodyFormat || 'LAYOUT'
    editLayoutJson.value = typeof data.data?.layoutJson === 'string' ? data.data.layoutJson : JSON.stringify(data.data?.layoutJson || '')
    if (typeof data.data?.body === 'string') editBody.value = data.data.body
    aiNote.value = 'AI 排版已写回，正文未改动'
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    aiBusy.value = false
  }
}

async function openView(row: any) {
  viewRow.value = row
  viewOpen.value = true
  try {
    const { data } = await http.get(`/content/${row.id}`)
    viewRow.value = data.data
  } catch {
    viewRow.value = row
  }
}

function onLayoutApplied(payload: {
  layoutHtml: string
  layoutJson: string
  bodyFormat: string
  layoutTemplateId: number | null
  body: string
}) {
  editLayoutHtml.value = payload.layoutHtml
  editLayoutJson.value = payload.layoutJson
  editBodyFormat.value = payload.bodyFormat
  editLayoutTemplateId.value = payload.layoutTemplateId
  editBody.value = payload.body
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
      platformType: editPlatform.value,
      documentType: editDocType.value,
      matchType: editMatchType.value,
      matchScheme: editScheme.value,
      body: editBody.value,
      layoutHtml: editLayoutHtml.value,
      layoutJson: editLayoutJson.value,
      bodyFormat: editBodyFormat.value,
      layoutTemplateId: editLayoutTemplateId.value,
    }
    if (editingId.value) {
      await http.put(`/content/${editingId.value}`, payload)
    } else {
      await http.post('/content', payload)
    }
    drawerOpen.value = false
    editingRow.value = null
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function reloadEditing() {
  if (!editingId.value) return
  try {
    const { data } = await http.get(`/content/${editingId.value}`)
    editingRow.value = data.data
    editBody.value = data.data?.body || ''
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
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

<style scoped>
.content-layout-preview {
  min-height: 88px;
  border: 1px dashed var(--line2);
  border-radius: 8px;
  padding: 8px;
  background: #fafafc;
}
.content-layout-preview figure {
  margin: 0 0 8px;
}
.content-layout-preview img {
  width: 96px;
  height: 96px;
  object-fit: contain;
  background: #fff;
  border: 1px solid var(--line);
}
.content-layout-preview figcaption {
  font-size: 12px;
  color: var(--text2);
}
</style>
