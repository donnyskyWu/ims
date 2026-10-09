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

    <p v-if="loadError" class="hint" style="color: var(--red)">{{ loadError }}</p>
    <div v-else-if="task" class="g2">
      <div class="card head">
        <div style="font-weight: 600; font-size: 16px">{{ task.taskName }}</div>
        <div class="meta">编号 {{ task.taskNo }} · 截止 {{ task.deadline }} · {{ confirmTypeLabel }}</div>
        <p v-if="overdueDays > 0" class="hint overdue-banner" data-testid="train-study-overdue">
          本任务已逾期 {{ overdueDays }} 天，补学仍计入完成率统计
        </p>
        <div class="meta">
          总进度 <strong>{{ progressPct }}%</strong>
          · 确认状态
          <span :class="confirmStatus === 'CONFIRMED' ? 'ok' : 'pending'">{{ confirmStatusLabel }}</span>
        </div>
      </div>

      <div class="card" style="padding: 12px">
        <div style="font-weight: 600; margin-bottom: 8px">资料清单</div>
        <ul v-if="materials.length" class="mat-list">
          <li v-for="m in materials" :key="m.id">
            <span>{{ m.title }}</span>
            <span class="mono">{{ materialPct(m.id) }}%</span>
          </li>
        </ul>
        <div v-else class="empty"><div class="et">无关联资料</div></div>

        <div v-if="materials.length && confirmStatus !== 'CONFIRMED'" class="acts" style="margin-top: 16px; flex-wrap: wrap; gap: 8px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="busy" @click="markCurrentMaterialDone">
            标记当前资料已学完
          </button>
          <button
            v-if="task.confirmType !== 'QUIZ'"
            class="btn btn-pri btn-sm"
            type="button"
            :disabled="busy || !allMaterialsDone"
            :title="allMaterialsDone ? '' : '请先完成全部资料学习'"
            @click="confirmComplete"
          >
            完成确认
          </button>
        </div>

        <div v-if="task.confirmType === 'QUIZ' && confirmStatus !== 'CONFIRMED'" class="quiz-paper">
          <div class="quiz-head">自测问卷 · 及格 {{ task.passScore }} 分 · 共 {{ quiz.length }} 题</div>
          <p class="hint">全部题目必答。提交后将判分，未及格可重答，成绩保留最新一次。</p>
          <p v-if="mustAllCorrect" class="hint" data-testid="train-study-quiz-all-correct">须全部答对才能通过</p>
          <div v-if="!quiz.length" class="empty" data-testid="train-quiz-empty">
            <div class="et">问卷未配置，无法交卷</div>
            <div class="es">请联系培训负责人补全题目后再学习</div>
          </div>
          <p v-else-if="unansweredCount > 0" class="hint" data-testid="train-quiz-unanswered">
            还有 {{ unansweredCount }} 题未作答
          </p>
          <div v-for="(q, qi) in quiz" :key="qi" class="quiz-q">
            <div class="q-title">{{ qi + 1 }}. {{ q.question }}</div>
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
          <button
            class="btn btn-pri btn-sm"
            type="button"
            :disabled="busy || !quizReady"
            :title="quizReady ? '' : '请答完全部题目'"
            @click="showQuizConfirm = true"
          >
            提交问卷
          </button>
          <p v-if="gradeText" class="hint grade-banner" data-testid="train-quiz-grade">{{ gradeText }}</p>
          <p v-if="gradeText" class="hint">请修改答案后再次交卷，成绩保留最新一次。</p>
        </div>

        <p v-if="actionError" class="hint" style="color: var(--red); margin-top: 8px">{{ actionError }}</p>
        <p v-if="confirmStatus === 'CONFIRMED'" class="hint ok-banner">
          学习已完成 · CONFIRMED<span v-if="passedScore != null"> · 得分 {{ passedScore }}</span>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'
import { useUserStore } from '../../stores/user'

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

type MatRow = { id: number; title: string; materialType: string }

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.taskId))
const task = ref<TaskRow | null>(null)
const materials = ref<MatRow[]>([])
const materialProgress = ref<Record<number, number>>({})
const progressPct = ref(0)
const confirmStatus = ref<'NOT_CONFIRMED' | 'CONFIRMED'>('NOT_CONFIRMED')
const loadError = ref('')
const actionError = ref('')
const gradeText = ref('')
const passedScore = ref<number | null>(null)
const busy = ref(false)
const showQuizConfirm = ref(false)
const activeMaterialId = ref(0)
const answers = reactive<(number | null)[]>([])

const confirmStatusLabel = computed(() =>
  confirmStatus.value === 'CONFIRMED' ? '已确认' : '未确认',
)

const confirmTypeLabel = computed(() =>
  task.value?.confirmType === 'QUIZ' ? '自测问卷' : '学时达标',
)

const quiz = computed(() => task.value?.quiz ?? [])

const quizReady = computed(
  () => quiz.value.length > 0 && quiz.value.every((_, index) => typeof answers[index] === 'number'),
)

const unansweredCount = computed(
  () => quiz.value.filter((_, index) => typeof answers[index] !== 'number').length,
)

const mustAllCorrect = computed(() => {
  const paper = quiz.value
  const line = task.value?.passScore ?? 0
  return paper.length > 0 && line === paper.length
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

const allMaterialsDone = computed(() => {
  if (!task.value?.materialIds?.length) return false
  return task.value.materialIds.every((id) => (materialProgress.value[id] ?? 0) >= 100)
})

function materialPct(id: number) {
  return materialProgress.value[id] ?? 0
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
  const listRes = await http.get('/train/task/list', { params: { pageNo: 1, pageSize: 100 } })
  if (listRes.data.code !== 0) {
    loadError.value = listRes.data.msg || '任务加载失败'
    return
  }
  const found = (listRes.data.data.list || []).find((r: TaskRow) => r.id === taskId.value)
  if (!found) {
    loadError.value = '任务不存在或无权查看'
    return
  }
  task.value = found
  activeMaterialId.value = found.materialIds[0] ?? 0
  answers.splice(0, answers.length, ...((found.quiz || []).map(() => null)))

  const matRes = await http.get('/train/material/list', {
    params: { status: 'PUBLISHED', pageNo: 1, pageSize: 100 },
  })
  if (matRes.data.code === 0) {
    const ids = new Set(found.materialIds)
    materials.value = (matRes.data.data.list || []).filter((m: MatRow) => ids.has(m.id))
  }

  const userStore = useUserStore()
  const uid = Number(userStore.profile?.userId || 0)
  const recParams: Record<string, number> = { taskId: taskId.value, pageNo: 1, pageSize: 1 }
  if (uid > 0) recParams.userId = uid
  const recRes = await http.get('/train/task/records', { params: recParams })
  if (recRes.data.code === 0 && recRes.data.data.list?.length) {
    const rec = recRes.data.data.list[0]
    materialProgress.value = parseMatProgress(rec.materialProgress)
    progressPct.value = rec.progress ?? 0
    confirmStatus.value = rec.confirmStatus === 'CONFIRMED' ? 'CONFIRMED' : 'NOT_CONFIRMED'
    if (rec.confirmStatus === 'CONFIRMED' && rec.confirmScore != null) {
      passedScore.value = rec.confirmScore
    }
  }
}

async function submitQuiz() {
  actionError.value = ''
  gradeText.value = ''
  busy.value = true
  try {
    const res = await http.post(`/train/task/${taskId.value}/confirm`, {
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
      gradeText.value = `得分 ${data.confirmScore}，及格 ${data.passScore}，未通过，可重答`
      confirmStatus.value = 'NOT_CONFIRMED'
      return
    }
    confirmStatus.value = 'CONFIRMED'
    passedScore.value = data.confirmScore ?? null
    progressPct.value = 100
    gradeText.value = ''
  } catch {
    actionError.value = '网络错误'
  } finally {
    busy.value = false
    showQuizConfirm.value = false
  }
}

async function markCurrentMaterialDone() {
  if (!task.value || !activeMaterialId.value) return
  actionError.value = ''
  busy.value = true
  try {
    const res = await http.put(`/train/task/${taskId.value}/progress`, {
      materialId: activeMaterialId.value,
      currentPage: 1,
      totalPages: 1,
      watchedSeconds: 60,
      heartbeatAt: new Date().toISOString(),
    })
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '进度上报失败'
      return
    }
    const data = res.data.data
    materialProgress.value = parseMatProgress(data.materialProgress)
    progressPct.value = data.progress ?? progressPct.value
  } catch {
    actionError.value = '网络错误'
  } finally {
    busy.value = false
  }
}

async function confirmComplete() {
  actionError.value = ''
  busy.value = true
  try {
    const res = await http.post(`/train/task/${taskId.value}/confirm`, {})
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '确认失败'
      return
    }
    confirmStatus.value = 'CONFIRMED'
    progressPct.value = 100
  } catch {
    actionError.value = '网络错误'
  } finally {
    busy.value = false
  }
}

onMounted(loadTaskAndProgress)
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
  margin-top: 12px;
  color: var(--red);
  font-weight: 600;
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
