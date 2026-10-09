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
      <div class="card" style="padding: 14px 16px; margin-bottom: 12px">
        <div class="rowline" style="flex-wrap: wrap; gap: 12px 20px; font-size: 13px">
          <span><span class="csub">任务</span> <b class="mono">{{ vo.id }}</b></span>
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
        <div class="dsec">执行人上传附件</div>
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
        <p v-if="!vo.linkedContent">请先保存内容（工作任务确认后通常已有 DRAFT）</p>
        <template v-else>
          <p>
            <b>{{ vo.linkedContent.title }}</b> · {{ vo.linkedContent.status }}
            <span v-if="vo.linkedContent.aiGenerateStatus"> · AI {{ vo.linkedContent.aiGenerateStatus }}</span>
          </p>
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
      <div v-else class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">工作说明</div>
        <textarea v-model="deliverables" style="width: 100%; min-height: 90px" placeholder="完成必填（ADR-079）" />
      </div>
      <div class="acts" style="margin-top: 12px">
        <button class="btn btn-sec" type="button" :disabled="uploading" @click="saveExecute">保存</button>
        <button class="btn btn-pri" type="button" :disabled="!canComplete || uploading" @click="completeTask">完成</button>
        <span v-if="savedHint" class="hint" data-testid="task-save-hint" style="margin-left: 8px">{{ savedHint }}</span>
      </div>
    </template>

    <ProtoDrawer :open="editOpen" title="内容编辑（玩法区）" width="720px" @close="editOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="editForm.title" />
        </div>
        <div class="fld">
          <label>matchType（1 竞足）</label>
          <input v-model.number="editForm.matchType" type="number" min="1" max="5" />
        </div>
        <div class="fld">
          <label>matchScheme JSON</label>
          <textarea v-model="editForm.matchSchemeJson" rows="6" placeholder='[{"matchId":"1","homeName":"主","awayName":"客","matchPlays":[]}]' />
        </div>
        <div class="fld">
          <label>正文</label>
          <textarea v-model="editForm.body" rows="4" />
        </div>
      </div>
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
import ProtoDrawer from '../../components/ProtoDrawer.vue'

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

type UserAttachment = { fileKey: string; fileName: string; fileUrl?: string }

const MAX_BYTES = 20 * 1024 * 1024
const ACCEPT_EXT = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'csv']
const acceptAttr = ACCEPT_EXT.map((ext) => `.${ext}`).join(',')
const editForm = ref({
  title: '',
  matchType: 1,
  matchSchemeJson: '[]',
  body: '',
})

const approvedStatuses = new Set(['PENDING_PUBLISH', 'PUBLISHED_DRAFT', 'FORMALLY_PUBLISHED', 'PUBLISHED', 'UNPUBLISHED'])

const executeSubtitle = computed(() => {
  if (loading.value) return '加载中…'
  const head = vo.value.planName || '工作任务'
  return `${head} · ${vo.value.nodeName || '—'}`
})

const canSubmitReview = computed(() => {
  const st = vo.value.linkedContent?.status
  return st === 'DRAFT' || st === 'REJECTED'
})

const refAttachments = computed(() => (Array.isArray(vo.value.attachments) ? vo.value.attachments : []))

const canComplete = computed(() => {
  if (vo.value.nodeType === 'CONTENT_GENERATION') {
    const lc = vo.value.linkedContent
    if (!lc) return false
    return approvedStatuses.has(lc.status)
  }
  return String(deliverables.value).trim().length > 0
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

function openContentEdit() {
  const lc = vo.value.linkedContent
  editForm.value.title = lc?.title || ''
  editForm.value.body = ''
  editForm.value.matchType = 1
  editForm.value.matchSchemeJson = '[]'
  editOpen.value = true
}

async function saveContent() {
  const cid = vo.value.linkedContent?.id
  if (!cid) return
  let scheme: unknown[] = []
  try {
    scheme = JSON.parse(editForm.value.matchSchemeJson || '[]')
  } catch {
    window.alert('matchScheme JSON 无效')
    return
  }
  try {
    await http.put(`/content/${cid}`, {
      title: editForm.value.title,
      matchType: editForm.value.matchType,
      matchScheme: scheme,
      body: editForm.value.body,
    })
    editOpen.value = false
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

watch(taskId, loadExecute, { immediate: true })
</script>
