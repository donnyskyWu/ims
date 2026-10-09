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
        <button class="btn btn-sec" type="button" @click="saveExecute">保存</button>
        <button class="btn btn-pri" type="button" :disabled="!canComplete" @click="completeTask">完成</button>
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
          <div class="rowline" style="justify-content: space-between; margin-bottom: 6px">
            <label style="margin: 0">正文</label>
            <button class="btn btn-sec btn-sm" type="button" @click="aiOpen = true">AI 文案</button>
          </div>
          <textarea v-model="editForm.body" rows="6" />
        </div>
      </div>
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
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import AiCopyDrawer from '../../components/AiCopyDrawer.vue'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.id))
const vo = ref<any>({})
const loading = ref(true)
const error = ref('')
const deliverables = ref('')
const editOpen = ref(false)
const aiOpen = ref(false)
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
  try {
    await http.post(`/content/task/${taskId.value}/execute/complete`, {
      deliverables: deliverables.value || undefined,
    })
    router.push('/ims/content/task')
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

function adoptAi(payload: { markdown: string; targetField: string }) {
  const key = payload.targetField
  if ((key === 'paidBody' || key === 'freeBody') && key in editForm.value) {
    ;(editForm.value as Record<string, string>)[key] = payload.markdown
  } else {
    editForm.value.body = payload.markdown
  }
  aiOpen.value = false
}

async function openContentEdit() {
  const lc = vo.value.linkedContent
  editForm.value.title = lc?.title || ''
  editForm.value.body = ''
  editForm.value.matchType = 1
  editForm.value.matchSchemeJson = '[]'
  aiOpen.value = false
  if (lc?.id) {
    try {
      const { data } = await http.get(`/content/${lc.id}`)
      const row = data.data || {}
      editForm.value.title = row.title || editForm.value.title
      editForm.value.body = row.body || ''
      editForm.value.matchType = row.matchType || 1
      editForm.value.matchSchemeJson = JSON.stringify(row.matchScheme || [], null, 2)
    } catch (e) {
      window.alert(errorMessage(e))
      return
    }
  }
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
