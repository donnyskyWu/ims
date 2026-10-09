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
        <p v-if="!(vo.attachments || []).length" class="hint">暂无</p>
        <ul v-else style="margin: 0; padding-left: 18px">
          <li v-for="(item, index) in vo.attachments" :key="index">{{ attachmentLabel(item) }}</li>
        </ul>
        <div class="dsec" style="margin-top: 10px">执行人上传附件</div>
        <p v-if="!(vo.userAttachments || []).length" class="hint">暂无</p>
        <ul v-else style="margin: 0; padding-left: 18px">
          <li v-for="(item, index) in vo.userAttachments" :key="index">{{ attachmentLabel(item) }}</li>
        </ul>
      </div>
      <div v-if="vo.nodeType === 'CONTENT_GENERATION'" class="card" style="padding: 12px 16px; margin-bottom: 12px">
        <div class="dsec">关联内容</div>
        <p v-if="!vo.linkedContent">请先进入内容创作</p>
        <template v-else>
          <p>
            <b>{{ vo.linkedContent.title }}</b> · {{ vo.linkedContent.status }}
            <span v-if="vo.linkedContent.documentType"> · {{ vo.linkedContent.documentType }}</span>
            <span v-if="vo.linkedContent.aiGenerateStatus"> · 文案 {{ vo.linkedContent.aiGenerateStatus }}</span>
            <span v-if="vo.linkedContent.videoJobStatus"> · 视频 {{ vo.linkedContent.videoJobStatus }}</span>
            <span v-if="vo.linkedContent.aiGenerateStatus === 'FAILED' && vo.linkedContent.aiGenerateError">
              · {{ vo.linkedContent.aiGenerateError }}
            </span>
          </p>
          <p class="hint" data-testid="gpu-hint">无本机 GPU。密钥仅在系统参数中配置，任务页不展示。</p>
          <button class="btn btn-pri btn-sm" type="button" @click="openContentEdit">进入内容创作</button>
          <button
            v-if="vo.linkedContent.aiGenerateStatus === 'FAILED'"
            class="btn btn-sec btn-sm"
            type="button"
            style="margin-left: 8px"
            @click="retryAi"
          >
            重新发起文案
          </button>
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
        <button class="btn btn-sec" type="button" @click="saveExecute">保存</button>
        <span :title="completeHint">
          <button class="btn btn-pri" type="button" :disabled="!canComplete" :title="completeHint" @click="completeTask">
            完成
          </button>
        </span>
        <span v-if="completeHint" class="hint">{{ completeHint }}</span>
      </div>
    </template>

    <ProtoDrawer :open="editOpen" title="内容编辑（玩法区）" width="720px" @close="editOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="editTitle" />
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
      <ContentAiPanel v-if="editContent" :content="editContent" @refresh="refreshEditContent" />
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
import ContentAiPanel from './ContentAiPanel.vue'
import MatchSchemeEditor, { type MatchSchemeItem } from './MatchSchemeEditor.vue'
import { COMPLETE_GATE_HINT, contentPassesGate } from './content-gate'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.id))
const vo = ref<any>({})
const loading = ref(true)
const error = ref('')
const deliverables = ref('')
const editOpen = ref(false)
const editContent = ref<any>(null)
const editorSeed = ref(0)
const editTitle = ref('')
const editDocType = ref('COPY')
const editMatchType = ref(1)
const editScheme = ref<MatchSchemeItem[]>([])
const editBody = ref('')

const executeSubtitle = computed(() => {
  if (loading.value) return '加载中…'
  const head = vo.value.planName || '工作任务'
  return `${head} · ${vo.value.nodeName || '—'}`
})

const canSubmitReview = computed(() => {
  const st = vo.value.linkedContent?.status
  return st === 'DRAFT' || st === 'REJECTED'
})

const aiBadge = computed(() => {
  const st = vo.value.linkedContent?.aiGenerateStatus
  if (st === 'QUEUED' || st === 'GENERATING') return '生成中'
  if (st === 'FAILED') return '失败'
  if (st === 'SUCCESS' || st === 'DONE') return st
  return ''
})

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

function attachmentLabel(item: unknown): string {
  if (typeof item === 'string') return item
  if (item && typeof item === 'object') {
    const row = item as Record<string, unknown>
    return String(row.fileName || row.name || row.fileKey || row.url || '附件')
  }
  return '附件'
}

async function loadExecute() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get(`/content/task/${taskId.value}/execute`)
    vo.value = data.data || {}
    deliverables.value = vo.value.deliverables || ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function saveExecute() {
  try {
    await http.post(`/content/task/${taskId.value}/execute/save`, {
      deliverables: deliverables.value,
    })
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function completeTask() {
  if (!canComplete.value) return
  try {
    await http.post(`/content/task/${taskId.value}/execute/complete`, {
      deliverables: deliverables.value || undefined,
    })
    router.push('/ims/content/task')
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

async function openContentEdit() {
  const lc = vo.value.linkedContent
  editTitle.value = lc?.title || ''
  editDocType.value = lc?.documentType || 'COPY'
  editMatchType.value = 1
  editScheme.value = []
  editBody.value = ''
  editContent.value = null
  if (lc?.id) {
    try {
      const { data } = await http.get(`/content/${lc.id}`)
      const detail = data.data || {}
      editContent.value = detail
      editTitle.value = detail.title || editTitle.value
      editDocType.value = detail.documentType || editDocType.value
      editMatchType.value = detail.matchType || 1
      editScheme.value = Array.isArray(detail.matchScheme) ? detail.matchScheme : []
      editBody.value = detail.body || ''
    } catch (e) {
      window.alert(errorMessage(e))
      return
    }
  }
  editorSeed.value += 1
  editOpen.value = true
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
  if (!editTitle.value.trim()) {
    window.alert('请填写标题')
    return
  }
  const payload = {
    title: editTitle.value.trim(),
    documentType: editDocType.value,
    matchType: editMatchType.value,
    matchScheme: editScheme.value,
    body: editBody.value,
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
