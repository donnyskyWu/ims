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
      <input v-model="filters.taskName" placeholder="任务名称" style="width: 140px" />
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="IN_PROGRESS">进行中</option>
        <option value="FINISHED">已结束</option>
      </select>
      <select v-model="filters.confirmType" style="width: 110px">
        <option value="">确认方式</option>
        <option value="DURATION">学时达标</option>
        <option value="QUIZ">自测问卷</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

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
              <td colspan="9"><div class="empty"><div class="et">{{ error || '暂无任务' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.taskNo }}</td>
              <td style="font-weight: 500">{{ row.taskName }}</td>
              <td class="num">{{ row.materialCount }}</td>
              <td class="num">{{ row.assignedCount }}</td>
              <td :style="{ color: finishColor(row.finishRate) }">{{ row.finishRate }}%</td>
              <td>{{ confirmLabel(row.confirmType) }}</td>
              <td class="mono">{{ row.deadline }}</td>
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
      <div class="card" style="width: 520px; padding: 20px; max-height: 85vh; overflow: auto">
        <h3 style="margin: 0 0 8px">学习记录 · {{ recordsTaskName }}</h3>
        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>进度</th>
              <th>确认状态</th>
              <th>得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="recordsLoading">
              <td colspan="4">加载中…</td>
            </tr>
            <tr v-else-if="!recordRows.length">
              <td colspan="4">暂无记录</td>
            </tr>
            <tr v-for="r in recordRows" v-else :key="r.userId">
              <td>{{ r.userName || r.userId }}</td>
              <td class="num">{{ r.progress }}%</td>
              <td>{{ r.confirmStatus }}</td>
              <td class="num">{{ r.confirmScore == null ? '—' : r.confirmScore }}</td>
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
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

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
const recordsTaskName = ref('')
const recordRows = ref<
  Array<{ userId: number; userName: string; progress: number; confirmStatus: string; confirmScore: number | null }>
>([])

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
  if (!form.quiz.length) return 'quiz 必填'
  for (const question of form.quiz) {
    if (!question.question.trim() || question.question.trim().length > 256) return '题目必填且不超过 256 字'
    const options = question.options.map((opt) => opt.trim())
    if (options.length < 2 || options.some((opt) => !opt)) return '每题选项至少 2 项'
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

async function openRecords(row: Row) {
  recordsTaskName.value = row.taskName
  showRecords.value = true
  recordsLoading.value = true
  recordRows.value = []
  try {
    const res = await http.get('/train/task/records', {
      params: { taskId: row.id, pageNo: 1, pageSize: 20 },
    })
    if (res.data.code === 0) {
      recordRows.value = res.data.data.list || []
    }
  } finally {
    recordsLoading.value = false
  }
}

function finishColor(rate: number) {
  if (rate >= 90) return 'var(--green)'
  if (rate >= 70) return 'var(--orange, #e6a700)'
  return 'var(--red)'
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
    if (filters.taskName) params.taskName = filters.taskName
    if (filters.status) params.status = filters.status
    if (filters.confirmType) params.confirmType = filters.confirmType
    const res = await http.get('/train/task/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
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
  if (!form.taskName.trim() || !materialIds.length || !userIds.length) {
    formError.value = '名称、资料与用户必填'
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
</style>
