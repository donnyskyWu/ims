<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>公推模板库</h1>
        <div class="sub">CONTENT-107 · /content/layout-template · 15 CONTENT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="layout-import-open" @click="openImport">导入向导</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建模板</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/content/list">内容管理</router-link>
      </div>
    </div>
    <form class="qbar" data-testid="layout-filters" @submit.prevent="loadList">
      <input v-model="filters.templateName" data-testid="layout-filter-name" placeholder="模板名称" style="width: 140px" />
      <select v-model="filters.status" data-testid="layout-filter-status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="DRAFT">DRAFT</option>
        <option value="ENABLED">ENABLED</option>
        <option value="DISABLED">DISABLED</option>
      </select>
      <select v-model="filters.source" data-testid="layout-filter-source" style="width: 110px">
        <option value="">全部来源</option>
        <option value="CUSTOM">CUSTOM</option>
        <option value="IMPORT">IMPORT</option>
        <option value="PRESET">PRESET</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="layout-filter-reset" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="layout-template-table">
          <thead>
            <tr>
              <th>模板名称</th>
              <th>预览</th>
              <th>文档类型</th>
              <th>来源</th>
              <th>状态</th>
              <th>创建人</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8">
                <div class="empty" data-testid="layout-list-empty">
                  <div class="et">{{ error || layoutEmptyTitle }}</div>
                  <div v-if="!error" class="es">{{ layoutEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td style="font-weight: 500" data-testid="layout-name">{{ row.templateName }}</td>
              <td class="hint" data-testid="layout-preview-cell">{{ previewText(row.previewHtml) }}</td>
              <td>{{ docLabel(row.documentType) }}</td>
              <td>{{ row.source }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.creatorName || '—' }}</td>
              <td class="mono">{{ formatTime(row.updatedAt) }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" @click="openPreview(row)">预览</button>
                <button
                  v-if="row.source === 'PRESET'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  data-testid="layout-view"
                  @click="openView(row)"
                >
                  查看
                </button>
                <button
                  v-if="row.source === 'PRESET'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  data-testid="layout-copy"
                  @click="copyTemplate(row)"
                >
                  复制
                </button>
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
                  v-if="row.status === 'DRAFT' && row.source !== 'PRESET'"
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
                <button
                  v-if="row.source !== 'PRESET' && row.status === 'DRAFT'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  data-testid="layout-delete"
                  @click="removeTemplate(row)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="tbl-block" data-testid="layout-import-jobs" style="margin-top: 16px">
      <h2 style="margin: 0 0 8px; font-size: 14px">导入任务</h2>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>任务号</th>
              <th>方式</th>
              <th>模板</th>
              <th>状态</th>
              <th>说明</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!jobs.length">
              <td colspan="6"><div class="empty"><div class="et">暂无导入任务</div></div></td>
            </tr>
            <tr v-for="job in jobs" v-else :key="job.jobId">
              <td class="mono">{{ job.jobId }}</td>
              <td>{{ channelLabel(job.channel) }}</td>
              <td>{{ job.templateName || '—' }}</td>
              <td>{{ job.status === 'SUCCESS' ? '成功' : job.status === 'FAILED' ? '失败' : job.status }}</td>
              <td>{{ job.message || '—' }}</td>
              <td class="mono">{{ formatTime(job.createdAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="toast" class="layout-toast" data-testid="layout-toast">{{ toast }}</p>

    <div v-if="pendingDelete" class="modal-mask" data-testid="layout-delete-confirm" @click.self="pendingDelete = null">
      <div class="card" style="width: 380px; padding: 20px">
        <h3 style="margin: 0 0 8px">删除模板</h3>
        <p>删除草稿模板「{{ pendingDelete.templateName }}」？</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="pendingDelete = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="layout-delete-ok" @click="confirmDelete">确定</button>
        </div>
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
        <div v-else class="empty" data-testid="layout-preview-empty">
          <div class="et">这条模板还没有预览 HTML</div>
          <div class="es">编辑并保存预览 HTML 后，可在这里看版式</div>
        </div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showPreview = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">编辑公推模板</h3>
        <label class="fld">模板名称</label>
        <input v-model="editForm.templateName" class="fld-in" data-testid="layout-edit-name" />
        <label class="fld">预览 HTML</label>
        <textarea v-model="editForm.previewHtml" class="fld-in" rows="4" />
        <p v-if="editError" class="hint bad" data-testid="layout-edit-name-error">{{ editError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showEdit = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitEdit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showView" class="modal-mask" @click.self="showView = false">
      <div class="card" style="width: 520px; padding: 20px" data-testid="layout-view-dialog">
        <h3 style="margin: 0 0 12px">查看 · {{ viewTitle }}</h3>
        <p class="hint">{{ viewMeta }} · 只读，预置模板不可编辑</p>
        <iframe
          v-if="viewHtml"
          sandbox=""
          :srcdoc="viewHtml"
          title="模板查看"
          style="width: 100%; height: 220px; border: 1px solid var(--line, #ddd); background: #fff"
        />
        <div v-else class="empty"><div class="et">这条模板还没有预览 HTML</div></div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showView = false">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="showImport" class="modal-mask" data-testid="layout-import" @click.self="showImport = false">
      <div class="card" style="width: 560px; padding: 20px">
        <h3 style="margin: 0 0 8px">导入向导</h3>
        <p class="hint" style="margin-bottom: 10px">ADR-020 套用 vs 预览 · 导入方式为 Tab（非步骤条）</p>
        <div class="tabs" style="margin-bottom: 10px">
          <button class="tab" :class="{ on: importTab === 'url' }" type="button" data-testid="layout-import-tab-url" @click="importTab = 'url'">公众号链接</button>
          <button class="tab" :class="{ on: importTab === 'mhtml' }" type="button" data-testid="layout-import-tab-mhtml" @click="importTab = 'mhtml'">MHTML 上传</button>
          <button class="tab" :class="{ on: importTab === 'html' }" type="button" data-testid="layout-import-tab-html" @click="importTab = 'html'">粘贴 HTML</button>
        </div>
        <template v-if="importTab === 'url'">
          <label class="fld">公众号链接 *</label>
          <input v-model="importUrl" class="fld-in" data-testid="layout-import-url" placeholder="https://mp.weixin.qq.com/s/…" />
          <label class="fld">模板名（可选）</label>
          <input v-model="importName" class="fld-in" placeholder="导入后模板名称" />
          <p class="hint">反爬失败时请改用 MHTML 或粘贴 HTML</p>
        </template>
        <template v-else-if="importTab === 'mhtml'">
          <label class="fld">.mhtml 单文件 *</label>
          <input data-testid="layout-import-file" type="file" accept=".mhtml,.mht" @change="onMhtmlFile" />
          <label class="fld">模板名（可选）</label>
          <input v-model="importName" class="fld-in" />
          <label class="fld">覆盖模板 ID（可选）</label>
          <input v-model="importOverrideId" class="fld-in" placeholder="留空为新建" />
          <p class="hint">上传后生成 DRAFT 模板</p>
        </template>
        <template v-else>
          <label class="fld">模板名 *</label>
          <input v-model="importName" class="fld-in" data-testid="layout-import-name" />
          <label class="fld">富文本 / 源码 *</label>
          <textarea v-model="importHtml" class="fld-in" rows="5" data-testid="layout-import-html" placeholder="<div>…</div>" />
          <p class="hint">开始导入后生成 DRAFT 模板</p>
        </template>
        <p v-if="importError" class="hint bad" data-testid="layout-import-error">{{ importError }}</p>
        <p v-if="importResult" class="hint" data-testid="layout-import-result">{{ importResult }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showImport = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="layout-import-submit" @click="submitImport">开始导入</button>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建公推模板</h3>
        <label class="fld">模板名称<span class="req">*</span></label>
        <input v-model="form.templateName" class="fld-in" data-testid="layout-create-name" />
        <label class="fld">标签</label>
        <input v-model="form.tags" class="fld-in" data-testid="layout-create-tags" placeholder="多个标签用逗号分隔" />
        <label class="fld">预览 HTML（可选）</label>
        <textarea v-model="form.previewHtml" class="fld-in" rows="3" />
        <p v-if="formError" class="hint bad" data-testid="layout-name-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Row = {
  id: number
  templateNo: string
  templateName: string
  source: string
  status: string
  documentType?: string
  tags?: string
  usageCount: number
  previewHtml?: string
  creatorName?: string
  updatedAt?: string
}

const docLabels: Record<string, string> = { SCRIPT: '脚本', COPY: '文案' }

function docLabel(code?: string) {
  if (!code) return '通用'
  return docLabels[code] || code
}

function previewText(html?: string) {
  const text = (html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  if (!text) return '—'
  return text.length > 24 ? `${text.slice(0, 24)}…` : text
}

function formatTime(value?: string) {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 16)
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const showEdit = ref(false)
const showPreview = ref(false)
const showView = ref(false)
const showImport = ref(false)
const formError = ref('')
const editError = ref('')
const previewTitle = ref('')
const previewHtml = ref('')
const viewTitle = ref('')
const viewHtml = ref('')
const viewMeta = ref('')
const importTab = ref<'url' | 'mhtml' | 'html'>('url')
const importUrl = ref('')
const importName = ref('')
const importHtml = ref('')
const importOverrideId = ref('')
const importFile = ref<File | null>(null)
const importError = ref('')
const importResult = ref('')
const editingId = ref<number | null>(null)
const filters = reactive({ templateName: '', status: '', source: '' })
const filtering = computed(() => !!(filters.templateName.trim() || filters.status || filters.source))
const layoutEmptyTitle = computed(() => (filtering.value ? '没有符合筛选的模板' : '暂无公推模板'))
const layoutEmptyHint = computed(() =>
  filtering.value ? '换名称、状态或来源，或重置筛选' : '点「新建模板」。预览 HTML 留空时，预览窗会说明版式还没写',
)
const form = reactive({ templateName: '', previewHtml: '', tags: '' })
const jobs = ref<{ jobId: string; channel: string; status: string; templateName: string; message: string; createdAt: string }[]>([])
const toast = ref('')
const pendingDelete = ref<Row | null>(null)
let toastTimer = 0

const channelLabels: Record<string, string> = { url: '公众号链接', mhtml: 'MHTML', html: '粘贴 HTML' }

function channelLabel(channel: string) {
  return channelLabels[channel] || channel || '—'
}

function showToast(message: string) {
  toast.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toast.value = ''
  }, 3000)
}
const editForm = reactive({ templateName: '', previewHtml: '' })

async function loadJobs() {
  try {
    const res = await http.get('/content/layout-template/import-job/list')
    jobs.value = res.data.data?.list || []
  } catch {
    jobs.value = []
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/content/layout-template/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        templateName: filters.templateName.trim() || undefined,
        status: filters.status || undefined,
        source: filters.source || undefined,
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

function resetFilters() {
  filters.templateName = ''
  filters.status = ''
  filters.source = ''
  void loadList()
}

function openCreate() {
  form.templateName = ''
  form.previewHtml = ''
  form.tags = ''
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  if (!form.templateName.trim()) {
    formError.value = '必填项，请填写'
    return
  }
  try {
    const res = await http.post('/content/layout-template', {
      templateName: form.templateName.trim(),
      previewHtml: form.previewHtml,
      tags: form.tags.trim(),
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
  if (!editForm.templateName.trim()) {
    editError.value = '请填写模板名称'
    return
  }
  try {
    const res = await http.put(`/content/layout-template/${editingId.value}`, {
      templateName: editForm.templateName.trim(),
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
  if (!enabled && !window.confirm('停用后新内容不可套用该模板，已使用内容不受影响')) return
  await http.put(`/content/layout-template/${id}/enable`, null, { params: { enabled } })
  await loadList()
}

function openView(row: Row) {
  viewTitle.value = row.templateName
  viewHtml.value = row.previewHtml || ''
  viewMeta.value = `${row.source} · ${row.status}`
  showView.value = true
}

async function copyTemplate(row: Row) {
  try {
    const res = await http.post(`/content/layout-template/${row.id}/copy`)
    if (res.data.code !== 0) {
      window.alert(res.data.msg || '复制失败')
      return
    }
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

function removeTemplate(row: Row) {
  pendingDelete.value = row
}

async function confirmDelete() {
  const row = pendingDelete.value
  if (!row) return
  try {
    const res = await http.delete(`/content/layout-template/${row.id}`)
    if (res.data.code !== 0) {
      showToast(res.data.msg || '删除失败')
      return
    }
    pendingDelete.value = null
    showToast('删除成功')
    await loadList()
  } catch (e) {
    showToast(errorMessage(e))
  }
}

function openImport() {
  importTab.value = 'url'
  importUrl.value = ''
  importName.value = ''
  importHtml.value = ''
  importOverrideId.value = ''
  importFile.value = null
  importError.value = ''
  importResult.value = ''
  showImport.value = true
}

function onMhtmlFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  importFile.value = input.files?.[0] || null
}

async function submitImport() {
  importError.value = ''
  importResult.value = ''
  try {
    if (importTab.value === 'url') {
      if (!importUrl.value.trim()) {
        importError.value = '必填项，请填写'
        return
      }
      await http.post('/content/layout-template/import-url', {
        url: importUrl.value.trim(),
        templateName: importName.value.trim(),
      })
      return
    }
    if (importTab.value === 'mhtml') {
      if (!importFile.value) {
        importError.value = '必填项，请填写'
        return
      }
      const data = new FormData()
      data.append('file', importFile.value)
      if (importName.value.trim()) data.append('templateName', importName.value.trim())
      if (importOverrideId.value.trim()) data.append('overrideId', importOverrideId.value.trim())
      await http.post('/content/layout-template/import-mhtml', data)
      showToast('导入成功')
      showImport.value = false
      await loadList()
      await loadJobs()
      return
    }
    if (!importName.value.trim() || !importHtml.value.trim()) {
      importError.value = '必填项，请填写'
      return
    }
    await http.post('/content/layout-template/import-paste', {
      templateName: importName.value.trim(),
      html: importHtml.value,
    })
    showToast('导入成功')
    showImport.value = false
    await loadList()
    await loadJobs()
  } catch (e) {
    importError.value = errorMessage(e)
    await loadJobs()
  }
}

onMounted(() => {
  void loadList()
  void loadJobs()
})
</script>

<style scoped>
.req {
  color: #d92d20;
  margin-left: 2px;
}
.layout-toast {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1400;
  background: #111;
  color: #fff;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
}
</style>
