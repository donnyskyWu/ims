<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>在线考试</h1>
        <div class="sub">PERF-003 · 随机组卷与补考</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">创建试卷</button>
      </div>
    </div>
    <div class="cattabs">
      <button type="button" class="cattab" :class="{ on: tab === 'bank' }" @click="tab = 'bank'">题库管理</button>
      <button type="button" class="cattab" :class="{ on: tab === 'paper' }" @click="showPapers">试卷管理</button>
      <button type="button" class="cattab" :class="{ on: tab === 'score' }" @click="showScores">成绩管理</button>
    </div>

    <template v-if="tab === 'bank'">
      <form class="qbar" @submit.prevent="loadList">
        <input v-model="filters.questionNo" placeholder="题目编号" style="width: 110px" />
        <input v-model="filters.stemKeyword" placeholder="题干关键词" style="width: 150px" />
        <select v-model="filters.knowledgeDomain" style="width: 110px">
          <option value="">全部知识域</option>
          <option v-for="d in domains" :key="d.value" :value="d.value">{{ d.label }}</option>
        </select>
        <select v-model="filters.questionType" style="width: 90px">
          <option value="">全部题型</option>
          <option v-for="t in qtypes" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
        <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>题目编号</th>
                <th>题干</th>
                <th>知识域</th>
                <th>题型</th>
                <th>分值</th>
                <th>被引用</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!rows.length">
                <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无题目' }}</div></div></td>
              </tr>
              <tr v-for="row in rows" v-else :key="row.id">
                <td class="mono num" style="color: var(--blue)">{{ row.questionNo }}</td>
                <td style="font-weight: 500; max-width: 340px">{{ row.stem }}</td>
                <td>
                  <span class="tag" style="background: rgba(142, 142, 147, 0.12); color: #6d6d72">
                    <span class="dot"></span>{{ row.knowledgeDomainLabel }}
                  </span>
                </td>
                <td>
                  <span class="tag" :style="typeStyle(row.questionType)">
                    <span class="dot"></span>{{ row.questionTypeLabel }}
                  </span>
                </td>
                <td class="num">{{ row.score }} 分</td>
                <td class="num">{{ row.refCount }} 卷</td>
                <td><span class="btn btn-sec btn-sm" style="pointer-events: none; opacity: 0.5">编辑</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="total > 0" class="pager">
          <span class="pg-total">共 {{ total }} 条</span>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'paper'">
      <form class="qbar" @submit.prevent="loadPapers">
        <input v-model="paperName" placeholder="试卷名称" style="width: 180px" />
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <p v-if="assignNotice" class="hint" data-testid="exam-assign-notice">{{ assignNotice }}</p>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>试卷编号</th>
                <th>名称</th>
                <th>组卷方式</th>
                <th>总分/及格线</th>
                <th>限时</th>
                <th>状态</th>
                <th>指派人数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="paperLoading">
                <td colspan="8">加载中</td>
              </tr>
              <tr v-else-if="!papers.length">
                <td colspan="8">{{ paperError || '暂无试卷' }}</td>
              </tr>
              <tr v-for="row in papers" v-else :key="row.id">
                <td class="mono num" style="color: var(--blue)">{{ row.paperNo }}</td>
                <td>{{ row.paperName }}</td>
                <td>{{ row.paperType === 'RANDOM' ? '随机组卷' : '固定卷' }}</td>
                <td class="num">{{ row.totalScore }} / {{ row.passScore }}</td>
                <td class="num">{{ row.durationMinutes }} 分钟</td>
                <td>{{ row.status === 'PUBLISHED' ? '已发布' : '草稿' }}</td>
                <td class="num">{{ row.assignedCount }}</td>
                <td>
                  <button v-if="row.status === 'DRAFT'" class="btn btn-sec btn-sm" type="button" @click="askPublish(row)">
                    发布
                  </button>
                  <button
                    v-if="row.status === 'PUBLISHED'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    @click="openAssign(row)"
                  >
                    指派考生
                  </button>
                  <button
                    v-if="row.status === 'PUBLISHED' && row.assignedCount > 0"
                    class="btn btn-pri btn-sm"
                    type="button"
                    @click="startTake(row)"
                  >
                    考生作答
                  </button>
                  <button class="btn btn-sec btn-sm" type="button" @click="jumpScores(row)">成绩</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else>
      <form class="qbar" @submit.prevent="loadScores">
        <select v-model="scoreFilter.paperId" style="width: 220px">
          <option value="">全部试卷</option>
          <option v-for="p in papers" :key="p.id" :value="String(p.id)">{{ p.paperName }}</option>
        </select>
        <input
          v-model="scoreFilter.userKeyword"
          placeholder="考生姓名/工号"
          style="width: 140px"
          data-testid="exam-score-user"
        />
        <select v-model="scoreFilter.examStatus" style="width: 120px">
          <option value="">全部状态</option>
          <option value="NOT_STARTED">未开始</option>
          <option value="IN_PROGRESS">进行中</option>
          <option value="SUBMITTED">已交卷</option>
          <option value="GRADED">已判分</option>
          <option value="MAKEUP_EXAM">补考</option>
        </select>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>考生</th>
                <th>试卷</th>
                <th>总分</th>
                <th>切屏</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="scoreLoading">
                <td colspan="6">加载中</td>
              </tr>
              <tr v-else-if="!scores.length">
                <td colspan="6">{{ scoreError || '暂无成绩' }}</td>
              </tr>
              <tr v-for="row in scores" v-else :key="row.id" data-testid="exam-score-row">
                <td>
                  <span
                    v-if="row.isMakeup"
                    class="tag"
                    style="background: rgba(255, 149, 0, 0.15); color: #c46a00; margin-right: 6px"
                  >
                    补考
                  </span>
                  {{ row.userName }}
                </td>
                <td>{{ row.paperName }}</td>
                <td class="num" data-testid="exam-score-total">{{ scoreText(row) }}</td>
                <td
                  class="num"
                  :class="{ 'switch-hot': row.switchScreenCount >= 3 }"
                  :title="row.switchScreenCount >= 3 ? '切屏 ≥3 次强制交卷，按已答计分（PER-E-R1）' : ''"
                >
                  {{ row.switchScreenCount }}
                </td>
                <td>
                  {{ statusLabel(row.examStatus) }}
                  <span
                    v-if="row.gradeOverdue"
                    class="tag tag-overdue"
                    data-testid="exam-grade-overdue"
                  >
                    超时待阅
                  </span>
                </td>
                <td>
                  <button
                    v-if="row.canGrade"
                    class="btn btn-pri btn-sm"
                    type="button"
                    data-testid="exam-grade-open"
                    @click="openGrade(row)"
                  >
                    阅卷
                  </button>
                  <span v-else>—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card compose" style="width: 760px; padding: 20px; max-height: 88vh; overflow: auto">
        <h3 style="margin: 0 0 8px">创建试卷</h3>
        <p class="hint">抽题按知识域和题型，同一题不重复计入。契约没有难度字段。</p>
        <label class="fld">试卷名称</label>
        <input v-model="form.paperName" class="fld-in" placeholder="如 10 月合规抽测" />
        <label class="fld">组卷方式</label>
        <div class="type-picks">
          <label><input v-model="form.paperType" type="radio" value="FIXED" /> 固定卷</label>
          <label><input v-model="form.paperType" type="radio" value="RANDOM" /> 随机组卷</label>
        </div>
        <div class="grid3">
          <div>
            <label class="fld">总分</label>
            <input v-model.number="form.totalScore" class="fld-in" type="number" min="1" aria-label="总分" />
          </div>
          <div>
            <label class="fld">及格分</label>
            <input v-model.number="form.passScore" class="fld-in" type="number" min="0" aria-label="及格分" />
          </div>
          <div>
            <label class="fld">限时（分钟）</label>
            <input v-model.number="form.durationMinutes" class="fld-in" type="number" min="1" />
          </div>
        </div>

        <div v-if="form.paperType === 'FIXED'" class="pick-list">
          <label v-for="q in bank" :key="q.id" class="mat-opt">
            <input v-model="form.questionIds" type="checkbox" :value="q.id" />
            <span class="mono">{{ q.questionNo }}</span>
            {{ q.stem }}
            <small>{{ q.score }} 分</small>
          </label>
        </div>

        <div v-else>
          <div v-for="(row, index) in form.strategy" :key="index" class="strategy-row">
            <select v-model="row.knowledgeDomain" @change="refreshStock(row)">
              <option v-for="d in domains" :key="d.value" :value="d.value">{{ d.label }}</option>
            </select>
            <select v-model="row.questionType" @change="refreshStock(row)">
              <option v-for="t in qtypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
            <input v-model.number="row.count" type="number" min="1" aria-label="抽题数" />
            <input v-model.number="row.scorePerQuestion" type="number" min="1" aria-label="每题分值" />
            <span class="num">小计 {{ lineSubtotal(row) }}</span>
            <button v-if="form.strategy.length > 1" class="btn btn-sec btn-sm" type="button" @click="form.strategy.splice(index, 1)">
              删除
            </button>
            <p v-if="stockError(row, index)" class="hint stock-err">{{ stockError(row, index) }}</p>
          </div>
          <button class="btn btn-sec btn-sm" type="button" @click="addStrategy">添加策略行</button>
        </div>

        <p class="sum-line" :class="{ bad: totalMismatch }">Σ = {{ sigma }} 分<span v-if="totalMismatch">，与总分 {{ form.totalScore }} 不一致（1159）</span></p>
        <p v-if="formError" class="hint stock-err">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" :disabled="saveBlocked" @click="savePaper">保存试卷</button>
        </div>
      </div>
    </div>

    <div v-if="publishTarget" class="modal-mask">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 8px">确认发布</h3>
        <p>发布后不可修改题目结构，考生将按窗口作答。</p>
        <div class="acts" style="justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="publishTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="publishPaper">确认发布</button>
        </div>
      </div>
    </div>

    <div v-if="assignTarget" class="modal-mask" @click.self="assignTarget = null">
      <div class="card" style="width: 460px; padding: 20px">
        <h3 style="margin: 0 0 8px">指派考生</h3>
        <p class="hint">{{ assignTarget.paperName }} · 仅窗口内可开考（1161）</p>
        <label class="fld">考生用户 ID</label>
        <input v-model="assignForm.userIdsText" class="fld-in" />
        <label class="fld">窗口开始</label>
        <input v-model="assignForm.from" class="fld-in" type="datetime-local" />
        <label class="fld">窗口结束</label>
        <input v-model="assignForm.to" class="fld-in" type="datetime-local" />
        <p v-if="assignError" class="hint stock-err">{{ assignError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="assignTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitAssign">确认指派</button>
        </div>
      </div>
    </div>

    <div v-if="taking" class="modal-mask">
      <div class="card" style="width: 640px; padding: 20px; max-height: 88vh; overflow: auto">
        <h3 style="margin: 0 0 8px">在线作答 · {{ taking.paperName }}</h3>
        <p class="hint">及格 {{ taking.passScore }} 分 · {{ taking.examStatus }}</p>
        <template v-if="takePhase === 'answer'">
          <div v-for="q in taking.questions" :key="q.questionId" class="quiz-q">
            <div class="q-title">{{ q.content }} <small>{{ q.score }} 分</small></div>
            <textarea
              v-if="isEssay(q)"
              v-model="essayAnswers[q.questionId]"
              class="fld-in"
              rows="3"
              :aria-label="q.content"
              placeholder="简答"
            />
            <template v-else>
              <label v-for="(opt, oi) in q.options || []" :key="oi" class="opt">
                <input
                  v-model.number="answers[q.questionId]"
                  type="radio"
                  :name="'q-' + q.questionId"
                  :value="oi"
                />
                {{ opt }}
              </label>
            </template>
          </div>
          <p v-if="takeError" class="hint stock-err">{{ takeError }}</p>
          <div class="acts" style="justify-content: flex-end">
            <button class="btn btn-sec btn-sm" type="button" @click="taking = null">关闭</button>
            <button class="btn btn-pri btn-sm" type="button" @click="askSubmit">交卷</button>
          </div>
        </template>
        <template v-else-if="takePhase === 'confirm'">
          <p>确认交卷后将按已答题目判分。</p>
          <div class="acts" style="justify-content: flex-end">
            <button class="btn btn-sec btn-sm" type="button" @click="takePhase = 'answer'">继续作答</button>
            <button class="btn btn-pri btn-sm" type="button" @click="submitPaper">确认交卷</button>
          </div>
        </template>
        <template v-else>
          <p v-if="taking.examStatus === 'SUBMITTED'" data-testid="exam-pending-grade">
            客观 {{ pendingObjective ?? 0 }} · 待阅（48 小时内）
          </p>
          <p v-if="resultText">{{ resultText }}</p>
          <p v-if="taking.examStatus === 'MAKEUP_EXAM'">补考成绩 {{ resultScore }}，已覆盖原成绩 · MAKEUP_EXAM</p>
          <div class="acts" style="justify-content: flex-end">
            <button v-if="canMakeup" class="btn btn-pri btn-sm" type="button" @click="takePhase = 'makeup'">申请补考</button>
            <button class="btn btn-sec btn-sm" type="button" @click="finishTake">查看成绩</button>
          </div>
        </template>
      </div>
    </div>

    <div v-if="grading" class="modal-mask" data-testid="exam-grade-drawer">
      <div class="card" style="width: 640px; padding: 20px; max-height: 88vh; overflow: auto">
        <h3 style="margin: 0 0 8px">阅卷 · {{ grading.userName }}</h3>
        <p class="hint">{{ grading.paperName }} · 客观得分 {{ grading.objectiveScore ?? 0 }}</p>
        <p class="hint">阅卷成绩将自动计入「考试成绩」类绩效指标取数（PER-E-R4）。主观题须 48 小时内完成。</p>
        <div v-for="item in grading.subjectiveItems || []" :key="item.questionId" class="quiz-q">
          <div class="q-title">{{ item.content }} <small>满分 {{ item.maxScore }}</small></div>
          <p>考生作答：{{ item.answer || '（未作答）' }}</p>
          <p v-if="item.reference" class="hint">参考答案：{{ item.reference }}</p>
          <label class="fld">评分</label>
          <input
            v-model.number="gradeScores[item.questionId]"
            class="fld-in"
            type="number"
            min="0"
            :max="item.maxScore"
            :aria-label="`评分 ${item.content}`"
          />
          <label class="fld">评语</label>
          <input v-model="gradeComments[item.questionId]" class="fld-in" placeholder="可选" />
        </div>
        <p v-if="gradeError" class="hint stock-err">{{ gradeError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="grading = null">取消</button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="exam-grade-submit"
            :disabled="gradeSaving"
            @click="submitGrade"
          >
            提交阅卷
          </button>
        </div>
      </div>
    </div>

    <div v-if="takePhase === 'makeup' && taking" class="modal-mask">
      <div class="card" style="width: 440px; padding: 20px">
        <h3 style="margin: 0 0 8px">确认补考</h3>
        <p>补考仅一次，新成绩将覆盖原成绩（PER-E-R3）。</p>
        <div class="acts" style="justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="takePhase = 'result'">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="applyMakeup">确认补考</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type BankRow = {
  id: string
  questionNo: string
  stem: string
  knowledgeDomain: string
  knowledgeDomainLabel: string
  questionType: string
  questionTypeLabel: string
  score: number
  refCount: number
}

type Strategy = { knowledgeDomain: string; questionType: string; count: number; scorePerQuestion: number }

type Paper = {
  id: number
  paperNo: string
  paperName: string
  paperType: string
  totalScore: number
  passScore: number
  durationMinutes: number
  status: string
  assignedCount: number
}

type SubjectiveItem = {
  questionId: number
  content: string
  maxScore: number
  answer: string
  reference?: string
}

type ScoreRow = {
  id: number
  paperId: number
  paperName: string
  userName: string
  score: number | null
  objectiveScore: number | null
  subjectiveScore: number | null
  switchScreenCount: number
  examStatus: string
  isMakeup: boolean
  gradeOverdue?: boolean
  canGrade?: boolean
  subjectiveItems?: SubjectiveItem[]
}

type QuestionSnap = { questionId: number; questionType: string; content: string; options?: string[]; score: number }

const domains = [
  { value: 'LIVE_RULE', label: '直播规范' },
  { value: 'CONTENT_SKILL', label: '内容技能' },
  { value: 'LIVE_SKILL', label: '直播技能' },
  { value: 'DATA_SKILL', label: '数据技能' },
  { value: 'COMPLIANCE', label: '制度合规' },
]
const qtypes = [
  { value: 'SINGLE', label: '单选' },
  { value: 'MULTIPLE', label: '多选' },
  { value: 'JUDGE', label: '判断' },
  { value: 'ESSAY', label: '简答' },
]

const user = useUserStore()
const tab = ref<'bank' | 'paper' | 'score'>('bank')
const rows = ref<BankRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const filters = reactive({ questionNo: '', stemKeyword: '', knowledgeDomain: '', questionType: '' })
const bank = ref<BankRow[]>([])
const stockCache = reactive<Record<string, number>>({})
const stockLoading = ref(false)

const papers = ref<Paper[]>([])
const paperLoading = ref(false)
const paperError = ref('')
const paperName = ref('')
const showForm = ref(false)
const formError = ref('')
const saving = ref(false)
const publishTarget = ref<Paper | null>(null)
const assignTarget = ref<Paper | null>(null)
const assignError = ref('')
const assignNotice = ref('')
const assignForm = reactive({ userIdsText: '', from: '', to: '' })

const scores = ref<ScoreRow[]>([])
const scoreLoading = ref(false)
const scoreError = ref('')
const scoreFilter = reactive({ paperId: '', examStatus: '', userKeyword: '' })
const grading = ref<ScoreRow | null>(null)
const gradeScores = reactive<Record<number, number>>({})
const gradeComments = reactive<Record<number, string>>({})
const gradeError = ref('')
const gradeSaving = ref(false)

const taking = ref<{
  recordId: number
  paperId: number
  paperName: string
  passScore: number
  examStatus: string
  questions: QuestionSnap[]
} | null>(null)
const answers = reactive<Record<number, number>>({})
const essayAnswers = reactive<Record<number, string>>({})
const takePhase = ref<'answer' | 'confirm' | 'result' | 'makeup'>('answer')
const takeError = ref('')
const resultScore = ref<number | null>(null)
const pendingObjective = ref<number | null>(null)

function isEssay(q: QuestionSnap) {
  return q.questionType === 'ESSAY' || q.questionType === 'SHORT_ANSWER'
}

function scoreText(row: ScoreRow) {
  if (row.examStatus === 'SUBMITTED' && row.subjectiveScore == null) {
    return `客观 ${row.objectiveScore ?? 0} · 待阅`
  }
  return row.score == null ? '—' : String(row.score)
}

function blankStrategy(): Strategy {
  return { knowledgeDomain: 'LIVE_RULE', questionType: 'SINGLE', count: 1, scorePerQuestion: 10 }
}

const form = reactive({
  paperName: '',
  paperType: 'RANDOM' as 'FIXED' | 'RANDOM',
  questionIds: [] as string[],
  strategy: [blankStrategy()] as Strategy[],
  totalScore: 10,
  passScore: 6,
  durationMinutes: 30,
})

function typeStyle(qtype: string) {
  const map: Record<string, string> = {
    SINGLE: 'background:rgba(0,113,227,.12);color:#0071e3',
    MULTIPLE: 'background:rgba(175,82,218,.12);color:#8944ab',
    JUDGE: 'background:rgba(90,200,250,.12);color:#0e7fb8',
    ESSAY: 'background:rgba(255,149,0,.12);color:#c46a00',
  }
  return map[qtype] || map.SINGLE
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    NOT_STARTED: '未开始',
    IN_PROGRESS: '进行中',
    SUBMITTED: '已交卷',
    GRADED: '已判分',
    MAKEUP_EXAM: '补考',
  }
  return map[status] || status
}

function lineSubtotal(row: Strategy) {
  return (Number(row.count) || 0) * (Number(row.scorePerQuestion) || 0)
}

const sigma = computed(() => {
  if (form.paperType === 'FIXED') {
    const picked = new Set(form.questionIds)
    return bank.value.filter((q) => picked.has(q.id)).reduce((sum, q) => sum + Number(q.score || 0), 0)
  }
  return form.strategy.reduce((sum, row) => sum + lineSubtotal(row), 0)
})

const totalMismatch = computed(() => Number(form.totalScore) !== sigma.value)

function reservedBefore(index: number, row: Strategy) {
  let used = 0
  for (let i = 0; i < index; i++) {
    const prev = form.strategy[i]
    if (prev.knowledgeDomain === row.knowledgeDomain && prev.questionType === row.questionType) {
      used += Number(prev.count) || 0
    }
  }
  return used
}

function stockError(row: Strategy, index: number) {
  const key = `${row.knowledgeDomain}|${row.questionType}`
  if (!(key in stockCache)) return ''
  const available = stockCache[key] - reservedBefore(index, row)
  if ((Number(row.count) || 0) > available) return `题库存量仅 ${Math.max(available, 0)} 题`
  return ''
}

const saveBlocked = computed(() => {
  if (saving.value || stockLoading.value) return true
  if (!form.paperName.trim()) return true
  if (form.paperType === 'RANDOM' && form.strategy.some((row, index) => stockError(row, index))) return true
  if (form.paperType === 'FIXED' && !form.questionIds.length) return true
  if (totalMismatch.value) return true
  if (!form.passScore && form.passScore !== 0) return true
  if (form.passScore > form.totalScore) return true
  return false
})

const canMakeup = computed(() => {
  if (!taking.value || resultScore.value == null) return false
  return taking.value.examStatus === 'GRADED' && resultScore.value < taking.value.passScore
})

const resultText = computed(() => {
  if (!taking.value || resultScore.value == null) return ''
  if (taking.value.examStatus === 'MAKEUP_EXAM') return ''
  const passed = resultScore.value >= taking.value.passScore
  return passed
    ? `得分 ${resultScore.value}，及格 ${taking.value.passScore}，已通过`
    : `得分 ${resultScore.value}，及格 ${taking.value.passScore}，未通过`
})

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.questionNo) params.questionNo = filters.questionNo
    if (filters.stemKeyword) params.stemKeyword = filters.stemKeyword
    if (filters.knowledgeDomain) params.knowledgeDomain = filters.knowledgeDomain
    if (filters.questionType) params.questionType = filters.questionType
    const res = await http.get('/perf/exam/questions', { params })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.questionNo = ''
  filters.stemKeyword = ''
  filters.knowledgeDomain = ''
  filters.questionType = ''
  loadList()
}

async function loadBank() {
  const res = await http.get('/perf/exam/questions', { params: { pageNo: 1, pageSize: 100 } })
  bank.value = res.data.data.list || []
}

async function refreshStock(row: Strategy) {
  const key = `${row.knowledgeDomain}|${row.questionType}`
  stockLoading.value = true
  try {
    const res = await http.get('/perf/exam/questions', {
      params: { pageNo: 1, pageSize: 1, knowledgeDomain: row.knowledgeDomain, questionType: row.questionType },
    })
    stockCache[key] = res.data.data.total || 0
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    stockLoading.value = false
  }
}

function addStrategy() {
  const row = blankStrategy()
  form.strategy.push(row)
  refreshStock(row)
}

function openCreate() {
  tab.value = 'paper'
  form.paperName = ''
  form.paperType = 'RANDOM'
  form.questionIds = []
  form.strategy = [blankStrategy()]
  form.totalScore = 10
  form.passScore = 6
  form.durationMinutes = 30
  formError.value = ''
  showForm.value = true
  loadBank().catch((e: unknown) => {
    formError.value = errorMessage(e)
  })
  refreshStock(form.strategy[0])
  if (!papers.value.length) loadPapers()
}

async function savePaper() {
  formError.value = ''
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      paperName: form.paperName.trim(),
      paperType: form.paperType,
      totalScore: Number(form.totalScore),
      passScore: Number(form.passScore),
      durationMinutes: Number(form.durationMinutes),
    }
    if (form.paperType === 'FIXED') {
      payload.questionIds = form.questionIds.map((id) => Number(id))
    } else {
      payload.strategy = form.strategy.map((row) => ({
        knowledgeDomain: row.knowledgeDomain,
        questionType: row.questionType,
        count: Number(row.count),
        scorePerQuestion: Number(row.scorePerQuestion),
      }))
    }
    await http.post('/perf/exam/paper', payload)
    showForm.value = false
    await loadPapers()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function loadPapers() {
  paperLoading.value = true
  paperError.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 50 }
    if (paperName.value.trim()) params.paperName = paperName.value.trim()
    const res = await http.get('/perf/exam/paper', { params })
    papers.value = res.data.data.list || []
  } catch (e: unknown) {
    paperError.value = errorMessage(e)
    papers.value = []
  } finally {
    paperLoading.value = false
  }
}

function showPapers() {
  tab.value = 'paper'
  loadPapers()
}

function askPublish(row: Paper) {
  publishTarget.value = row
}

async function publishPaper() {
  if (!publishTarget.value) return
  try {
    await http.put(`/perf/exam/paper/${publishTarget.value.id}/publish`)
    publishTarget.value = null
    await loadPapers()
  } catch (e: unknown) {
    paperError.value = errorMessage(e)
    publishTarget.value = null
  }
}

function localInput(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function openAssign(row: Paper) {
  assignTarget.value = row
  assignError.value = ''
  assignForm.userIdsText = user.profile?.userId || '1'
  const now = new Date()
  assignForm.from = localInput(new Date(now.getTime() - 5 * 60 * 1000))
  assignForm.to = localInput(new Date(now.getTime() + 24 * 60 * 60 * 1000))
}

async function submitAssign() {
  if (!assignTarget.value) return
  assignError.value = ''
  const userIds = assignForm.userIdsText
    .split(/[,，\s]+/)
    .map((item) => Number(item))
    .filter((item) => item > 0)
  try {
    const res = await http.post(`/perf/exam/paper/${assignTarget.value.id}/assign`, {
      userIds,
      examWindow: { from: new Date(assignForm.from).toISOString(), to: new Date(assignForm.to).toISOString() },
    })
    const count = res.data.data?.assignedCount ?? userIds.length
    assignNotice.value = `已指派 ${count} 人，考生工作台已收到考试待办`
    assignTarget.value = null
    await loadPapers()
  } catch (e: unknown) {
    assignError.value = errorMessage(e)
  }
}

function clearAnswers() {
  for (const key of Object.keys(answers)) delete answers[Number(key)]
  for (const key of Object.keys(essayAnswers)) delete essayAnswers[Number(key)]
}

async function startTake(row: Paper) {
  takeError.value = ''
  resultScore.value = null
  pendingObjective.value = null
  clearAnswers()
  try {
    const res = await http.post('/perf/exam/record/start', { paperId: row.id })
    const data = res.data.data
    taking.value = {
      recordId: data.id,
      paperId: row.id,
      paperName: data.paperName || row.paperName,
      passScore: row.passScore,
      examStatus: data.examStatus,
      questions: data.questions || [],
    }
    takePhase.value = 'answer'
  } catch (e: unknown) {
    const body = e as { code?: number; data?: { id?: number; questions?: QuestionSnap[]; examStatus?: string; paperName?: string } }
    if (body?.code === 1162 && body.data?.questions) {
      taking.value = {
        recordId: Number(body.data.id),
        paperId: row.id,
        paperName: body.data.paperName || row.paperName,
        passScore: row.passScore,
        examStatus: body.data.examStatus || 'IN_PROGRESS',
        questions: body.data.questions,
      }
      takePhase.value = 'answer'
      return
    }
    paperError.value = errorMessage(e)
  }
}

function askSubmit() {
  if (!taking.value) return
  const missing = taking.value.questions.some((q) => {
    if (isEssay(q)) return !(essayAnswers[q.questionId] || '').trim()
    return answers[q.questionId] === undefined
  })
  if (missing) {
    takeError.value = '请答完所有题目'
    return
  }
  takeError.value = ''
  takePhase.value = 'confirm'
}

async function submitPaper() {
  if (!taking.value) return
  takeError.value = ''
  try {
    const res = await http.post('/perf/exam/record/submit', {
      recordId: taking.value.recordId,
      switchScreenCount: 0,
      answers: taking.value.questions.map((q) => ({
        questionId: q.questionId,
        answer: isEssay(q) ? (essayAnswers[q.questionId] || '').trim() : answers[q.questionId],
      })),
    })
    const data = res.data.data
    resultScore.value = data.totalScore
    pendingObjective.value = data.examStatus === 'SUBMITTED' ? data.objectiveScore : null
    taking.value.examStatus = data.examStatus
    takePhase.value = 'result'
  } catch (e: unknown) {
    takeError.value = errorMessage(e)
    takePhase.value = 'answer'
  }
}

async function applyMakeup() {
  if (!taking.value) return
  takeError.value = ''
  clearAnswers()
  try {
    const res = await http.post('/perf/exam/record/start', { paperId: taking.value.paperId })
    const data = res.data.data
    taking.value.recordId = data.id
    taking.value.examStatus = data.examStatus
    taking.value.questions = data.questions || []
    resultScore.value = null
    pendingObjective.value = null
    takePhase.value = 'answer'
  } catch (e: unknown) {
    takeError.value = errorMessage(e)
    takePhase.value = 'result'
  }
}

function finishTake() {
  const paperId = taking.value?.paperId
  taking.value = null
  takePhase.value = 'answer'
  if (paperId) scoreFilter.paperId = String(paperId)
  showScores()
}

async function loadScores() {
  scoreLoading.value = true
  scoreError.value = ''
  try {
    if (!papers.value.length) await loadPapers()
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 50 }
    if (scoreFilter.paperId) params.paperId = Number(scoreFilter.paperId)
    if (scoreFilter.userKeyword.trim()) params.userKeyword = scoreFilter.userKeyword.trim()
    if (scoreFilter.examStatus) params.examStatus = scoreFilter.examStatus
    const res = await http.get('/perf/exam/record/scores', { params })
    scores.value = res.data.data.list || []
  } catch (e: unknown) {
    scoreError.value = errorMessage(e)
    scores.value = []
  } finally {
    scoreLoading.value = false
  }
}

function showScores() {
  tab.value = 'score'
  loadScores()
}

function jumpScores(row: Paper) {
  scoreFilter.paperId = String(row.id)
  showScores()
}

function openGrade(row: ScoreRow) {
  grading.value = row
  gradeError.value = ''
  for (const key of Object.keys(gradeScores)) delete gradeScores[Number(key)]
  for (const key of Object.keys(gradeComments)) delete gradeComments[Number(key)]
  for (const item of row.subjectiveItems || []) {
    gradeScores[item.questionId] = 0
    gradeComments[item.questionId] = ''
  }
}

async function submitGrade() {
  if (!grading.value) return
  gradeError.value = ''
  gradeSaving.value = true
  try {
    await http.put(`/perf/exam/record/${grading.value.id}/grade`, {
      gradings: (grading.value.subjectiveItems || []).map((item) => ({
        questionId: item.questionId,
        score: Number(gradeScores[item.questionId]),
        comment: (gradeComments[item.questionId] || '').trim() || undefined,
      })),
    })
    grading.value = null
    await loadScores()
  } catch (e: unknown) {
    gradeError.value = errorMessage(e)
  } finally {
    gradeSaving.value = false
  }
}

onMounted(loadList)
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
.grid3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.type-picks {
  display: flex;
  gap: 16px;
  font-size: 13px;
}
.pick-list {
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--line, #ddd);
  border-radius: 4px;
  padding: 8px;
  margin-top: 8px;
}
.mat-opt {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  margin: 4px 0;
}
.strategy-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}
.strategy-row input[type='number'] {
  width: 80px;
}
.stock-err {
  color: var(--red, #d92d20);
  width: 100%;
}
.sum-line {
  margin-top: 10px;
  font-weight: 600;
}
.sum-line.bad {
  color: var(--red, #d92d20);
}
.quiz-q {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--line, #eee);
}
.opt {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 6px;
}
.switch-hot {
  color: #d92d20;
  font-weight: 700;
}
.tag-overdue {
  margin-left: 6px;
  background: rgba(255, 149, 0, 0.18);
  color: #c46a00;
}
</style>
