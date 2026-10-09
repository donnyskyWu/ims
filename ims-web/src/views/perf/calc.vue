<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>绩效计算与核准</h1>
        <div class="sub">PERF-002 · 月度计算 → 人工补充 → 核准发布。分档为优秀 / 合格 / 待改进。</div>
      </div>
      <div class="acts">
        <label>
          周期
          <input v-model="period" data-testid="perf-period" type="month" @change="loadList" />
        </label>
        <button class="btn btn-sec btn-sm" type="button" data-testid="perf-run-open" @click="openRun">
          手动触发计算
        </button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="perf-approve-open" @click="openApprove">
          核准发布
        </button>
      </div>
    </div>

    <p v-if="error" data-testid="perf-calc-error" class="hint" style="color: var(--red)">{{ error }}</p>
    <p v-if="toast" data-testid="perf-calc-toast" class="hint">{{ toast }}</p>
    <div class="hint" data-testid="perf-status-bar" style="margin-bottom: 12px">
      计算中 {{ counts.CALCULATING }} | 待人工补充 {{ counts.PENDING_MANUAL }} | 待核准
      {{ counts.PENDING_APPROVE }} | 已发布 {{ counts.PUBLISHED }}
    </div>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>员工</th>
              <th>部门</th>
              <th>岗位</th>
              <th>综合得分</th>
              <th>分档</th>
              <th>部门排名</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8">
                <div class="empty" data-testid="perf-calc-empty">
                  <div class="et">本周期还没有计算结果</div>
                  <div class="es">每月 1 日自动计算上月，也可手动触发补算。第 23 周前无基线数据。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :data-testid="`perf-row-${row.userName}`">
              <td>{{ row.userName }}</td>
              <td>{{ row.deptName }}</td>
              <td class="mono">{{ row.positionCode }}</td>
              <td class="num">
                {{ scoreText(row.totalScore) }}
                <div
                  v-if="row.resultStatus === 'PENDING_MANUAL' && row.missingCount"
                  class="hint"
                  :data-testid="`perf-missing-hint-${row.userName}`"
                  :title="`含 ${row.missingCount} 项缺项按 0 分计入（PER-C-R1）`"
                >
                  含 {{ row.missingCount }} 项缺项按 0 分计入（PER-C-R1）
                </div>
              </td>
              <td>
                <span class="tag" :data-testid="`perf-grade-${row.userName}`">{{ gradeText(row.gradeLevel) }}</span>
              </td>
              <td class="num">{{ row.rankInDept ? `第 ${row.rankInDept} 名` : '—' }}</td>
              <td>
                <span class="tag" :data-testid="`perf-status-${row.userName}`">
                  {{ statusText(row.resultStatus) }}
                  <template v-if="row.resultStatus === 'PENDING_MANUAL'"> {{ row.missingCount }} 项</template>
                </span>
              </td>
              <td>
                <button
                  v-if="row.resultStatus === 'PENDING_MANUAL'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="perf-supplement"
                  @click="openManual(row)"
                >
                  补充
                </button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="perf-detail" @click="openDetail(row)">
                  详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="runOpen" title="手动触发计算" width="480px" @close="runOpen = false">
      <p class="hint">每月 1 日自动计算上月。此处为补算。第 23 周前返回 1156。</p>
      <div class="fld">
        <label>绩效月</label>
        <input v-model="runPeriod" data-testid="perf-run-period" type="month" />
      </div>
      <p v-if="runError" data-testid="perf-run-error" class="hint" style="color: var(--red)">{{ runError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="runOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="perf-run-confirm" @click="runCalc">开始计算</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="manualOpen" title="人工补充指标值" width="560px" @close="manualOpen = false">
      <p class="hint">{{ active?.userName }} · {{ active?.periodMonth }}。补充原因必填（1158）。</p>
      <div v-for="item in missingDetails" :key="item.metricId" class="fld">
        <label>{{ item.metricName }}</label>
        <input
          v-model="manualValue"
          data-testid="perf-manual-value"
          type="number"
          step="0.01"
        />
        <input
          v-model="manualReason"
          data-testid="perf-manual-reason"
          placeholder="补充原因（必填）"
          style="margin-top: 8px"
        />
        <p v-if="!manualReason.trim()" data-testid="perf-manual-hint" class="hint" style="color: var(--red)">
          补充原因必填（1158）
        </p>
      </div>
      <p v-if="manualError" data-testid="perf-manual-error" class="hint" style="color: var(--red)">{{ manualError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="manualOpen = false">取消</button>
        <button
          class="btn btn-pri"
          type="button"
          data-testid="perf-manual-save"
          :disabled="!manualReason.trim() || !missingDetails.length"
          @click="saveManual"
        >
          保存
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="approveOpen" title="核准发布" width="640px" @close="approveOpen = false">
      <p class="hint">
        待人工 {{ counts.PENDING_MANUAL }} 人默认排除。核准后员工可见本人明细，并生成排名与分档。
      </p>
      <p v-if="manualRows.length" class="hint" data-testid="perf-approve-manual-note">
        以下人员存在缺项，默认排除本次发布，补充后再发布。
      </p>
      <p v-else class="hint" data-testid="perf-approve-manual-empty">本周期没有待人工人员，可直接核准发布。</p>
      <div v-for="row in manualRows" :key="row.id" class="fld">
        <label>
          <input v-model="excluded[row.userId]" type="checkbox" :data-testid="`perf-exclude-${row.userName}`" />
          {{ row.userName }}（缺 {{ row.missingCount }} 项，默认不发布）
        </label>
      </div>
      <div class="fld">
        <label>审批意见</label>
        <textarea v-model="approveRemark" data-testid="perf-approve-remark" rows="3"></textarea>
      </div>
      <p v-if="!approveRemark.trim()" data-testid="perf-reject-hint" class="hint" style="color: var(--red)">
        驳回须填写审批意见
      </p>
      <p v-if="approveError" data-testid="perf-approve-error" class="hint" style="color: var(--red)">{{ approveError }}</p>
      <p v-if="approveResult" data-testid="perf-approve-result" class="hint">{{ approveResult }}</p>
      <template #foot>
        <button
          class="btn btn-sec"
          type="button"
          data-testid="perf-approve-reject"
          :disabled="!approveRemark.trim()"
          @click="submitApprove(false)"
        >
          驳回
        </button>
        <button class="btn btn-pri" type="button" data-testid="perf-approve-confirm" @click="submitApprove(true)">
          核准发布
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" :title="`结果详情 · ${active?.userName || ''}`" width="800px" @close="detailOpen = false">
      <p v-if="active?.resultStatus === 'PUBLISHED'" class="hint">
        本结果为不可变快照（V2-B4）。更正须 R4 审批后重算生成新版本，旧版本审计保留。
      </p>
      <p class="hint">
        引擎 {{ active?.calcSnapshot?.engineVersion || '—' }} · 取数
        {{ active?.calcSnapshot?.fetchTime || '—' }} · v{{ active?.version || 1 }}
      </p>
      <div v-if="active?.resultStatus === 'PUBLISHED'" class="acts" style="margin-bottom: 8px">
        <button class="btn btn-sec btn-sm" type="button" data-testid="perf-recalc" @click="recalc">申请重算</button>
      </div>
      <p v-if="tenureNote" data-testid="perf-tenure-note" class="hint">{{ tenureNote }}</p>
      <p v-if="active?.approveRemark" data-testid="perf-approve-remark-view" class="hint">
        审批意见：{{ active.approveRemark }}
      </p>
      <p v-if="lockError" data-testid="perf-lock-error" class="hint" style="color: var(--red)">{{ lockError }}</p>
      <table>
        <thead>
          <tr>
            <th>指标</th>
            <th>原始值</th>
            <th>得分</th>
            <th>权重</th>
            <th>取数</th>
            <th>贡献分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in active?.details || []" :key="item.metricCode">
            <td>{{ item.metricName }}</td>
            <td class="num">{{ item.metricValue ?? '—' }}</td>
            <td class="num">{{ scoreText(item.metricScore) }}</td>
            <td class="num">{{ item.weight }}%</td>
            <td>{{ dataStatusText(item.dataStatus) }}</td>
            <td class="num">{{ scoreText(item.contribution) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="hint">合计 {{ scoreText(active?.totalScore) }} = Σ(得分 × 权重)</p>
      <p v-if="active?.versionHistory?.length" class="hint">
        版本：
        <span v-for="item in active.versionHistory" :key="item.version">
          v{{ item.version }} {{ statusText(item.resultStatus) }}
        </span>
      </p>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http } from '../../api/http'

type Detail = {
  metricId: number
  metricCode: string
  metricName: string
  metricValue: number | string | null
  metricScore: number
  weight: number
  dataStatus: string
  contribution: number
}
type History = { version: number; resultStatus: string; totalScore: number | null; fetchTime: string }
type Row = {
  id: number
  periodMonth: string
  userId: number
  userName: string
  positionCode: string
  deptName: string
  totalScore: number | null
  rankInDept: number | null
  gradeLevel: string
  resultStatus: string
  missingCount: number
  version: number
  approveRemark?: string
  calcSnapshot?: { engineVersion?: string; fetchTime?: string; tenureRatio?: number }
  details?: Detail[]
  versionHistory?: History[]
}

const period = ref(previousMonth())
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const toast = ref('')
const runOpen = ref(false)
const runPeriod = ref(period.value)
const runError = ref('')
const manualOpen = ref(false)
const manualValue = ref('80')
const manualReason = ref('')
const manualError = ref('')
const approveOpen = ref(false)
const approveRemark = ref('')
const approveError = ref('')
const approveResult = ref('')
const excluded = reactive<Record<number, boolean>>({})
const detailOpen = ref(false)
const active = ref<Row | null>(null)
const lockError = ref('')

const counts = computed(() => {
  const bag = { CALCULATING: 0, PENDING_MANUAL: 0, PENDING_APPROVE: 0, PUBLISHED: 0 }
  for (const row of rows.value) {
    if (row.resultStatus in bag) bag[row.resultStatus as keyof typeof bag] += 1
  }
  return bag
})
const manualRows = computed(() => rows.value.filter((row) => row.resultStatus === 'PENDING_MANUAL'))
const missingDetails = computed(() => (active.value?.details || []).filter((item) => item.dataStatus === 'MISSING'))
const tenureNote = computed(() => {
  const ratio = active.value?.calcSnapshot?.tenureRatio
  if (ratio === undefined || ratio === null || Number(ratio) >= 1) return ''
  return `入职/离职当月按在职天数折算（PER-C-R2），折算比例 ${Number(ratio).toFixed(2)}`
})

function previousMonth() {
  const now = new Date()
  const cursor = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const month = String(cursor.getMonth() + 1).padStart(2, '0')
  return `${cursor.getFullYear()}-${month}`
}

function scoreText(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toFixed(2)
}

function gradeText(level: string) {
  if (level === 'EXCELLENT') return '优秀 ≥85'
  if (level === 'QUALIFIED') return '合格 60~84'
  if (level === 'IMPROVE') return '待改进 <60'
  return '—'
}

function dataStatusText(status: string) {
  if (status === 'AUTO') return '自动取数 AUTO'
  if (status === 'MANUAL') return '人工补充 MANUAL'
  if (status === 'MISSING') return '缺项 MISSING'
  if (status === 'EXAM') return '考试取数 EXAM'
  return status || '—'
}

function statusText(status: string) {
  if (status === 'CALCULATING') return '计算中'
  if (status === 'PENDING_MANUAL') return '待人工'
  if (status === 'PENDING_APPROVE') return '待核准'
  if (status === 'PUBLISHED') return '已发布'
  return status
}

function rejectText(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    if (body.code === 1156) return '1156 观察期不足：第 23 周前无基线数据'
    if (body.code === 1155) return '1155 绩效月数据已锁定，更正须运营总监审批并留痕（PER-C-R4）'
    if (body.code === 1001 && (body.msg || '').includes('审批意见')) return '1001 驳回须填写审批意见'
    return `${body.code ?? ''} ${body.msg || ''}`.trim()
  }
  return '请求失败'
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get(`/perf/calc/${period.value}`, { params: { pageNo: 1, pageSize: 100 } })
    rows.value = res.data.data.list || []
  } catch (err) {
    error.value = rejectText(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openRun() {
  runPeriod.value = period.value
  runError.value = ''
  toast.value = ''
  runOpen.value = true
}

async function runCalc() {
  runError.value = ''
  try {
    const res = await http.post('/perf/calc/run', { periodMonth: runPeriod.value })
    const data = res.data.data || {}
    toast.value = data.message || `已创建计算任务（${data.targetUserCount ?? 0} 人）`
    period.value = runPeriod.value
    runOpen.value = false
    await loadList()
  } catch (err) {
    runError.value = rejectText(err)
    error.value = runError.value
  }
}

function openManual(row: Row) {
  active.value = row
  manualValue.value = '80'
  manualReason.value = ''
  manualError.value = ''
  manualOpen.value = true
}

async function saveManual() {
  if (!active.value || !missingDetails.value.length) return
  manualError.value = ''
  const item = missingDetails.value[0]
  try {
    await http.put(`/perf/calc/detail/${active.value.id}/manual`, {
      metricId: item.metricId,
      manualValue: Number(manualValue.value),
      supplementReason: manualReason.value.trim(),
    })
    manualOpen.value = false
    toast.value = '缺项已补充'
    await loadList()
  } catch (err) {
    manualError.value = rejectText(err)
  }
}

function openApprove() {
  approveRemark.value = ''
  approveError.value = ''
  approveResult.value = ''
  for (const key of Object.keys(excluded)) delete excluded[Number(key)]
  for (const row of manualRows.value) excluded[row.userId] = true
  approveOpen.value = true
}

async function submitApprove(approve: boolean) {
  approveError.value = ''
  approveResult.value = ''
  const excludeUserIds = Object.entries(excluded)
    .filter(([, checked]) => checked)
    .map(([id]) => Number(id))
  try {
    const res = await http.put(`/perf/calc/${period.value}/approve`, {
      approve,
      remark: approveRemark.value.trim(),
      excludeUserIds,
    })
    const data = res.data.data || {}
    approveResult.value = approve
      ? `已发布 ${data.publishedCount} 人，${data.pendingManualCount} 人待人工补充`
      : '已驳回，结果回到计算中'
    toast.value = approveResult.value
    await loadList()
  } catch (err) {
    approveError.value = rejectText(err)
  }
}

function openDetail(row: Row) {
  active.value = row
  lockError.value = ''
  detailOpen.value = true
}

async function recalc() {
  lockError.value = ''
  if (!window.confirm('重算将生成新版本快照，原版本审计保留，确认？')) return
  try {
    const res = await http.post('/perf/calc/run', { periodMonth: period.value })
    toast.value = res.data.data?.message || '已创建计算任务'
    detailOpen.value = false
    await loadList()
  } catch (err) {
    lockError.value = rejectText(err)
    error.value = lockError.value
  }
}

void loadList()
</script>
