<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>任务执行</h1>
        <div class="sub">{{ executeSubtitle }}</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec" type="button" @click="router.push('/ims/content/task')">返回我的任务</button>
      </div>
    </div>
    <p v-if="error" class="hint">{{ error }}</p>
    <div v-else-if="loading" class="empty"><div class="et">加载中</div></div>
    <template v-else>
      <div v-if="(vo.ipGroupTabs || []).length > 1" class="tabs" style="margin-bottom: 12px">
        <div
          v-for="tab in vo.ipGroupTabs"
          :key="tab.taskId"
          class="tab"
          :class="{ on: tab.taskId === vo.id }"
          @click="router.push(`/ims/content/task/${tab.taskId}/execute`)"
        >
          {{ tab.ipGroupName || tab.ipGroupId }}
        </div>
      </div>
      <div class="card" style="padding: 14px 16px; margin-bottom: 12px">
        <div class="rowline" style="flex-wrap: wrap; gap: 12px 20px; font-size: 13px">
          <span><span class="csub">任务</span> <b class="mono">{{ vo.id }}</b></span>
          <span><span class="csub">节点</span> {{ vo.nodeName }}</span>
          <span><span class="csub">计划</span> {{ vo.planName || '—' }}</span>
          <span><span class="csub">IP 组</span> {{ vo.ipGroupName }}</span>
          <span><span class="csub">赛事</span> {{ vo.competitionName || '—' }}</span>
          <span><span class="csub">状态</span> {{ vo.status }}</span>
        </div>
        <p v-if="vo.workTaskRemark" class="hint" style="margin-top: 8px">{{ vo.workTaskRemark }}</p>
      </div>
      <div class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">执行说明</div>
        <p style="font-size: 13px; margin: 0">{{ vo.executionInstruction || '—' }}</p>
      </div>
      <div class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">节点参考附件</div>
        <ul data-testid="task-ref-attachments" style="margin: 0; padding-left: 18px; font-size: 13px">
          <li v-for="(item, index) in refAttachments" :key="index">{{ refLabel(item) }}</li>
        </ul>
        <p v-if="!refAttachments.length" class="hint">无参考附件</p>
        <div class="dsec" style="margin-top: 10px">执行人上传附件</div>
        <ul data-testid="task-user-attachments" style="margin: 0; padding-left: 18px; font-size: 13px">
          <li v-for="(item, index) in userAttachments" :key="item.fileKey" style="margin-bottom: 6px">
            <span>{{ item.fileName }}</span>
            <button class="btn btn-sec btn-sm" type="button" style="margin-left: 8px" @click="downloadAttachment(item)">
              下载
            </button>
            <button class="btn btn-sec btn-sm" type="button" style="margin-left: 6px" @click="removeAttachment(index)">
              删除
            </button>
          </li>
        </ul>
        <p v-if="!userAttachments.length" class="hint">暂无上传附件</p>
        <label class="hint" style="display: block; margin-top: 8px">
          上传附件
          <input
            data-testid="task-attachment-file"
            type="file"
            :accept="acceptAttr"
            :disabled="uploading"
            style="margin-left: 8px"
            @change="onPickFile"
          />
        </label>
        <p class="hint">选择文件后点保存，附件才会写入任务。</p>
        <p v-if="uploadError" class="hint bad" data-testid="task-attachment-error">{{ uploadError }}</p>
      </div>
      <div v-if="vo.nodeType === 'CONTENT_GENERATION'" class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">关联内容</div>
        <p v-if="!vo.linkedContent">请先进入内容创作</p>
        <template v-else>
          <p>
            <b>{{ vo.linkedContent.title }}</b> · {{ vo.linkedContent.status }}
            <span v-if="vo.linkedContent.documentType"> · {{ vo.linkedContent.documentType }}</span>
            <span v-if="aiStatusLabel" class="ai-draft-status" :data-ai-status="vo.linkedContent.aiGenerateStatus">
              · AI {{ aiStatusLabel }}
            </span>
            <span v-if="vo.linkedContent.videoJobStatus"> · 视频 {{ vo.linkedContent.videoJobStatus }}</span>
          </p>
          <p v-if="vo.linkedContent.aiGenerateStatus === 'FAILED'" class="hint">
            {{ vo.linkedContent.aiGenerateError || 'AI 文案生成失败' }}
            <button class="btn btn-sec btn-sm" type="button" style="margin-left: 8px" @click="retryAi">重试</button>
          </p>
          <pre v-if="vo.linkedContent.body" class="ai-draft-body">{{ vo.linkedContent.body }}</pre>
          <p class="hint" data-testid="gpu-hint">无本机 GPU。密钥仅在系统参数中配置，任务页不展示。</p>
          <button class="btn btn-pri btn-sm" type="button" @click="openContentEdit">进入内容创作</button>
          <button
            v-if="canSubmitReview"
            class="btn btn-sec btn-sm"
            type="button"
            style="margin-left: 8px"
            @click="submitReview"
          >
            提交审核
          </button>
        </template>
      </div>
      <div v-else-if="vo.nodeType === 'CONTENT_PUBLISH'" class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">发布节点</div>
        <p class="hint" style="margin: 0">发布动作在内容管理与发布管理完成，本页不填写发布字段。</p>
      </div>
      <div v-else class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">工作说明</div>
        <textarea v-model="deliverables" style="width: 100%; min-height: 90px" placeholder="完成必填（ADR-079）" />
      </div>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-sec" type="button" :disabled="uploading" @click="saveExecute">保存</button>
        <span :title="completeHint">
          <button class="btn btn-pri" type="button" :disabled="!canComplete || uploading" :title="completeHint" @click="completeTask">
            完成
          </button>
        </span>
        <span v-if="completeHint" class="hint">{{ completeHint }}</span>
        <span v-if="savedHint" class="hint" data-testid="task-save-hint" style="margin-left: 8px">{{ savedHint }}</span>
      </div>
    </template>

    <ProtoDrawer :open="editOpen" title="内容编辑（玩法区）" width="880px" @close="editOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="editTitle" data-testid="task-content-title" />
          <p v-if="titleError" class="hint bad" data-testid="task-content-title-error">{{ titleError }}</p>
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
          <textarea v-model="editBody" rows="6" placeholder="正文" />
        </div>
        <ContentLayoutPanel
          :content-id="vo.linkedContent?.id || null"
          :body="editBody"
          :body-format="editBodyFormat"
          :layout-html="editLayoutHtml"
          @applied="onLayoutApplied"
        />
      </div>
      <ContentAiPanel v-if="editContent" :content="editContent" @refresh="refreshEditContent" />
      <AiCopyDrawer
        :open="aiOpen"
        :content-id="vo.linkedContent?.id"
        @close="aiOpen = false"
        @adopt="adoptAi"
      />
      <template #footer>
        <button class="btn btn-sec" type="button" @click="editOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="saveContent">保存内容</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import AiCopyDrawer from '../../components/AiCopyDrawer.vue'
import ContentLayoutPanel from '../../components/ContentLayoutPanel.vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import ContentAiPanel from './ContentAiPanel.vue'
import MatchSchemeEditor, { type MatchSchemeItem } from './MatchSchemeEditor.vue'
import { COMPLETE_GATE_HINT, contentPassesGate } from './content-gate'

type UserAttachment = { fileKey: string; fileName: string; fileUrl?: string }

const MAX_BYTES = 20 * 1024 * 1024
const ACCEPT_EXT = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'csv']
const acceptAttr = ACCEPT_EXT.map((ext) => `.${ext}`).join(',')

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.id))
const vo = ref<any>({})
const loading = ref(true)
const error = ref('')
const deliverables = ref('')
const userAttachments = ref<UserAttachment[]>([])
const uploading = ref(false)
const uploadError = ref('')
const savedHint = ref('')
const editOpen = ref(false)
const aiOpen = ref(false)
const editContent = ref<any>(null)
const editorSeed = ref(0)
const editTitle = ref('')
const titleError = ref('')
const editDocType = ref('COPY')
const editMatchType = ref(1)
const editScheme = ref<MatchSchemeItem[]>([])
const editBody = ref('')
const editLayoutHtml = ref('')
const editLayoutJson = ref('')
const editBodyFormat = ref('PLAIN')
const editLayoutTemplateId = ref<number | null>(null)

const executeSubtitle = computed(() => {
  if (loading.value) return '加载中…'
  const head = vo.value.planName || '工作任务'
  return `${head} · ${vo.value.nodeName || '—'}`
})

const aiStatusLabel = computed(() => {
  const status = vo.value.linkedContent?.aiGenerateStatus
  if (status === 'QUEUED' || status === 'GENERATING') return '生成中'
  if (status === 'GENERATED') return '已生成'
  if (status === 'FAILED') return '失败'
  return ''
})

const canSubmitReview = computed(() => {
  const st = vo.value.linkedContent?.status
  return st === 'DRAFT' || st === 'REJECTED'
})

const refAttachments = computed(() => (Array.isArray(vo.value.attachments) ? vo.value.attachments : []))

const canComplete = computed(() => {
  if (vo.value.nodeType === 'CONTENT_GENERATION') {
    return contentPassesGate(vo.value.linkedContent?.status)
  }
  if (vo.value.nodeType === 'CONTENT_PUBLISH') return false
  return String(deliverables.value).trim().length > 0
})

const completeHint = computed(() => {
  if (canComplete.value) return ''
  if (vo.value.nodeType === 'CONTENT_GENERATION') {
    if (!vo.value.linkedContent) return '请先进入内容创作'
    return COMPLETE_GATE_HINT
  }
  if (vo.value.nodeType === 'CONTENT_PUBLISH') return '发布节点不在本页完成'
  return '请填写工作说明'
})

async function loadExecute() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get(`/content/task/${taskId.value}/execute`)
    vo.value = data.data || {}
    deliverables.value = vo.value.deliverables || ''
    userAttachments.value = Array.isArray(vo.value.userAttachments) ? vo.value.userAttachments.map(asAttachment) : []
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function asAttachment(item: UserAttachment): UserAttachment {
  return { fileKey: item.fileKey, fileName: item.fileName, fileUrl: item.fileUrl }
}

function refLabel(item: unknown): string {
  if (typeof item === 'string') return item || '附件'
  if (item && typeof item === 'object') {
    const row = item as Record<string, unknown>
    return String(row.fileName || row.name || row.url || row.fileUrl || '附件')
  }
  return '附件'
}

function attachmentPayload() {
  return userAttachments.value.map((item) => ({ fileKey: item.fileKey, fileName: item.fileName }))
}

async function persistExecute() {
  const { data } = await http.post(`/content/task/${taskId.value}/execute/save`, {
    deliverables: deliverables.value,
    userAttachments: attachmentPayload(),
  })
  const saved = data.data?.userAttachments
  if (Array.isArray(saved)) userAttachments.value = saved.map(asAttachment)
}

async function saveExecute() {
  savedHint.value = ''
  try {
    await persistExecute()
    savedHint.value = '已保存'
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function completeTask() {
  if (!canComplete.value) return
  try {
    await persistExecute()
    await http.post(`/content/task/${taskId.value}/execute/complete`, {
      deliverables: deliverables.value || undefined,
    })
    router.push('/ims/content/task')
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

function removeAttachment(index: number) {
  userAttachments.value = userAttachments.value.filter((_, i) => i !== index)
  savedHint.value = ''
}

async function onPickFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files && input.files[0] ? input.files[0] : null
  input.value = ''
  uploadError.value = ''
  savedHint.value = ''
  if (!file) return
  const ext = file.name.includes('.') ? file.name.split('.').pop()!.toLowerCase() : ''
  if (!ACCEPT_EXT.includes(ext)) {
    uploadError.value = '不支持的文件类型'
    return
  }
  if (file.size <= 0) {
    uploadError.value = '文件为空'
    return
  }
  if (file.size > MAX_BYTES) {
    uploadError.value = '文件超过大小限制'
    return
  }
  uploading.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    body.append('scene', 'task_execute_attachment')
    const { data } = await http.post('/content/file/upload', body)
    const row = data.data || {}
    if (!row.fileKey) {
      uploadError.value = '文件上传失败，请重试'
      return
    }
    userAttachments.value = [
      ...userAttachments.value.filter((item) => item.fileKey !== row.fileKey),
      { fileKey: row.fileKey, fileName: row.fileName || file.name, fileUrl: row.fileUrl },
    ]
  } catch (e) {
    uploadError.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}

async function downloadAttachment(item: UserAttachment) {
  try {
    const res = await http.get(`/file/${item.fileKey}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = item.fileName || 'attachment'
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

function adoptAi(payload: { markdown: string }) {
  editBody.value = payload.markdown
  aiOpen.value = false
}

async function openContentEdit() {
  titleError.value = ''
  const lc = vo.value.linkedContent
  const seedTitle = lc?.title || ''
  const seedBody = lc?.body || ''
  editTitle.value = seedTitle
  editDocType.value = lc?.documentType || 'COPY'
  editMatchType.value = 1
  editScheme.value = []
  editBody.value = seedBody
  editContent.value = null
  aiOpen.value = false
  if (lc?.id) {
    try {
      const { data } = await http.get(`/content/${lc.id}`)
      const detail = data.data || {}
      editContent.value = detail
      if (editTitle.value === seedTitle) editTitle.value = detail.title || seedTitle
      editDocType.value = detail.documentType || editDocType.value
      editMatchType.value = detail.matchType || 1
      editScheme.value = Array.isArray(detail.matchScheme) ? detail.matchScheme : []
      if (editBody.value === seedBody) editBody.value = detail.body || seedBody
      editLayoutHtml.value = detail.layoutHtml || ''
      editLayoutJson.value = typeof detail.layoutJson === 'string' ? detail.layoutJson : JSON.stringify(detail.layoutJson || '')
      editBodyFormat.value = detail.bodyFormat || 'PLAIN'
      editLayoutTemplateId.value = detail.layoutTemplateId ?? null
    } catch (e) {
      window.alert(errorMessage(e))
      return
    }
  } else {
    editLayoutHtml.value = ''
    editLayoutJson.value = ''
    editBodyFormat.value = 'PLAIN'
    editLayoutTemplateId.value = null
  }
  editorSeed.value += 1
  editOpen.value = true
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

async function refreshEditContent() {
  const cid = vo.value.linkedContent?.id
  if (!cid) return
  const { data } = await http.get(`/content/${cid}`)
  const detail = data.data || {}
  editContent.value = detail
  editBody.value = detail.body || editBody.value
  await loadExecute()
}

async function saveContent() {
  titleError.value = ''
  if (!editTitle.value.trim()) {
    titleError.value = '请填写标题'
    window.alert('请填写标题')
    return
  }
  const payload = {
    title: editTitle.value.trim(),
    documentType: editDocType.value,
    matchType: editMatchType.value,
    matchScheme: editScheme.value,
    body: editBody.value,
    layoutHtml: editLayoutHtml.value,
    layoutJson: editLayoutJson.value,
    bodyFormat: editBodyFormat.value,
    layoutTemplateId: editLayoutTemplateId.value,
    taskId: vo.value.id,
    ipGroupId: vo.value.ipGroupId,
  }
  try {
    const cid = vo.value.linkedContent?.id
    if (cid) {
      await http.put(`/content/${cid}`, payload)
    } else {
      await http.post('/content', payload)
    }
    editOpen.value = false
    editContent.value = null
    await loadExecute()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function submitReview() {
  const cid = vo.value.linkedContent?.id
  if (!cid) return
  try {
    await http.post(`/content/${cid}/submit-review`)
    await loadExecute()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function retryAi() {
  const cid = vo.value.linkedContent?.id
  if (!cid) return
  try {
    await http.post(`/content/${cid}/retry-ai-generate`)
    await loadExecute()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

watch(taskId, loadExecute, { immediate: true })
</script>

<style scoped>
.ai-draft-body {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 8px 0 12px;
  max-height: 220px;
  overflow: auto;
  background: #f6f8fa;
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 10px 12px;
  font-size: 12.5px;
  line-height: 1.55;
}
</style>
