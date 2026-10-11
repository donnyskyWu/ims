<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>学习中心</h1>
        <div class="sub">TRAIN-002 · 任务 #{{ taskId }} · 学习执行</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="router.push('/ims/train/task')">返回任务列表</button>
      </div>
    </div>

    <p v-if="loadError" class="hint" data-testid="train-study-load-error" style="color: var(--red)">{{ loadError }}</p>
    <p v-if="notAssignee && !task" style="margin-top: 8px">
      <router-link class="btn btn-sec btn-sm" to="/ims/workbench" data-testid="train-study-back-workbench">
        返回工作台
      </router-link>
    </p>
    <div v-else-if="task" class="g2">
      <div class="card head">
        <div style="font-weight: 600; font-size: 16px">{{ task.taskName }}</div>
        <div class="meta">
          编号 {{ task.taskNo }} · 截止 <span data-testid="train-study-deadline">{{ deadlineText }}</span> · {{ confirmTypeLabel }}
        </div>
        <p v-if="overdueDays > 0" class="hint overdue-banner" data-testid="train-study-overdue">
          本任务已逾期 {{ overdueDays }} 天，补学仍计入完成率统计
        </p>
        <div class="meta">
          总进度 <strong>{{ progressPct }}%</strong>
          · 学时 <strong data-testid="train-study-hours">{{ studyHoursText }}</strong>
          · 确认状态
          <span :class="confirmStatus === 'CONFIRMED' ? 'ok' : 'pending'">{{ confirmStatusLabel }}</span>
        </div>
      </div>

      <div class="card" style="padding: 12px">
        <div style="font-weight: 600; margin-bottom: 8px">资料清单</div>
        <ul v-if="materials.length" class="mat-list">
          <li
            v-for="m in materials"
            :key="m.id"
            :class="{ on: activeMaterialId === m.id }"
            @click="activeMaterialId = m.id"
          >
            <div>
              <div>{{ m.title }}</div>
              <div class="hint">{{ materialKindLabel(m) }}</div>
              <div class="hint">要求 {{ m.requiredMinutes || 1 }} 分钟 · 已学 {{ learnedMinutes(m.id) }} 分钟</div>
            </div>
            <span class="mono">{{ materialPct(m.id) }}%</span>
          </li>
        </ul>
        <p v-if="materials.length && hiddenMaterialCount > 0" class="hint" data-testid="train-study-material-hidden">
          有 {{ hiddenMaterialCount }} 份资料已下架或未发布，清单只显示仍可学习的资料
        </p>
        <div v-if="!materials.length" class="empty" data-testid="train-study-material-missing">
          <template v-if="(task.materialIds || []).length">
            <div class="et">关联资料已下架或未发布，暂不可学习</div>
            <div class="es">请联系培训负责人恢复资料后再学习</div>
          </template>
          <div v-else class="et">无关联资料</div>
        </div>

        <div v-if="activeMaterial" class="stage" data-testid="train-study-player">
          <div class="stage-title">{{ activeMaterial.title }}</div>
          <div v-if="previewMode === 'video'" class="stage-body">
            <video
              v-if="previewUrl"
              ref="videoRef"
              data-testid="train-study-video"
              controls
              playsinline
              :src="previewUrl"
              @play="onVideoPlay"
              @pause="onVideoPause"
            />
            <p v-else-if="previewLoading" class="hint">视频加载中</p>
            <p v-else class="hint" data-testid="train-study-preview-error">{{ previewError || '暂无可播放的视频' }}</p>
          </div>
          <div v-else-if="previewMode === 'doc'" class="stage-body">
            <iframe
              v-if="previewUrl && docEmbeddable"
              data-testid="train-study-doc"
              :src="previewUrl"
              title="文档预览"
            />
            <object
              v-else-if="previewUrl"
              data-testid="train-study-doc"
              :data="previewUrl"
              :type="previewMime || 'application/octet-stream'"
            >
              <p class="hint">当前格式请打开资料查看</p>
            </object>
            <p v-else-if="previewLoading" class="hint">文档加载中</p>
            <p v-else class="hint" data-testid="train-study-preview-error">{{ previewError || '暂无可预览的文档' }}</p>
            <a v-if="previewUrl" class="linkish" :href="previewUrl" target="_blank" rel="noopener">打开资料</a>
          </div>
          <div v-else-if="previewMode === 'link'" class="stage-body">
            <a class="linkish" :href="activeMaterial.linkUrl" target="_blank" rel="noopener">打开外链</a>
            <p class="hint">打开资料后点击开始学习，学习时长计入学时</p>
          </div>
          <div v-else class="empty" data-testid="train-study-material-empty">
            <div class="et">暂无可预览</div>
          </div>
          <div v-if="confirmStatus !== 'CONFIRMED'" class="acts" style="margin-top: 12px">
            <button
              class="btn btn-pri btn-sm"
              type="button"
              data-testid="train-study-start"
              :disabled="busy || (studying && previewMode !== 'video')"
              @click="startStudy"
            >
              {{ studying ? '学习中' : '开始学习' }}
            </button>
          </div>
        </div>

        <p
          v-if="materials.length && task.confirmType !== 'QUIZ' && confirmStatus !== 'CONFIRMED' && remainMinutes > 0"
          class="hint"
          data-testid="train-study-gap"
        >
          还差 {{ remainMinutes }} 分钟学时，学时达标后才能完成确认
        </p>
        <div v-if="materials.length && confirmStatus !== 'CONFIRMED' && task.confirmType !== 'QUIZ'" class="acts" style="margin-top: 16px; flex-wrap: wrap; gap: 8px">
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="train-study-confirm"
            :disabled="busy || !hoursMet"
            :title="hoursMet ? '' : `还差 ${remainMinutes} 分钟学时`"
            @click="confirmComplete"
          >
            完成确认
          </button>
        </div>

        <div v-if="task.confirmType === 'QUIZ' && confirmStatus !== 'CONFIRMED'" class="quiz-paper">
          <div class="quiz-head" data-testid="train-quiz-full-score">满分 100 / 及格分 {{ task.passScore }} · 共 {{ quiz.length }} 题</div>
          <p class="hint">全部题目必答。提交后将判分，未及格可重答，成绩保留最新一次。</p>
          <p v-if="mustAllCorrect" class="hint" data-testid="train-study-quiz-all-correct">须全部答对才能通过</p>
          <p v-if="latestScore == null" class="hint score-empty" data-testid="train-quiz-score-empty">暂无成绩</p>
          <p v-else class="hint grade-banner" data-testid="train-quiz-score-latest"><span data-testid="train-quiz-grade">{{ gradeText }}</span></p>
          <div v-if="!quiz.length" class="empty" data-testid="train-quiz-empty">
            <div class="et">问卷未配置，无法交卷</div>
            <div class="es">请联系培训负责人补全题目后再学习</div>
          </div>
          <p v-else-if="unansweredCount > 0" class="hint" data-testid="train-quiz-unanswered">
            还有 {{ unansweredCount }} 题未作答
          </p>
          <div v-for="(q, qi) in quiz" :key="qi" class="quiz-q">
            <div class="q-title">{{ qi + 1 }}. {{ q.question }}</div>
            <div v-if="!q.options?.length" class="hint" data-testid="train-quiz-option-empty">该题暂无选项</div>
            <label v-for="(opt, oi) in q.options" :key="oi" class="opt">
              <input
                type="radio"
                :name="'quiz-' + qi"
                :value="oi"
                :checked="answers[qi] === oi"
                @change="answers[qi] = oi"
              />
              {{ opt }}
            </label>
          </div>
          <div class="acts" style="margin-top: 8px; gap: 8px; flex-wrap: wrap">
            <button
              class="btn btn-pri btn-sm"
              type="button"
              :disabled="busy || !quizReady"
              :title="quizReady ? '' : '请答完全部题目'"
              @click="showQuizConfirm = true"
            >
              提交问卷
            </button>
            <button
              v-if="latestScore != null"
              class="btn btn-sec btn-sm"
              type="button"
              data-testid="train-quiz-retake"
              :disabled="busy"
              @click="startRetake"
            >
              重新作答
            </button>
          </div>
          <p v-if="gradeText" class="hint">请修改答案后再次交卷，成绩保留最新一次。</p>
        </div>

        <p v-if="actionError" class="hint" data-testid="train-study-action-error" style="color: var(--red); margin-top: 8px">
          {{ actionError }}
        </p>
        <p v-if="notAssignee" style="margin-top: 8px">
          <router-link class="btn btn-sec btn-sm" to="/ims/workbench" data-testid="train-study-back-workbench">
            返回工作台
          </router-link>
        </p>
        <p v-if="confirmStatus === 'CONFIRMED'" class="hint ok-banner">
          学习已完成 · 已确认<span v-if="passedScore != null"> · 得分 {{ passedScore }}</span>
        </p>
      </div>
    </div>
    <div v-else class="empty"><div class="et">加载中…</div></div>

    <div v-if="showQuizConfirm" class="modal-mask" @click.self="showQuizConfirm = false">
      <div class="card" style="width: 360px; padding: 20px">
        <h3 style="margin: 0 0 8px">确认交卷</h3>
        <p class="hint">提交后将判分，未及格可重答</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end; gap: 8px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="busy" @click="showQuizConfirm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" :disabled="busy" @click="submitQuiz">确认交卷</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type QuizPublic = { question: string; options: string[] }

type TaskRow = {
  id: number
  taskNo: string
  taskName: string
  materialIds: number[]
  deadline: string
  confirmType: string
  passScore?: number
  quiz?: QuizPublic[]
}

type MatRow = {
  id: number
  title: string
  materialType: string
  fileKey?: string
  linkUrl?: string
  requiredMinutes?: number
}

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.taskId))
const task = ref<TaskRow | null>(null)
const materials = ref<MatRow[]>([])
const materialProgress = ref<Record<number, number>>({})
const materialSeconds = ref<Record<number, number>>({})
const progressPct = ref(0)
const studySeconds = ref(0)
const confirmStatus = ref<'NOT_CONFIRMED' | 'CONFIRMED'>('NOT_CONFIRMED')
const loadError = ref('')
const actionError = ref('')
const notAssignee = ref(false)
const gradeText = ref('')
const latestScore = ref<number | null>(null)
const passedScore = ref<number | null>(null)
const busy = ref(false)
const showQuizConfirm = ref(false)
const activeMaterialId = ref(0)
const answers = reactive<(number | null)[]>([])
const studying = ref(false)
const previewUrl = ref('')
const previewError = ref('')
const previewLoading = ref(false)
const previewMime = ref('')
const videoRef = ref<HTMLVideoElement | null>(null)
let previewBlob = ''

const confirmStatusLabel = computed(() =>
  confirmStatus.value === 'CONFIRMED' ? '已确认' : '未确认',
)

const studyHoursText = computed(() => {
  const minutes = Math.floor(studySeconds.value / 60)
  if (minutes <= 0) return '0 分钟'
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
})

function fmtBj(raw?: string) {
  if (!raw) return '—'
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(raw)) return raw
  const stamp = Date.parse(raw)
  if (Number.isNaN(stamp)) return raw.slice(0, 16).replace('T', ' ')
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(stamp))
  const pick = (type: string) => parts.find((part) => part.type === type)?.value || ''
  return `${pick('year')}-${pick('month')}-${pick('day')} ${pick('hour')}:${pick('minute')}`
}

const deadlineText = computed(() => fmtBj(task.value?.deadline))

const confirmTypeLabel = computed(() =>
  task.value?.confirmType === 'QUIZ' ? '自测问卷' : '学时达标',
)

const quiz = computed(() => task.value?.quiz ?? [])

const quizReady = computed(
  () =>
    quiz.value.length > 0 &&
    quiz.value.every((question, index) => question.options?.length > 0 && typeof answers[index] === 'number'),
)

const unansweredCount = computed(
  () => quiz.value.filter((question, index) => question.options?.length > 0 && typeof answers[index] !== 'number').length,
)

const mustAllCorrect = computed(() => {
  const paper = quiz.value
  const line = task.value?.passScore ?? 0
  return paper.length > 0 && line === 100
})

const overdueDays = computed(() => {
  if (!task.value || confirmStatus.value === 'CONFIRMED') return 0
  const deadline = new Date(task.value.deadline)
  if (Number.isNaN(deadline.getTime()) || Date.now() <= deadline.getTime()) return 0
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const today = fmt.format(new Date())
  const due = fmt.format(deadline)
  const [ty, tm, td] = today.split('-').map(Number)
  const [dy, dm, dd] = due.split('-').map(Number)
  const days = Math.round((Date.UTC(ty, tm - 1, td) - Date.UTC(dy, dm - 1, dd)) / 86400000)
  return days >= 1 ? days : 1
})

const activeMaterial = computed(
  () => materials.value.find((item) => item.id === activeMaterialId.value) || null,
)

const previewMode = computed(() => {
  const item = activeMaterial.value
  if (!item) return 'empty'
  if (item.materialType === 'LINK' && item.linkUrl) return 'link'
  if (item.materialType === 'VIDEO' || ['mp4', 'mov'].includes(fileExt(item.fileKey || ''))) return 'video'
  if (item.fileKey) return 'doc'
  return 'empty'
})

const docEmbeddable = computed(() => {
  const ext = fileExt(activeMaterial.value?.fileKey || '')
  return ext === 'pdf' || previewMime.value.includes('pdf')
})

const previewKey = computed(() => {
  const item = activeMaterial.value
  if (!item) return ''
  return `${item.id}:${item.materialType}:${item.fileKey || ''}:${item.linkUrl || ''}`
})

function fileExt(key: string) {
  const base = key.split('/').pop() || ''
  const dot = base.lastIndexOf('.')
  return dot >= 0 ? base.slice(dot + 1).toLowerCase() : ''
}

function materialKindLabel(item: MatRow) {
  if (item.materialType === 'VIDEO') return '视频'
  if (item.materialType === 'LINK') return '外链'
  return '文档'
}

function revokePreview() {
  if (previewBlob) URL.revokeObjectURL(previewBlob)
  previewBlob = ''
  previewUrl.value = ''
}

function learnedSeconds(id: number) {
  return materialSeconds.value[id] ?? 0
}

function learnedMinutes(id: number) {
  return Math.floor(learnedSeconds(id) / 60)
}

function needSeconds(id: number) {
  const mat = materials.value.find((item) => item.id === id)
  return Math.max(1, mat?.requiredMinutes || 1) * 60
}

const remainMinutes = computed(() => {
  const ids = task.value?.materialIds || []
  let remain = 0
  for (const id of ids) {
    const gap = needSeconds(id) - learnedSeconds(id)
    if (gap > 0) remain += gap
  }
  return remain <= 0 ? 0 : Math.ceil(remain / 60)
})

const hoursMet = computed(() => {
  const ids = task.value?.materialIds || []
  return ids.length > 0 && remainMinutes.value === 0 && hiddenMaterialCount.value === 0
})

const hiddenMaterialCount = computed(() => {
  const ids = task.value?.materialIds || []
  if (!ids.length) return 0
  const visible = new Set(materials.value.map((item) => item.id))
  return ids.filter((id) => !visible.has(id)).length
})

function isAssigneeDenial(err: unknown): boolean {
  return errorMessage(err).includes('仅被指派人')
}

function noteActionFailure(err: unknown, fallback: string) {
  const msg = errorMessage(err)
  if (isAssigneeDenial(err)) {
    notAssignee.value = true
    actionError.value = msg
    return
  }
  notAssignee.value = false
  actionError.value = msg === '加载失败' ? fallback : msg
}

function materialPct(id: number) {
  return materialProgress.value[id] ?? 0
}

function failGradeText(score: number, passScore: number) {
  return `得分 ${score}，及格 ${passScore}，未通过，可重答`
}

function startRetake() {
  actionError.value = ''
  answers.splice(0, answers.length, ...quiz.value.map(() => null))
}

function parseMatProgress(raw: Record<string, number> | undefined) {
  const out: Record<number, number> = {}
  if (!raw) return out
  for (const [k, v] of Object.entries(raw)) {
    out[Number(k)] = Number(v)
  }
  return out
}

async function loadTaskAndProgress() {
  loadError.value = ''
  notAssignee.value = false
  try {
    const res = await http.get(`/train/study/${taskId.value}`)
    const data = res.data.data || {}
    const found = data.task as TaskRow | undefined
    if (!found) {
      task.value = null
      loadError.value = '任务不存在或无权查看'
      return
    }
    task.value = found
    activeMaterialId.value = found.materialIds[0] ?? 0
    answers.splice(0, answers.length, ...((found.quiz || []).map(() => null)))
    materials.value = (data.materials || []) as MatRow[]

    const rec = data.progress
    if (rec) {
      materialProgress.value = parseMatProgress(rec.materialProgress)
      materialSeconds.value = parseMatProgress(rec.materialSeconds)
      progressPct.value = rec.progress ?? 0
      studySeconds.value = Number(rec.studySeconds || 0)
      confirmStatus.value = rec.confirmStatus === 'CONFIRMED' ? 'CONFIRMED' : 'NOT_CONFIRMED'
      if (rec.confirmStatus === 'CONFIRMED' && rec.confirmScore != null) {
        passedScore.value = rec.confirmScore
        latestScore.value = rec.confirmScore
      } else if (found.confirmType === 'QUIZ' && rec.confirmScore != null) {
        latestScore.value = rec.confirmScore
        gradeText.value = failGradeText(rec.confirmScore, found.passScore ?? 0)
      }
    }
  } catch (err) {
    task.value = null
    const msg = errorMessage(err)
    if (isAssigneeDenial(err)) {
      notAssignee.value = true
      loadError.value = msg
      return
    }
    notAssignee.value = false
    loadError.value = msg === '加载失败' ? '任务加载失败' : msg
  }
}

async function submitQuiz() {
  actionError.value = ''
  notAssignee.value = false
  gradeText.value = ''
  busy.value = true
  try {
    const res = await http.post(`/train/study/${taskId.value}/confirm`, {
      answers: quiz.value.map((_, index) => ({
        questionIndex: index,
        answerIndex: answers[index],
      })),
    })
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '交卷失败'
      return
    }
    const data = res.data.data || {}
    if (data.isPassed === false || data.confirmStatus !== 'CONFIRMED') {
      latestScore.value = data.confirmScore ?? null
      gradeText.value = failGradeText(data.confirmScore, data.passScore)
      confirmStatus.value = 'NOT_CONFIRMED'
      return
    }
    confirmStatus.value = 'CONFIRMED'
    passedScore.value = data.confirmScore ?? null
    latestScore.value = data.confirmScore ?? null
    progressPct.value = 100
    gradeText.value = ''
  } catch (err) {
    noteActionFailure(err, '交卷失败')
  } finally {
    busy.value = false
    showQuizConfirm.value = false
  }
}

function syncLocalProgress() {
  const ids = task.value?.materialIds || []
  const next: Record<number, number> = {}
  let sum = 0
  for (const id of ids) {
    const pct = Math.min(100, Math.floor((learnedSeconds(id) * 100) / needSeconds(id)))
    next[id] = pct
    sum += pct
  }
  materialProgress.value = next
  progressPct.value = ids.length ? Math.floor(sum / ids.length) : 0
  studySeconds.value = ids.reduce((acc, id) => acc + learnedSeconds(id), 0)
}

async function pushProgress(materialId: number, seconds: number) {
  try {
    const res = await http.put(`/train/study/${taskId.value}/progress`, {
      materialId,
      watchedSeconds: seconds,
      heartbeatAt: new Date().toISOString(),
    })
    const data = res.data.data || {}
    const serverSeconds = parseMatProgress(data.materialSeconds)
    const merged = { ...materialSeconds.value }
    for (const [key, value] of Object.entries(serverSeconds)) {
      merged[Number(key)] = Math.max(merged[Number(key)] || 0, value)
    }
    materialSeconds.value = merged
    syncLocalProgress()
  } catch (err) {
    noteActionFailure(err, '进度上报失败')
  }
}

let sinceBeat = 0
function onStudyTick() {
  if (!studying.value || !task.value || confirmStatus.value === 'CONFIRMED' || !activeMaterialId.value) return
  if (!materials.value.some((item) => item.id === activeMaterialId.value)) return
  const id = activeMaterialId.value
  materialSeconds.value = { ...materialSeconds.value, [id]: learnedSeconds(id) + 1 }
  syncLocalProgress()
  sinceBeat += 1
  if (sinceBeat >= 15) {
    sinceBeat = 0
    void pushProgress(id, learnedSeconds(id))
  }
}

function startStudy() {
  actionError.value = ''
  studying.value = true
  if (previewMode.value === 'video') void videoRef.value?.play()
}

function onVideoPlay() {
  studying.value = true
}

function onVideoPause() {
  studying.value = false
  sinceBeat = 0
  const id = activeMaterialId.value
  if (id) void pushProgress(id, learnedSeconds(id))
}

async function flushStudy() {
  const ids = materials.value.map((item) => item.id)
  for (const id of ids) {
    if (learnedSeconds(id) > 0) await pushProgress(id, learnedSeconds(id))
  }
}

async function loadPreview() {
  revokePreview()
  previewError.value = ''
  previewMime.value = ''
  const item = activeMaterial.value
  if (!item || (previewMode.value !== 'doc' && previewMode.value !== 'video') || !item.fileKey) {
    previewLoading.value = false
    return
  }
  previewLoading.value = true
  const key = previewKey.value
  try {
    const token = localStorage.getItem('ims_access')
    const res = await fetch(`/admin-api/ims/train/study/${taskId.value}/material/${item.id}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const mime = res.headers.get('content-type') || ''
    if (!res.ok || mime.includes('application/json')) {
      previewError.value = '资料文件暂不可预览'
      return
    }
    if (previewKey.value !== key) return
    const blob = await res.blob()
    previewMime.value = blob.type || mime
    previewBlob = URL.createObjectURL(blob)
    previewUrl.value = previewBlob
  } catch {
    if (previewKey.value === key) previewError.value = '资料文件暂不可预览'
  } finally {
    if (previewKey.value === key) previewLoading.value = false
  }
}

async function confirmComplete() {
  actionError.value = ''
  notAssignee.value = false
  busy.value = true
  try {
    await flushStudy()
    const res = await http.post(`/train/study/${taskId.value}/confirm`, {})
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '确认失败'
      return
    }
    confirmStatus.value = 'CONFIRMED'
    progressPct.value = 100
  } catch (err) {
    noteActionFailure(err, '确认失败')
  } finally {
    busy.value = false
  }
}

let tickHandle = 0
watch(previewKey, () => {
  void loadPreview()
})
onMounted(async () => {
  await loadTaskAndProgress()
  tickHandle = window.setInterval(onStudyTick, 1000)
})
onUnmounted(() => {
  window.clearInterval(tickHandle)
  if (studying.value) void flushStudy()
  revokePreview()
})
</script>

<style scoped>
.g2 {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.head {
  padding: 16px;
}
.meta {
  font-size: 13px;
  color: var(--text2);
  margin-top: 6px;
}
.mat-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 14px;
}
.mat-list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #eee);
  cursor: pointer;
}
.mat-list li.on {
  background: rgba(0, 0, 0, 0.04);
}
.stage {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border, #eee);
}
.stage-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.stage-body video,
.stage-body iframe,
.stage-body object {
  width: 100%;
  min-height: 320px;
  border: 0;
  background: #111;
}
.stage-body video {
  background: #000;
}
.ok {
  color: var(--green);
  font-weight: 600;
}
.pending {
  color: var(--orange, #e6a700);
}
.ok-banner {
  margin-top: 12px;
  color: var(--green);
  font-weight: 600;
}
.overdue-banner {
  margin: 8px 0 0;
  color: var(--red);
  font-size: 13px;
}
.quiz-paper {
  margin-top: 16px;
  padding-top: 8px;
  border-top: 1px solid var(--border, #eee);
}
.quiz-head {
  font-weight: 600;
  margin-bottom: 8px;
}
.quiz-q {
  margin: 12px 0;
}
.q-title {
  font-weight: 500;
  margin-bottom: 6px;
}
.opt {
  display: block;
  margin: 4px 0;
  cursor: pointer;
}
.grade-banner {
  margin-top: 8px;
  color: var(--red);
  font-weight: 600;
}
.score-empty {
  margin-top: 8px;
  color: var(--text2);
}
.overdue-banner {
  margin-top: 8px;
  color: var(--red);
  font-weight: 600;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
</style>
