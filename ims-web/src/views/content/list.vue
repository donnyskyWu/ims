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

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑内容' : '新增内容'" width="780px" @close="drawerOpen = false">
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
          <textarea v-model="form.layoutHtml" data-testid="content-layout-html" rows="4" readonly />
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

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const titleKw = ref('')
const statusKw = ref('')
const drawerOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const uploading = ref(false)
const uploadError = ref('')
const previewHint = ref('插入图片后在此预览')
const previewImages = ref<{ fileKey: string; objectUrl: string; alt: string }[]>([])
let previewToken = 0

const emptyForm = () => ({
  title: '',
  contentType: 'SHORT_VIDEO',
  matchType: 1,
  matchSchemeJson: '[]',
  body: '',
  layoutHtml: '',
})
const form = ref(emptyForm())

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
  const parsed = parseLayoutImages(form.value.layoutHtml)
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
    form.value.layoutHtml = form.value.layoutHtml ? `${form.value.layoutHtml}\n${tag}` : tag
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
  uploadError.value = ''
  revokePreviews()
  form.value = emptyForm()
  previewHint.value = '插入图片后在此预览'
  drawerOpen.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  uploadError.value = ''
  form.value = {
    title: row.title,
    contentType: row.contentType || 'SHORT_VIDEO',
    matchType: row.matchType || 1,
    matchSchemeJson: JSON.stringify(row.matchScheme || [], null, 2),
    body: row.body || '',
    layoutHtml: row.layoutHtml || '',
  }
  drawerOpen.value = true
  void refreshPreview()
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
