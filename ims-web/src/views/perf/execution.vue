<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>执行考核</h1>
        <div class="sub">FR-M3-002 · /ims/perf/execution · GET/POST /perf/execution · 05 PERF</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/perf/scheme">考核方案</router-link>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">创建考核</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      列表状态：草稿、计算中、已计算、已确认
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.evaluateeName" placeholder="被考核人" style="width: 110px" />
      <select v-model="filters.status" style="width: 120px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="CALCULATING">计算中</option>
        <option value="CALCULATED">已计算</option>
        <option value="CONFIRMED">已确认</option>
        <option value="ISSUED">已下发</option>
      </select>
      <select v-model="filters.periodType" style="width: 100px">
        <option value="">周期</option>
        <option value="MONTHLY">月度</option>
        <option value="QUARTERLY">季度</option>
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
              <th>单号</th>
              <th>被考核人</th>
              <th>岗位</th>
              <th>考核周期</th>
              <th>考核方案</th>
              <th>总分</th>
              <th>状态</th>
              <th>考核人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="perf-exec-empty"><div class="et">{{ emptyText }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue); font-size: 11px">{{ row.recordNo }}</td>
              <td style="font-weight: 500">{{ row.evaluateeName }}</td>
              <td>{{ row.position }}</td>
              <td class="num" style="font-size: 12px">{{ row.cycleDisplay }}</td>
              <td style="font-size: 12px; color: var(--text2)">{{ row.schemeName || '—' }}</td>
              <td class="num">{{ row.totalScore != null ? `${row.totalScore} 分` : '—' }}</td>
              <td><span class="tag" :style="statusStyle(row.status)"><span class="dot"></span>{{ statusLabel(row.status) }}</span></td>
              <td>{{ row.evaluatorName }}</td>
              <td>
                <span
                  v-if="row.status === 'DRAFT' || row.status === 'REJECTED'"
                  class="btn-txt btn"
                  @click="calculate(row)"
                >算分</span>
                <span
                  v-if="row.status === 'CALCULATED' || row.status === 'REVIEWED'"
                  class="btn-txt btn"
                  @click="openAdjust(row)"
                >调整</span>
                <span
                  v-if="row.status === 'CALCULATED' || row.status === 'REVIEWED'"
                  class="btn-txt btn"
                  data-testid="perf-exec-confirm"
                  @click="openConfirm(row)"
                >确认</span>
                <span
                  v-if="row.status === 'REVIEWED' || row.status === 'CONFIRMED'"
                  class="btn-txt btn"
                  data-testid="perf-exec-issue"
                  @click="openIssue(row)"
                >下发</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="confirmTarget" class="modal-mask" data-testid="perf-confirm-dialog" @click.self="confirmTarget = null">
      <div class="modal card" style="max-width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">确认结果</h3>
        <p data-testid="perf-confirm-score">综合得分 {{ confirmTarget.totalScore ?? '—' }}</p>
        <p data-testid="perf-confirm-grade">分档 {{ confirmTarget.gradeEdge || '—' }}</p>
        <p v-if="confirmTarget.grade === 'IMPROVE'" class="hint" data-testid="perf-confirm-alert" style="color: var(--red)">
          低于合格线，将触发预警
        </p>
        <p v-if="confirmError" class="hint" style="color: var(--red)">{{ confirmError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="confirmTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="perf-confirm-submit" @click="submitConfirm">
            确认结果
          </button>
        </div>
      </div>
    </div>

    <div v-if="issueTarget" class="modal-mask" data-testid="perf-issue-dialog" @click.self="issueTarget = null">
      <div class="modal card" style="max-width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">确认下发</h3>
        <p class="hint">下发后，被考核人可在「我的绩效」查看本期结果。未下发前不可见。</p>
        <p data-testid="perf-issue-score">综合得分 {{ issueTarget.totalScore ?? '—' }}</p>
        <p data-testid="perf-issue-grade">分档 {{ issueTarget.gradeEdge || '—' }}</p>
        <p v-if="issueError" class="hint" style="color: var(--red)">{{ issueError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="issueTarget = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="perf-issue-submit" @click="submitIssue">
            确认下发
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAdjust" class="modal-mask" @click.self="showAdjust = false">
      <div class="modal card" style="max-width: 760px; padding: 20px">
        <h3 style="margin: 0 0 12px">人工调整 · {{ adjustTarget?.recordNo }}</h3>
        <p class="hint">
          基础分 {{ adjustTarget?.calcBaseScore ?? adjustTarget?.totalScore }} · 综合分变动不能超过 ±20%。综合分 =
          Σ(自动得分 + 人工调整) × 权重。
        </p>
        <div class="tbl-wrap">
          <table data-testid="perf-adjust-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>权重</th>
                <th>原始值</th>
                <th>自动得分</th>
                <th>人工调整</th>
                <th>最终得分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in adjustLines" :key="line.metricName">
                <td>{{ line.metricName }}</td>
                <td class="num">{{ line.weight }}%</td>
                <td class="num">{{ line.rawValue }}</td>
                <td class="num">{{ line.autoScore }}</td>
                <td>
                  <input
                    v-model="line.manualAdjustment"
                    data-testid="perf-adjust-line"
                    type="number"
                    step="0.1"
                    style="width: 88px"
                  />
                </td>
                <td class="num">{{ lineFinal(line) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="hint" data-testid="perf-adjust-total">综合分 {{ adjustPreview }}</p>
        <div class="fld">
          <label>说明</label>
          <input v-model="adjustForm.remark" placeholder="场次补录等" />
        </div>
        <p v-if="adjustError" class="hint" data-testid="perf-adjust-error" style="color: var(--red)">{{ adjustError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showAdjust = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitAdjust">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 440px; padding: 20px">
        <h3 style="margin: 0 0 12px">创建考核</h3>
        <div class="fld"><label>考核方案 ID</label><input v-model.number="form.schemeId" type="number" min="1" /></div>
        <div class="fld"><label>被考核人用户 ID</label><input v-model.number="form.targetUserId" type="number" min="1" /></div>
        <div class="fld">
          <label>周期类型</label>
          <select v-model="form.periodType">
            <option value="MONTHLY">月度</option>
            <option value="QUARTERLY">季度</option>
          </select>
        </div>
        <div class="fld"><label>周期开始</label><input v-model="form.periodStart" placeholder="2026-07-01" /></div>
        <div class="fld"><label>周期结束</label><input v-model="form.periodEnd" placeholder="2026-09-30" /></div>
        <p v-if="formError" class="hint" data-testid="perf-exec-error" style="color: var(--red)">{{ stripReqCodes(formError) }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'

function stripReqCodes(text: string) {
  return text.replace(/[（(][^）)]*(?:BR|ADR)-[^）)]*[）)]/g, '').replace(/[ \t]{2,}/g, ' ').trim()
}

type ScoreLine = {
  metricName: string
  weight: number
  rawValue: number
  autoScore: number
  manualAdjustment: number | string
  finalScore: number
}
type Row = {
  id: number
  recordNo: string
  evaluateeName: string
  position: string
  cycleDisplay: string
  schemeName: string
  totalScore: number | null
  calcBaseScore?: number | null
  manualAdjustment?: number
  status: string
  evaluatorName: string
  grade?: string
  gradeEdge?: string
  lines?: ScoreLine[]
}

const route = useRoute()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const showAdjust = ref(false)
const confirmTarget = ref<Row | null>(null)
const confirmError = ref('')
const issueTarget = ref<Row | null>(null)
const issueError = ref('')
const adjustTarget = ref<Row | null>(null)
const adjustError = ref('')
const adjustLines = ref<ScoreLine[]>([])
const adjustForm = reactive({ remark: '' })
const formError = ref('')
const filters = reactive({ evaluateeName: '', status: '', periodType: '' })
const form = reactive({
  schemeId: 0,
  targetUserId: 1,
  periodType: 'QUARTERLY',
  periodStart: '2026-07-01',
  periodEnd: '2026-09-30',
})

const emptyText = computed(() => {
  if (error.value) return error.value
  const named = filters.evaluateeName.trim()
  const narrowed = !!(named || filters.status || filters.periodType)
  if (!narrowed) return '暂无考核单'
  if (filters.status === 'ISSUED' && !named) return '暂无已下发考核'
  if (filters.status === 'CONFIRMED' && !named) return '暂无已确认考核'
  return '没有符合筛选条件的考核单'
})

function statusLabel(status: string) {
  const map: Record<string, string> = {
    DRAFT: '草稿',
    CALCULATING: '计算中',
    CALCULATED: '已计算',
    REVIEWED: '已计算',
    CONFIRMED: '已确认',
    ISSUED: '已下发',
    REJECTED: '已驳回',
  }
  return map[status] || status
}

function statusStyle(status: string) {
  if (status === 'DRAFT') return { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
  if (status === 'CALCULATING') return { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
  if (status === 'CALCULATED' || status === 'REVIEWED') return { background: 'rgba(52,199,89,.12)', color: '#248a3d' }
  if (status === 'CONFIRMED') return { background: 'rgba(255,149,0,.12)', color: '#c46a00' }
  if (status === 'ISSUED') return { background: 'rgba(88,86,214,.12)', color: '#5856d6' }
  return { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.status) params.status = filters.status
    if (filters.periodType) params.periodType = filters.periodType
    const res = await http.get('/perf/execution/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    let list: Row[] = res.data.data.list || []
    const kw = filters.evaluateeName.trim()
    if (kw) list = list.filter((r) => r.evaluateeName.includes(kw))
    rows.value = list
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.evaluateeName = ''
  filters.status = ''
  filters.periodType = ''
  loadList()
}

function openCreate() {
  formError.value = ''
  showForm.value = true
}

async function submit() {
  formError.value = ''
  if (!form.schemeId || !form.targetUserId) {
    formError.value = '方案与被考核人必填'
    return
  }
  try {
    const res = await http.post('/perf/execution', {
      schemeId: form.schemeId,
      targetUserId: form.targetUserId,
      periodType: form.periodType,
      periodStart: form.periodStart,
      periodEnd: form.periodEnd,
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '创建失败'
      return
    }
    showForm.value = false
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    formError.value = body.msg || '创建失败'
  }
}

async function calculate(row: Row) {
  const res = await http.post(`/perf/execution/${row.id}/calculate`)
  if (res.data.code !== 0) {
    alert(res.data.msg || '算分失败')
    return
  }
  await loadList()
}

function openConfirm(row: Row) {
  confirmError.value = ''
  confirmTarget.value = row
}

async function submitConfirm() {
  if (!confirmTarget.value) return
  confirmError.value = ''
  try {
    const res = await http.post(`/perf/execution/${confirmTarget.value.id}/confirm`)
    if (res.data.code !== 0) {
      confirmError.value = res.data.msg || '确认失败'
      return
    }
    confirmTarget.value = null
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    confirmError.value = body.msg || '确认失败'
  }
}

function openIssue(row: Row) {
  issueError.value = ''
  issueTarget.value = row
}

async function submitIssue() {
  if (!issueTarget.value) return
  issueError.value = ''
  try {
    const res = await http.put(`/perf/execution/${issueTarget.value.id}/issue`)
    if (res.data.code !== 0) {
      issueError.value = res.data.msg || '下发失败'
      return
    }
    issueTarget.value = null
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    issueError.value = body.msg || '下发失败'
  }
}

function lineFinal(line: ScoreLine) {
  const delta = Number(line.manualAdjustment)
  const auto = Number(line.autoScore)
  if (!Number.isFinite(delta) || !Number.isFinite(auto)) return '—'
  return Math.round((auto + delta) * 100) / 100
}

const adjustPreview = computed(() => {
  let total = 0
  for (const line of adjustLines.value) {
    const finalScore = Number(lineFinal(line))
    const weight = Number(line.weight)
    if (!Number.isFinite(finalScore) || !Number.isFinite(weight)) continue
    total += (finalScore * weight) / 100
  }
  if (!adjustLines.value.length) return adjustTarget.value?.totalScore ?? '—'
  return Math.round(total * 10) / 10
})

function openAdjust(row: Row) {
  adjustTarget.value = row
  adjustForm.remark = ''
  adjustError.value = ''
  adjustLines.value = (row.lines || []).map((line) => ({
    ...line,
    manualAdjustment: line.manualAdjustment ?? 0,
  }))
  showAdjust.value = true
}

async function submitAdjust() {
  if (!adjustTarget.value) return
  adjustError.value = ''
  try {
    const res = await http.put(`/perf/execution/${adjustTarget.value.id}/adjust`, {
      lines: adjustLines.value.map((line) => ({
        metricName: line.metricName,
        manualAdjustment: Number(line.manualAdjustment),
      })),
      remark: adjustForm.remark,
    })
    if (res.data.code !== 0) {
      adjustError.value = res.data.msg || '调整失败'
      return
    }
    showAdjust.value = false
    await loadList()
  } catch (err) {
    const body = err as { msg?: string }
    adjustError.value = body.msg || '调整失败'
  }
}

watch(
  () => route.query.schemeId,
  (id) => {
    if (id) {
      form.schemeId = Number(id)
      showForm.value = true
    }
  },
  { immediate: true }
)

onMounted(loadList)
</script>
