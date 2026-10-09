<template>
  <div class="card" style="padding: 12px; margin-top: 8px" data-testid="content-ai-panel">
    <div class="dsec">AI 文案 / 视频</div>
    <p class="hint" data-testid="gpu-hint">无本机 GPU。生成走管理员配置的第三方地址，或本地桩；此处不显示密钥。</p>
    <p v-if="!hasMatch" class="hint bad">请先选择比赛（matchScheme 至少一场）后再生成。</p>
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
    <p v-if="content.videoFileKey" class="mono" data-testid="video-file-key">{{ content.videoFileKey }}</p>
    <div class="acts" style="margin-top: 8px; flex-wrap: wrap; gap: 8px">
      <button class="btn btn-pri btn-sm" type="button" data-testid="ai-copy-btn" :disabled="!canGenerate" @click="generateCopy">
        AI 生成文案
      </button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="ai-video-btn" :disabled="!canGenerate || !content.defaultWorkflowId" @click="generateVideo">
        视频生成
      </button>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="ai-video-task-btn"
        :disabled="!hasMatch || !content.defaultWorkflowId"
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

const copyLabelMap: Record<string, string> = {
  QUEUED: '生成中',
  GENERATING: '生成中',
  SUCCESS: '成功',
  FAILED: '失败',
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
const generating = computed(() => props.content.aiGenerateStatus === 'QUEUED' || props.content.aiGenerateStatus === 'GENERATING' || props.content.videoJobStatus === 'GENERATING')
const canGenerate = computed(() => editable.value && hasMatch.value && !busy.value && !generating.value)
const canRetryVideo = computed(() => props.content.videoJobStatus === 'FAILED' || props.content.videoJobStatus === 'REVIEW_REJECTED')
const copyLabel = computed(() => copyLabelMap[props.content.aiGenerateStatus] || '未生成')
const videoLabel = computed(() => videoLabelMap[props.content.videoJobStatus] || '未生成')

function requirement() {
  const title = String(props.content.title || '').trim()
  const body = String(props.content.body || '').trim()
  return [title, body].filter(Boolean).join('\n') || title
}

async function generateCopy() {
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
    window.alert(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function generateVideo() {
  busy.value = true
  try {
    const created = await http.post('/content/ai-production/task', {
      topicId: props.content.id,
      requirement: requirement(),
      workflowId: props.content.defaultWorkflowId,
    })
    const taskNo = created.data?.data?.taskNo
    if (!taskNo) {
      window.alert('未返回生产任务号')
      return
    }
    await http.post(`/content/ai-production/task/${taskNo}/run`)
    emit('refresh')
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function retryCopy() {
  busy.value = true
  try {
    await http.post(`/content/${props.content.id}/retry-ai-generate`)
    emit('refresh')
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function retryVideo() {
  const taskNo = props.content.videoTaskNo
  if (!taskNo) {
    window.alert('没有可重新发起的视频任务')
    return
  }
  busy.value = true
  try {
    await http.post(`/content/ai-production/task/${taskNo}/run`)
    emit('refresh')
  } catch (e) {
    window.alert(errorMessage(e))
  } finally {
    busy.value = false
  }
}

async function reviewVideo(pass: boolean) {
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
    window.alert(errorMessage(e))
  } finally {
    busy.value = false
  }
}
</script>
