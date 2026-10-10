<template>
  <ProtoDrawer :open="open" title="视频生成" width="640px" :z-index="160" @close="close">
    <div data-testid="video-gen-drawer">
      <p class="hint">无本机 GPU。提交后轮询任务状态，成功即绑定到本条内容。密钥不在此显示。</p>
      <p v-if="provider" data-testid="video-provider">服务：{{ providerLabel }}</p>
      <p v-if="!editable" class="hint" data-testid="video-locked">只有草稿或被驳回的内容可以提交视频任务。</p>
      <div class="fld">
        <label>成片要求</label>
        <textarea v-model="requirementText" rows="4" data-testid="video-requirement" :disabled="busy" />
      </div>
      <p v-if="editable && !requirementText.trim()" class="hint" data-testid="video-requirement-empty">
        成片要求为空时不能提交。本地桩不会出片，也不占用本机 GPU。
      </p>
      <p data-testid="video-poll-status">
        任务状态：{{ statusLabel }}
        <span v-if="progress != null && polling"> · {{ progress }}%</span>
        <span v-if="jobId"> · 任务 {{ jobId }}</span>
      </p>
      <p v-if="pollStale" class="hint" data-testid="video-poll-wait">桩任务仍在排队。关闭后再打开可继续看状态。</p>
      <p v-if="errorText" class="hint bad" data-testid="video-gen-error">{{ errorText }}</p>
      <div v-if="!showPreview && !errorText" class="empty" data-testid="video-preview-empty">
        <div class="et">尚未绑定成片</div>
        <div class="es">提交后由本地桩轮询，成功才出现预览。</div>
      </div>
      <div v-if="showPreview" class="video-preview" data-testid="video-preview">
        <div class="video-frame" data-testid="video-preview-frame">成片预览</div>
        <p data-testid="video-bind-line">已绑定到本条内容 · {{ fileKey }}</p>
      </div>
    </div>
    <template #footer>
      <button class="btn btn-sec" type="button" @click="close">关闭</button>
      <button
        class="btn btn-pri"
        type="button"
        data-testid="video-submit-btn"
        :disabled="!canSubmit"
        @click="submitJob"
      >
        提交视频任务
      </button>
    </template>
  </ProtoDrawer>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const props = defineProps<{ open: boolean; content: Record<string, any> }>()
const emit = defineEmits<{ close: []; refresh: [] }>()

const busy = ref(false)
const polling = ref(false)
const requirementText = ref('')
const provider = ref('')
const pollStatus = ref('')
const progress = ref<number | null>(null)
const jobId = ref<number | null>(null)
const fileKey = ref('')
const bound = ref(false)
const errorText = ref('')
const pollStale = ref(false)
let pollToken = 0

const providerLabels: Record<string, string> = {
  stub: '桩（不占用本机 GPU）',
  remote: '第三方 ComfyUI',
  unconfigured: '未配置',
}
const statusLabels: Record<string, string> = {
  WAITING: '排队',
  GENERATING: '生成中',
  SUCCESS: '已完成',
  FAILED: '失败',
  PENDING_FINAL_REVIEW: '待终审',
}

const providerLabel = computed(() => providerLabels[provider.value] || provider.value)
const statusLabel = computed(() => statusLabels[pollStatus.value] || (pollStatus.value ? pollStatus.value : '未提交'))
const showPreview = computed(() => bound.value && !!fileKey.value)
const editable = computed(() => props.content.contentStatus === 'DRAFT' || props.content.contentStatus === 'REJECTED')
const canSubmit = computed(
  () => editable.value && !busy.value && !polling.value && !!props.content.defaultWorkflowId && !!requirementText.value.trim(),
)

function seedFromContent() {
  const title = String(props.content.title || '').trim()
  const body = String(props.content.body || '').trim()
  requirementText.value = [title, body].filter(Boolean).join('\n') || title
  provider.value = String(props.content.videoProvider || '')
  fileKey.value = String(props.content.videoFileKey || '')
  bound.value = !!fileKey.value
  pollStatus.value = String(props.content.videoJobStatus || '')
  jobId.value = props.content.videoJobId || null
  errorText.value = String(props.content.videoJobError || '')
  pollStale.value = false
}

watch(
  () => props.open,
  (open) => {
    if (!open) return
    seedFromContent()
    if ((pollStatus.value === 'WAITING' || pollStatus.value === 'GENERATING') && jobId.value) {
      void pollUntilDone(jobId.value)
    }
  },
  { immediate: true },
)

function close() {
  pollToken += 1
  emit('close')
}

function applyJob(job: Record<string, any>) {
  provider.value = String(job.provider || provider.value || '')
  pollStatus.value = String(job.queueStatus || '')
  progress.value = typeof job.progress === 'number' ? job.progress : null
  jobId.value = job.id || jobId.value
  if (job.preview?.ready && job.preview.fileKey) {
    fileKey.value = String(job.preview.fileKey)
    bound.value = !!job.boundContentId
  } else if (job.resultFileKey) {
    fileKey.value = String(job.resultFileKey)
  }
  errorText.value = job.queueStatus === 'FAILED' ? String(job.errorMsg || '视频生成失败，可重新发起') : ''
}

async function sleep(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function pollUntilDone(id: number) {
  const token = ++pollToken
  polling.value = true
  pollStale.value = false
  let settled = false
  try {
    for (let i = 0; i < 8; i += 1) {
      if (token !== pollToken) return
      const { data } = await http.get(`/content/ai-job/${id}/status`)
      const job = data.data || {}
      applyJob(job)
      if (job.queueStatus === 'SUCCESS' || job.queueStatus === 'FAILED') {
        settled = true
        emit('refresh')
        return
      }
      await sleep(700)
    }
  } catch (e) {
    if (token === pollToken) {
      errorText.value = errorMessage(e)
      settled = true
    }
  } finally {
    if (token === pollToken) {
      polling.value = false
      pollStale.value = !settled && pollStatus.value !== 'SUCCESS' && pollStatus.value !== 'FAILED'
    }
  }
}

async function submitJob() {
  busy.value = true
  errorText.value = ''
  pollStale.value = false
  bound.value = false
  fileKey.value = ''
  try {
    const created = await http.post('/content/ai-production/task', {
      topicId: props.content.id,
      requirement: requirementText.value.trim(),
      workflowId: props.content.defaultWorkflowId,
    })
    const taskNo = created.data?.data?.taskNo
    if (!taskNo) {
      errorText.value = '未返回生产任务号'
      return
    }
    const submitted = await http.post('/content/ai-job/submit', {
      taskNo,
      workflowId: props.content.defaultWorkflowId,
      nodeName: '成片',
      params: { text: requirementText.value.trim() },
      priority: 'P2',
    })
    const job = submitted.data?.data
    if (!job?.id) {
      errorText.value = '未返回视频任务'
      return
    }
    applyJob(job)
    busy.value = false
    await pollUntilDone(job.id)
  } catch (e) {
    errorText.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

onBeforeUnmount(() => {
  pollToken += 1
})
</script>

<style scoped>
.video-preview {
  margin-top: 12px;
}
.video-frame {
  height: 148px;
  border-radius: 8px;
  background: linear-gradient(160deg, #1c1c1e, #3a3a3c);
  color: #fff;
  display: flex;
  align-items: flex-end;
  padding: 12px 14px;
  font-size: 13px;
}
</style>
