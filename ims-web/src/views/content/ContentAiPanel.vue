<template>
  <div class="card" style="padding: 12px; margin-top: 8px" data-testid="content-ai-panel">
    <div class="dsec">AI 文案 / 视频</div>
    <p class="hint" data-testid="gpu-hint">无本机 GPU。生成走管理员配置的第三方地址，或本地桩；此处不显示密钥。</p>
    <p data-testid="ai-copy-provider">文案服务：{{ copyProviderLabel }}</p>
    <p data-testid="comfyui-stub-status">ComfyUI：{{ videoProviderLabel }}</p>
    <p v-if="copyIsEmpty" class="hint" data-testid="ai-copy-empty">尚未生成文案。预览与正文都还是空的，本地桩不占用本机 GPU。</p>
    <p v-if="locked" class="hint" data-testid="ai-panel-locked">当前不是草稿或驳回，不能新提交文案或视频。本地桩也不会出新任务。</p>
    <p v-if="copyUnconfigured" class="hint bad" data-testid="ai-copy-unconfigured">未配置 AI 文案地址，文案生成不可用。</p>
    <p v-if="videoUnconfigured" class="hint bad" data-testid="comfyui-unconfigured">未配置 ComfyUI 地址，视频生成不可用。</p>
    <p v-if="workflowMissing" class="hint" data-testid="ai-workflow-empty">还没有默认视频工作流，视频任务不可提交。</p>
    <p v-if="!hasMatch" class="hint bad" data-testid="ai-panel-need-match">请先选择比赛（matchScheme 至少一场）后再生成。本地桩也不会出稿。</p>
    <p data-testid="ai-copy-status">
      文案状态：{{ copyLabel }}
      <span v-if="content.aiGenerateError"> · {{ content.aiGenerateError }}</span>
    </p>
    <p data-testid="video-status">
      视频状态：{{ videoLabel }}
      <span v-if="content.videoFileKey"> · 产物 {{ content.videoFileKey }}</span>
      <span v-if="content.videoJobError"> · {{ content.videoJobError }}</span>
      <span v-else-if="content.videoRetryHint"> · {{ content.videoRetryHint }}</span>
    </p>
    <p v-if="panelError" class="hint bad" data-testid="ai-panel-error">{{ panelError }}</p>
    <p v-if="content.videoFileKey" class="mono" data-testid="video-file-key">{{ content.videoFileKey }}</p>
    <div class="acts" style="margin-top: 8px; flex-wrap: wrap; gap: 8px">
      <button class="btn btn-pri btn-sm" type="button" data-testid="ai-copy-btn" :disabled="!canGenerateCopy" @click="generateCopy">
        AI 生成文案
      </button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="ai-video-btn" :disabled="!canGenerate || !content.defaultWorkflowId || videoUnconfigured" @click="generateVideo">
        视频生成
      </button>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="ai-video-task-btn"
        :disabled="!hasMatch || !content.defaultWorkflowId || videoUnconfigured"
        @click="videoOpen = true"
      >
        视频任务
      </button>
      <button
        v-if="content.aiGenerateStatus === 'FAILED'"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="ai-copy-retry"
        :disabled="busy"
        @click="retryCopy"
      >
        重新发起文案
      </button>
      <button
        v-if="canRetryVideo"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="ai-video-retry"
        :disabled="busy"
        @click="retryVideo"
      >
        重新发起视频
      </button>
      <button
        v-if="content.videoJobStatus === 'PENDING_FINAL_REVIEW'"
        class="btn btn-pri btn-sm"
        type="button"
        data-testid="ai-review-pass"
        :disabled="busy"
        @click="reviewVideo(true)"
      >
        终审通过
      </button>
      <button
        v-if="content.videoJobStatus === 'PENDING_FINAL_REVIEW'"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="ai-review-reject"
        :disabled="busy"
        @click="reviewVideo(false)"
      >
        终审打回
      </button>
    </div>
    <p v-if="content.videoJobStatus === 'PENDING_FINAL_REVIEW'" class="hint" data-testid="ai-review-reject-hint">
      打回会记「终审打回，可重新发起」。本地桩不另开 GPU。
    </p>
    <ContentVideoDrawer
      v-if="videoOpen"
      :open="videoOpen"
      :content="content"
      @close="videoOpen = false"
      @refresh="emit('refresh')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import ContentVideoDrawer from './ContentVideoDrawer.vue'

const props = defineProps<{ content: Record<string, any> }>()
const emit = defineEmits<{ refresh: [] }>()
const busy = ref(false)
const videoOpen = ref(false)
const panelError = ref('')

const copyLabelMap: Record<string, string> = {
  QUEUED: '生成中',
  GENERATING: '生成中',
  GENERATED: '已生成',
  SUCCESS: '成功',
  FAILED: '失败',
}
const providerLabels: Record<string, string> = {
  stub: '桩（不占用本机 GPU）',
  remote: '第三方',
  unconfigured: '未配置',
}
const videoLabelMap: Record<string, string> = {
  WAITING: '待生成',
  GENERATING: '生成中',
  PENDING_FINAL_REVIEW: '待终审',
  REVIEW_PASSED: '终审通过',
  REVIEW_REJECTED: '终审打回',
  FAILED: '失败',
}

const hasMatch = computed(() => Array.isArray(props.content.matchScheme) && props.content.matchScheme.length > 0)
const editable = computed(() => props.content.contentStatus === 'DRAFT' || props.content.contentStatus === 'REJECTED')
const locked = computed(() => {
  const status = String(props.content.contentStatus || '')
  return !!status && !editable.value
})
const generating = computed(() => props.content.aiGenerateStatus === 'QUEUED' || props.content.aiGenerateStatus === 'GENERATING' || props.content.videoJobStatus === 'GENERATING')
const canGenerate = computed(() => editable.value && hasMatch.value && !busy.value && !generating.value)
const copyUnconfigured = computed(() => props.content.aiCopyProvider === 'unconfigured')
const canGenerateCopy = computed(() => canGenerate.value && !copyUnconfigured.value)
const canRetryVideo = computed(() => props.content.videoJobStatus === 'FAILED' || props.content.videoJobStatus === 'REVIEW_REJECTED')
const copyIsEmpty = computed(() => !props.content.aiGenerateStatus)
const videoUnconfigured = computed(() => props.content.videoProvider === 'unconfigured')
const workflowMissing = computed(() => !videoUnconfigured.value && !props.content.defaultWorkflowId)
const copyProviderLabel = computed(() => providerLabels[props.content.aiCopyProvider] || '未返回')
const videoProviderLabel = computed(() => providerLabels[props.content.videoProvider] || '未返回')
const copyLabel = computed(() => {
  const status = props.content.aiGenerateStatus
  if (!status) return '未生成'
  return copyLabelMap[status] || status
})
const videoLabel = computed(() => {
  const status = props.content.videoJobStatus
  if (!status) return '未生成'
  return videoLabelMap[status] || status
})

function requirement() {
  const title = String(props.content.title || '').trim()
  const body = String(props.content.body || '').trim()
  return [title, body].filter(Boolean).join('\n') || title
}

function noteError(message: string) {
  panelError.value = message
}

async function generateCopy() {
  panelError.value = ''
  if (!requirement()) {
    noteError('标题和正文都为空时不能生成。本地桩也不会出文案。')
    return
  }
  busy.value = true
  try {
    await http.post('/content/script/generate', {
      topicId: props.content.id,
      contentRequirement: requirement(),
      scriptType: 'MONOLOGUE',
      candidateCount: 2,
    })
    emit('refresh')
  } catch (e) {
    noteError(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function generateVideo() {
  panelError.value = ''
  if (!requirement()) {
    noteError('标题和正文都为空时不能生成。本地桩也不会出成片。')
    return
  }
  busy.value = true
  try {
    const created = await http.post('/content/ai-production/task', {
      topicId: props.content.id,
      requirement: requirement(),
      workflowId: props.content.defaultWorkflowId,
    })
    const taskNo = created.data?.data?.taskNo
    if (!taskNo) {
      noteError('未返回生产任务号')
      return
    }
    await http.post(`/content/ai-production/task/${taskNo}/run`)
    emit('refresh')
  } catch (e) {
    noteError(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function retryCopy() {
  panelError.value = ''
  busy.value = true
  try {
    await http.post(`/content/${props.content.id}/retry-ai-generate`)
    emit('refresh')
  } catch (e) {
    noteError(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function retryVideo() {
  panelError.value = ''
  const taskNo = props.content.videoTaskNo
  if (!taskNo) {
    noteError('没有可重新发起的视频任务')
    return
  }
  busy.value = true
  try {
    await http.post(`/content/ai-production/task/${taskNo}/run`)
    emit('refresh')
  } catch (e) {
    noteError(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function reviewVideo(pass: boolean) {
  panelError.value = ''
  const taskNo = props.content.videoTaskNo
  if (!taskNo) return
  busy.value = true
  try {
    await http.put(`/content/ai-production/task/${taskNo}/review`, {
      pass,
      comment: pass ? '' : '终审打回',
    })
    emit('refresh')
  } catch (e) {
    noteError(errorMessage(e))
  } finally {
    busy.value = false
  }
}
</script>
