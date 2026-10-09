<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>学习任务管理</h1>
        <div class="sub">TRAIN-002 · 资料多选 · DURATION/QUIZ · 02 TRAIN</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">下达学习任务</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      从已发布资料多选关联；按人指派；完成率 = 已完成人次 / 应完成人次（BR-102）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input
        v-model="filters.taskName"
        placeholder="任务名称"
        style="width: 140px"
        data-testid="train-task-filter-name"
      />
      <select v-model="filters.status" style="width: 100px" data-testid="train-task-filter-status">
        <option value="">全部状态</option>
        <option value="IN_PROGRESS">进行中</option>
        <option value="FINISHED">已结束</option>
      </select>
      <select v-model="filters.confirmType" style="width: 110px" data-testid="train-task-filter-confirm">
        <option value="">确认方式</option>
        <option value="DURATION">学时达标</option>
        <option value="QUIZ">自测问卷</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="train-task-filter-reset" @click="resetFilters">
        重置
      </button>
    </form>
    <p v-if="hasActiveFilters" class="filter-note" data-testid="train-task-filter-summary">
      当前筛选：{{ filterSummary }}
      <button type="button" class="linkish" @click="resetFilters">清除筛选</button>
    </p>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>任务名称</th>
              <th>资料数</th>
              <th>应完成</th>
              <th>完成率</th>
              <th>确认方式</th>
              <th>截止时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="train-task-empty">
                  <div class="et">{{ error || (hasActiveFilters ? '没有符合筛选的任务' : '暂无任务') }}</div>
                  <div v-if="!error && hasActiveFilters" class="es">调整任务名称、状态或确认方式后再查询</div>
                  <button
                    v-if="!error && hasActiveFilters"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="train-task-filter-clear-empty"
                    @click="resetFilters"
                  >
                    清除筛选
                  </button>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :class="{ 'due-soon': deadlineTone(row) === 'soon' }">
              <td class="mono">{{ row.taskNo }}</td>
              <td style="font-weight: 500">{{ row.taskName }}</td>
              <td class="num">{{ row.materialCount }}</td>
              <td class="num">{{ row.assignedCount }}</td>
              <td :style="{ color: finishColor(row.finishRate) }">{{ row.finishRate }}%</td>
              <td>{{ confirmLabel(row.confirmType) }}</td>
              <td
                class="mono"
                data-testid="train-task-deadline"
                :class="{ 'due-over': deadlineTone(row) === 'over' }"
              >
                {{ row.deadline }}
                <span v-if="deadlineTone(row) === 'soon'" class="tag due-tag" data-testid="train-task-due-soon">即将到期</span>
                <span v-else-if="deadlineTone(row) === 'over'" class="tag due-tag over" data-testid="train-task-overdue">已逾期</span>
              </td>
              <td>{{ row.status }}</td>
              <td>
                <button
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="train-task-edit"
                  :disabled="row.status !== 'IN_PROGRESS'"
                  :title="row.status === 'IN_PROGRESS' ? '截止前可编辑，已有学习记录不回滚' : '已过截止时间'"
                  @click="openEdit(row)"
                >
                  编辑
                </button>
                <button class="btn btn-sec btn-sm" type="button" @click="goStudy(row)">去学习</button>
                <button class="btn btn-sec btn-sm" type="button" @click="openRecords(row)">学习记录</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="hint" style="margin-top: 8px" data-testid="train-task-total">共 {{ total }} 条</div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 640px; padding: 20px; max-height: 90vh; overflow: auto">
        <h3 style="margin: 0 0 12px">{{ editingId ? '编辑学习任务' : '下达学习任务' }}</h3>
        <label class="fld">任务名称</label>
        <input v-model="form.taskName" class="fld-in" />
        <label class="fld">已发布资料（多选）</label>
        <div v-if="publishedMaterials.length" class="mat-pick">
          <label v-for="m in publishedMaterials" :key="m.id" class="mat-opt">
            <input v-model="form.materialIds" type="checkbox" :value="m.id" />
            {{ m.title }} <small class="mono">#{{ m.id }}</small>
          </label>
        </div>
        <p v-else class="hint">暂无已发布资料，请先在资料库发布</p>
        <label class="fld">指派用户 ID（逗号）</label>
        <input v-model="form.userIdsText" class="fld-in" placeholder="如 1" />
        <label class="fld">截止时间 ISO</label>
        <input v-model="form.deadline" class="fld-in" placeholder="2026-12-31T18:00:00+08:00" />
        <label class="fld">确认方式</label>
        <select v-model="form.confirmType" class="fld-in">
          <option value="DURATION">学时达标</option>
          <option value="QUIZ">自测问卷</option>
        </select>
        <div v-if="form.confirmType === 'QUIZ'" class="quiz-editor">
          <p class="hint">手工组卷：每题 1 分。及格分是需要答对的题数，不能超过题目数。</p>
          <label class="fld">及格分（答对题数）</label>
          <input v-model.number="form.passScore" class="fld-in" type="number" min="1" />
          <div v-for="(q, qi) in form.quiz" :key="qi" class="quiz-block" :data-qi="qi">
            <label class="fld">题目 {{ qi + 1 }}</label>
            <input v-model="q.question" class="fld-in" placeholder="请输入题目" />
            <div v-for="(opt, oi) in q.options" :key="oi" class="opt-row">
              <input v-model.number="q.answerIndex" type="radio" :name="'ans-' + qi" :value="oi" />
              <input v-model="q.options[oi]" class="fld-in" placeholder="选项内容" />
              <button
                v-if="q.options.length > 2"
                class="btn btn-sec btn-sm"
                type="button"
                @click="removeOption(qi, oi)"
              >
                删除选项
              </button>
            </div>
            <div class="acts" style="margin-top: 6px; gap: 8px">
              <button class="btn btn-sec btn-sm" type="button" @click="addOption(qi)">添加选项</button>
              <button v-if="form.quiz.length > 1" class="btn btn-sec btn-sm" type="button" @click="removeQuestion(qi)">
                删除题目
              </button>
            </div>
          </div>
          <button class="btn btn-sec btn-sm" type="button" style="margin-top: 8px" @click="addQuestion">添加题目</button>
          <p v-if="mustAnswerAll" class="hint" data-testid="train-quiz-all-correct">须全部答对才能通过</p>
        </div>
        <p v-if="editingId" class="hint">已产生的学习记录不会回滚。</p>
        <p v-if="formError" class="hint" style="color: var(--red)" data-testid="train-task-form-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showRecords" class="modal-mask" @click.self="showRecords = false">
      <div class="card" style="width: 640px; padding: 20px; max-height: 85vh; overflow: auto">
        <h3 style="margin: 0 0 8px">学习记录 · {{ recordsTaskName }}</h3>
        <form class="qbar" @submit.prevent="loadRecords">
          <select v-model="recordFilters.confirmStatus" data-testid="train-record-filter-status">
            <option value="">全部确认状态</option>
            <option value="NOT_CONFIRMED">未确认</option>
            <option value="CONFIRMED">已确认</option>
          </select>
          <label class="hint" style="display: flex; align-items: center; gap: 4px">
            <input v-model="recordFilters.overdueOnly" type="checkbox" data-testid="train-record-filter-overdue" />
            仅逾期
          </label>
          <button class="btn btn-pri btn-sm" type="submit" data-testid="train-record-query">筛选</button>
        </form>
        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>部门</th>
              <th>进度</th>
              <th>确认状态</th>
              <th>得分</th>
              <th>逾期</th>
              <th v-if="recordsConfirmType === 'QUIZ'">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="recordsLoading">
              <td :colspan="recordsColspan">加载中…</td>
            </tr>
            <tr v-else-if="!recordRows.length">
              <td :colspan="recordsColspan">
                <div class="empty" data-testid="train-record-empty">
                  <div class="et">{{ recordFilterOn ? '没有符合筛选的学习记录' : '暂无学习记录' }}</div>
                  <button
                    v-if="recordFilterOn"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="train-record-clear"
                    @click="clearRecordFilters"
                  >
                    清除筛选
                  </button>
                </div>
              </td>
            </tr>
            <tr v-for="r in recordRows" v-else :key="r.userId" data-testid="train-record-row">
              <td>{{ r.userName || r.userId }}</td>
              <td>{{ r.deptName || '未分配' }}</td>
              <td class="num">{{ r.progress }}%</td>
              <td>{{ r.confirmStatus }}</td>
              <td class="num">
                <span
                  v-if="recordsConfirmType === 'QUIZ' && r.confirmScore == null"
                  data-testid="train-record-score-empty"
                >暂无成绩</span>
                <template v-else>{{ r.confirmScore == null ? '—' : r.confirmScore }}</template>
              </td>
              <td>
                <span v-if="r.isOverdue" data-testid="train-record-overdue">已逾期 {{ r.overdueDays || '' }}天</span>
                <span v-else>—</span>
              </td>
              <td v-if="recordsConfirmType === 'QUIZ'">
                <button
                  v-if="r.confirmStatus !== 'CONFIRMED' && r.confirmScore != null && isSelfRecord(r.userId)"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="train-record-retake"
                  @click="goRetake"
                >
                  去重答
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" @click="showRecords = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const route = useRoute()

type Row = {
  id: number
  taskNo: string
  taskName: string
  materialIds?: number[]
  assignTargetUserIds?: number[]
  materialCount: number
  assignedCount: number
  finishRate: number
  confirmType: string
  deadline: string
  status: string
  passScore?: number
  quiz?: QuizDraft[]
}

const rows = ref<Row[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref(0)
const formError = ref('')
const filters = reactive({ taskName: '', status: '', confirmType: '' })
type MatPick = { id: number; title: string }
const publishedMaterials = ref<MatPick[]>([])
const showRecords = ref(false)
const recordsLoading = ref(false)
const recordsTaskId = ref(0)
const recordsTaskName = ref('')
const recordsConfirmType = ref('')
const recordFilters = reactive({ confirmStatus: '', overdueOnly: false })
const recordRows = ref<
  Array<{
    userId: number
    userName: string
    deptName: string
    progress: number
    confirmStatus: string
    confirmScore: number | null
    isOverdue: boolean
    overdueDays: number
  }>
>([])
const recordsColspan = computed(() => (recordsConfirmType.value === 'QUIZ' ? 7 : 6))
const userStore = useUserStore()

function isSelfRecord(userId: number) {
  const mine = Number(userStore.profile?.userId || 0)
  return mine > 0 && mine === Number(userId)
}

const hasActiveFilters = computed(
  () => Boolean(filters.taskName.trim() || filters.status || filters.confirmType),
)

const filterSummary = computed(() => {
  const parts: string[] = []
  if (filters.taskName.trim()) parts.push(`名称「${filters.taskName.trim()}」`)
  if (filters.status === 'IN_PROGRESS') parts.push('进行中')
  if (filters.status === 'FINISHED') parts.push('已结束')
  if (filters.confirmType === 'DURATION') parts.push('学时达标')
  if (filters.confirmType === 'QUIZ') parts.push('自测问卷')
  return parts.join(' · ')
})

const recordFilterOn = computed(() => Boolean(recordFilters.confirmStatus || recordFilters.overdueOnly))

const mustAnswerAll = computed(
  () => form.confirmType === 'QUIZ' && form.quiz.length > 0 && form.passScore === form.quiz.length,
)

type QuizDraft = { question: string; options: string[]; answerIndex: number }

function blankQuestion(): QuizDraft {
  return { question: '', options: ['', ''], answerIndex: 0 }
}

const form = reactive({
  taskName: '',
  materialIds: [] as number[],
  userIdsText: '1',
  deadline: '2026-12-31T18:00:00+08:00',
  confirmType: 'DURATION',
  passScore: 1,
  quiz: [blankQuestion()] as QuizDraft[],
})

function confirmLabel(value: string) {
  if (value === 'QUIZ') return '自测问卷'
  if (value === 'DURATION') return '学时达标'
  return value
}

function addQuestion() {
  form.quiz.push(blankQuestion())
}

function removeQuestion(index: number) {
  if (form.quiz.length <= 1) return
  form.quiz.splice(index, 1)
  if (form.passScore > form.quiz.length) form.passScore = form.quiz.length
}

function addOption(questionIndex: number) {
  form.quiz[questionIndex].options.push('')
}

function removeOption(questionIndex: number, optionIndex: number) {
  const question = form.quiz[questionIndex]
  if (question.options.length <= 2) return
  question.options.splice(optionIndex, 1)
  if (question.answerIndex >= question.options.length) question.answerIndex = 0
}

function quizError(): string {
  if (!form.quiz.length) return '请至少添加 1 道题目'
  const seen = new Set<string>()
  for (const question of form.quiz) {
    const title = question.question.trim()
    if (!title || title.length > 256) return '题目必填且不超过 256 字'
    if (seen.has(title)) return '题目不能重复'
    seen.add(title)
    const options = question.options.map((opt) => opt.trim())
    if (options.length < 2) return '每题选项至少 2 项'
    if (options.some((opt) => !opt)) return '选项内容不能为空'
    if (new Set(options).size !== options.length) return '选项内容不能重复'
    if (question.answerIndex < 0 || question.answerIndex >= options.length) return '请设定正确答案'
  }
  if (!form.passScore || form.passScore < 1 || form.passScore > form.quiz.length) {
    return '及格分须在 1 到题目数之间'
  }
  return ''
}

function defaultDeadline() {
  const d = new Date()
  d.setMonth(d.getMonth() + 3)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T18:00:00+08:00`
}

async function loadPublishedMaterials() {
  const res = await http.get('/train/material/list', {
    params: { status: 'PUBLISHED', pageNo: 1, pageSize: 50 },
  })
  if (res.data.code === 0) {
    publishedMaterials.value = (res.data.data.list || []).map((m: MatPick) => ({
      id: m.id,
      title: m.title,
    }))
  }
}

function goStudy(row: Row) {
  router.push(`/ims/train/study/${row.id}`)
}

function goRetake() {
  const id = recordsTaskId.value
  showRecords.value = false
  if (id) router.push(`/ims/train/study/${id}`)
}

async function loadRecords() {
  if (!recordsTaskId.value) return
  recordsLoading.value = true
  recordRows.value = []
  try {
    const params: Record<string, string | number | boolean> = {
      taskId: recordsTaskId.value,
      pageNo: 1,
      pageSize: 20,
    }
    if (recordFilters.confirmStatus) params.confirmStatus = recordFilters.confirmStatus
    if (recordFilters.overdueOnly) params.overdue = true
    const res = await http.get('/train/task/records', { params })
    if (res.data.code === 0) {
      recordRows.value = res.data.data.list || []
    }
  } finally {
    recordsLoading.value = false
  }
}

function clearRecordFilters() {
  recordFilters.confirmStatus = ''
  recordFilters.overdueOnly = false
  void loadRecords()
}

async function openRecords(row: Row) {
  recordsTaskId.value = row.id
  recordsTaskName.value = row.taskName
  recordsConfirmType.value = row.confirmType
  recordFilters.confirmStatus = ''
  recordFilters.overdueOnly = false
  showRecords.value = true
  await loadRecords()
}

function resetFilters() {
  filters.taskName = ''
  filters.status = ''
  filters.confirmType = ''
  void loadList()
}

function finishColor(rate: number) {
  if (rate >= 90) return 'var(--green)'
  if (rate >= 70) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

function deadlineTone(row: Row): 'soon' | 'over' | '' {
  const ts = Date.parse(row.deadline || '')
  if (Number.isNaN(ts)) return ''
  const delta = ts - Date.now()
  if (delta < 0) return 'over'
  if (row.status === 'IN_PROGRESS' && delta <= 24 * 60 * 60 * 1000) return 'soon'
  return ''
}

function deadlineFormatError(raw: string): string {
  const text = raw.trim()
  if (!text) return '截止时间必填'
  const iso = /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?)?$/
  if (!iso.test(text)) return '截止时间格式无效'
  const stamp = Date.parse(text.includes(' ') ? text.replace(' ', 'T') : text)
  if (!Number.isFinite(stamp)) return '截止时间格式无效'
  return ''
}

function parseIds(text: string): number[] {
  return text
    .split(/[,，\s]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n > 0)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 30 }
    const name = filters.taskName.trim()
    if (name) params.taskName = name
    if (filters.status) params.status = filters.status
    if (filters.confirmType) params.confirmType = filters.confirmType
    const res = await http.get('/train/task/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch {
    error.value = '网络错误'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function openEdit(row: Row) {
  if (row.status !== 'IN_PROGRESS') return
  editingId.value = row.id
  form.taskName = row.taskName
  form.materialIds = [...(row.materialIds || [])]
  form.userIdsText = (row.assignTargetUserIds && row.assignTargetUserIds.length
    ? row.assignTargetUserIds
    : [1]
  ).join(',')
  form.deadline = row.deadline || defaultDeadline()
  form.confirmType = row.confirmType || 'DURATION'
  form.passScore = row.passScore || 1
  form.quiz =
    row.quiz && row.quiz.length
      ? row.quiz.map((question) => ({
          question: question.question,
          options: [...(question.options || ['', ''])],
          answerIndex: question.answerIndex || 0,
        }))
      : [blankQuestion()]
  formError.value = ''
  void loadPublishedMaterials()
  showForm.value = true
}

function openCreate() {
  editingId.value = 0
  form.taskName = ''
  form.materialIds = []
  form.userIdsText = '1'
  form.deadline = defaultDeadline()
  form.confirmType = 'DURATION'
  form.passScore = 1
  form.quiz = [blankQuestion()]
  formError.value = ''
  void loadPublishedMaterials()
  showForm.value = true
}

async function submit() {
  formError.value = ''
  const materialIds = [...form.materialIds]
  const userIds = parseIds(form.userIdsText)
  if (!form.taskName.trim()) {
    formError.value = '任务名称必填'
    return
  }
  if (!materialIds.length) {
    formError.value = '请选择已发布资料'
    return
  }
  if (!form.userIdsText.trim()) {
    formError.value = '请填写指派用户'
    return
  }
  if (!userIds.length) {
    formError.value = '指派用户 ID 无效'
    return
  }
  const deadlineBad = deadlineFormatError(form.deadline)
  if (deadlineBad) {
    formError.value = deadlineBad
    return
  }
  if (form.taskName.trim().length > 128) {
    formError.value = '任务名称不超过 128 字'
    return
  }
  const payload: Record<string, unknown> = {
    taskName: form.taskName.trim(),
    materialIds,
    assignScope: 'BY_USER',
    assignTargetUserIds: userIds,
    deadline: form.deadline,
    confirmType: form.confirmType,
  }
  if (form.confirmType === 'QUIZ') {
    const invalid = quizError()
    if (invalid) {
      formError.value = invalid
      return
    }
    payload.passScore = form.passScore
    payload.quiz = form.quiz.map((question) => ({
      question: question.question.trim(),
      options: question.options.map((opt) => opt.trim()),
      answerIndex: question.answerIndex,
    }))
  }
  let res
  try {
    res = editingId.value
      ? await http.put(`/train/task/${editingId.value}`, payload)
      : await http.post('/train/task', payload)
  } catch (err) {
    formError.value = errorMessage(err)
    return
  }
  if (res.data.code !== 0) {
    formError.value = res.data.msg || `失败 (${res.data.code})`
    return
  }
  showForm.value = false
  editingId.value = 0
  await loadList()
}

onMounted(async () => {
  await loadList()
  const rawId = route.query.taskId
  const taskId = Number(Array.isArray(rawId) ? rawId[0] : rawId)
  if (!taskId) return
  const rawName = route.query.taskName
  const taskName = String(Array.isArray(rawName) ? rawName[0] : rawName || '')
  const hit = rows.value.find((row) => row.id === taskId)
  await openRecords(hit || { id: taskId, taskName: taskName || `任务#${taskId}` } as Row)
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.mat-pick {
  max-height: 160px;
  overflow: auto;
  border: 1px solid var(--border, #ddd);
  padding: 8px;
  border-radius: 4px;
}
.mat-opt {
  display: block;
  font-size: 13px;
  margin: 4px 0;
  cursor: pointer;
}
.quiz-editor {
  margin-top: 8px;
}
.quiz-block {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid var(--border, #ddd);
  border-radius: 4px;
}
.opt-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.opt-row .fld-in {
  flex: 1;
}
.filter-note {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -6px 0 12px;
  font-size: 12px;
  color: var(--text2);
}
.linkish {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}
tr.due-soon {
  background: rgba(230, 167, 0, 0.16);
}
.due-over {
  color: var(--red);
}
.due-tag {
  margin-left: 6px;
  background: rgba(230, 167, 0, 0.22);
  color: #8a6500;
}
.due-tag.over {
  background: rgba(255, 59, 48, 0.12);
  color: var(--red);
}
</style>
