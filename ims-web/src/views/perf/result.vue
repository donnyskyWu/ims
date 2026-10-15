<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>考核结果</h1>
        <div class="sub">FR-M3-003 · GET /perf/result/list · GET /perf/result/export · 05 PERF</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="perf-result-export" @click="exportCsv">导出 CSV</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/perf/execution">执行考核</router-link>
      </div>
    </div>
    <p class="hint">仅展示 CALCULATED 及以上态；草稿/算分中仍留在执行考核页。导出只含已确认、已下发。</p>
    <p v-if="exportNote" class="hint" data-testid="perf-result-export-note">{{ exportNote }}</p>

    <section data-testid="perf-rank-board" style="margin-bottom: 16px">
      <div class="pg-h" style="margin-bottom: 8px">
        <div>
          <div class="sub">PERF-004 排名区 · {{ gradeLine }}</div>
          <p class="hint">V2 排名不含竞品分析维度。</p>
        </div>
        <div class="acts">
          <label>
            排名周期
            <input v-model="rankPeriod" data-testid="perf-rank-period" type="month" @change="onRankPeriod" />
          </label>
          <select
            v-if="depts.length"
            v-model="rankDept"
            data-testid="perf-rank-dept"
            style="width: 140px"
            @change="loadRank"
          >
            <option value="">全部部门</option>
            <option v-for="dept in depts" :key="dept.deptId" :value="String(dept.deptId)">{{ dept.deptName }}</option>
          </select>
        </div>
      </div>
      <p v-if="rankEmpty" class="empty" data-testid="perf-rank-empty"><span class="et">{{ rankEmpty }}</span></p>
      <template v-else>
        <div class="g3">
          <div class="card stat" data-testid="perf-rank-top3" style="border-left: 3px solid var(--green)">
            <span class="l">绩效红榜 TOP3</span>
            <div style="margin-top: 8px">
              <span
                v-for="row in top3"
                :key="`${row.userId}-${row.boardRank}`"
                class="tag"
                :data-testid="`perf-rank-top-${row.userName}`"
                style="margin-right: 6px"
              >
                {{ medalText(row.medal, row.boardRank) }} {{ row.userName }} {{ scoreText(row.totalScore) }}
              </span>
              <span v-if="!top3.length">—</span>
            </div>
          </div>
          <div class="card stat" data-testid="perf-rank-tail" style="border-left: 3px solid var(--red)">
            <span class="l">末位预警</span>
            <div style="margin-top: 8px">
              <span v-if="!tail.length" data-testid="perf-rank-tail-clear">本期没有低于 60 分的员工</span>
              <span
                v-for="row in tail"
                :key="row.userId"
                class="tag"
                :data-testid="`perf-rank-tail-${row.userName}`"
                style="margin-right: 6px; color: var(--red)"
              >
                {{ row.userName }} {{ scoreText(row.totalScore) }} 待改进 &lt;60
              </span>
            </div>
            <p class="hint" data-testid="perf-rank-pip">{{ pipStub }}</p>
          </div>
          <div class="card stat" data-testid="perf-rank-avg">
            <span class="l">部门均分</span>
            <div class="n" data-testid="perf-rank-avg-value">{{ deptAverage == null ? '—' : scoreText(deptAverage) }}</div>
            <div class="hint">{{ deptAverageText }}</div>
          </div>
        </div>
        <div v-if="rankRows.length" class="tbl-block" style="margin-top: 12px">
          <div class="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>排名</th>
                  <th>员工</th>
                  <th>部门</th>
                  <th>综合得分</th>
                  <th>分档</th>
                  <th>预警</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rankRows" :key="row.id" data-testid="perf-rank-row">
                  <td class="num">{{ medalText('', row.rankNo) }}</td>
                  <td>{{ row.userName }}</td>
                  <td>{{ row.deptName }}</td>
                  <td class="num" :style="row.totalScore < 60 ? { color: 'var(--red)' } : undefined">
                    {{ scoreText(row.totalScore) }}
                  </td>
                  <td><span class="tag">{{ gradeText(row.gradeLevel) }}</span></td>
                  <td>{{ row.alertStatus === 'ALERTED' ? '已预警' : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </section>

    <form class="qbar" @submit.prevent="loadList">
      <select v-model="filters.status" data-testid="perf-result-status" style="width: 130px">
        <option value="">全部可阅态</option>
        <option value="CONFIRMED">已确认</option>
        <option value="ISSUED">已下发</option>
      </select>
      <select v-model="filters.periodType" data-testid="perf-result-period" style="width: 110px">
        <option value="">全部周期</option>
        <option value="MONTHLY">月度</option>
        <option value="QUARTERLY">季度</option>
      </select>
      <select v-model="filters.grade" data-testid="perf-result-grade-filter" style="width: 150px">
        <option value="">全部分档</option>
        <option value="EXCELLENT">优秀 ≥85</option>
        <option value="QUALIFIED">合格 60~84</option>
        <option value="IMPROVE">待改进 &lt;60</option>
      </select>
      <select v-model="filters.deptId" data-testid="perf-result-dept" style="width: 140px">
        <option value="">全部部门</option>
        <option v-for="dept in resultDepts" :key="dept.deptId" :value="String(dept.deptId)">{{ dept.deptName }}</option>
      </select>
      <input v-model="filters.evaluateeName" data-testid="perf-result-name" placeholder="被考核人" style="width: 120px" />
      <input v-model="filters.recordNo" data-testid="perf-result-no" placeholder="单号" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="perf-result-query">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="perf-result-reset" @click="resetFilters">重置</button>
    </form>
    <p class="hint" data-testid="perf-result-dist">{{ distText }}</p>
    <div class="g3" style="margin-bottom: 12px">
      <div class="card stat" data-testid="perf-result-top3" style="border-left: 3px solid var(--green)">
        <span class="l">红榜 TOP3</span>
        <div style="margin-top: 8px">
          <span v-if="!topRecords.length">—</span>
          <span v-for="row in topRecords" :key="row.id" class="tag" style="margin-right: 6px">
            🏆{{ row.rank }} {{ row.evaluateeName }} {{ scoreText(row.totalScore) }}
          </span>
        </div>
      </div>
      <div class="card stat" data-testid="perf-result-tail" style="border-left: 3px solid var(--red)">
        <span class="l">末位预警</span>
        <div style="margin-top: 8px">
          <span v-if="!tailRecords.length">本期没有待改进</span>
          <span v-for="row in tailRecords" :key="row.id" class="tag" style="margin-right: 6px; color: var(--red)">
            {{ row.evaluateeName }} {{ scoreText(row.totalScore) }}
          </span>
        </div>
      </div>
      <div class="card stat" data-testid="perf-result-avg">
        <span class="l">部门均分</span>
        <div class="n" data-testid="perf-result-avg-value">{{ resultAverage == null ? '—' : scoreText(resultAverage) }}</div>
      </div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>被考核人</th>
              <th>部门</th>
              <th>周期</th>
              <th>KPI 得分</th>
              <th>加减分项</th>
              <th>综合得分</th>
              <th>评级</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="perf-result-empty"><div class="et">{{ emptyText }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" data-testid="perf-result-row">
              <td class="num">{{ row.rank && row.rank <= 3 ? `🏆${row.rank}` : row.rank || '—' }}</td>
              <td>
                {{ row.evaluateeName }}
                <div class="csub mono">{{ row.recordNo }}</div>
              </td>
              <td>{{ row.deptName || '—' }}</td>
              <td>{{ row.cycleDisplay }}</td>
              <td class="num">{{ row.calcBaseScore ?? '—' }}</td>
              <td class="num">{{ row.manualAdjustment ?? 0 }}</td>
              <td class="num">{{ row.totalScore ?? '—' }}</td>
              <td><span class="tag" data-testid="perf-result-grade">{{ row.gradeEdge || row.grade }}</span></td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="perf-result-view" @click="openDetail(row)">
                  查看
                </button>
                <button class="btn btn-sec btn-sm" type="button" data-testid="perf-result-alert" @click="openAlert(row)">
                  改进预警
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" data-testid="perf-result-detail" @click.self="detail = null">
      <div class="modal card" style="max-width: 760px; padding: 20px">
        <h3 style="margin: 0 0 8px">{{ detail.evaluateeName }} · {{ detail.recordNo }}</h3>
        <p class="hint">{{ detail.deptName }} · {{ detail.cycleDisplay }} · 综合 {{ detail.totalScore ?? '—' }} · {{ detail.gradeEdge }}</p>
        <div class="tbl-wrap">
          <table>
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
              <tr v-if="!detail.lines?.length">
                <td colspan="6">暂无指标明细</td>
              </tr>
              <tr v-for="line in detail.lines || []" :key="line.metricName">
                <td>{{ line.metricName }}</td>
                <td>{{ line.weight }}%</td>
                <td>{{ line.rawValue }}</td>
                <td>{{ line.autoScore }}</td>
                <td>{{ line.manualAdjustment }}</td>
                <td>{{ line.finalScore }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="detail = null">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="perf-result-detail-export" @click="exportOne(detail)">
            导出考核单
          </button>
        </div>
      </div>
    </div>

    <div v-if="alertRow" class="modal-mask" data-testid="perf-result-alert-dialog" @click.self="alertRow = null">
      <div class="modal card" style="max-width: 420px; padding: 20px">
        <h3 style="margin: 0 0 8px">改进预警</h3>
        <p>{{ alertText }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" @click="alertRow = null">知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type ScoreLine = {
  metricName: string
  weight: number
  rawValue: number
  autoScore: number
  manualAdjustment: number
  finalScore: number
}
type Row = {
  id: number
  recordNo: string
  evaluateeName: string
  deptId?: number
  deptName?: string
  position: string
  cycleDisplay: string
  totalScore?: number
  calcBaseScore?: number | null
  manualAdjustment?: number
  grade: string
  gradeEdge?: string
  alerted?: boolean
  status: string
  rank?: number
  lines?: ScoreLine[]
}

type GradeCounts = { EXCELLENT: number; QUALIFIED: number; IMPROVE: number }
type RankRow = {
  id?: number
  userId: number
  userName: string
  deptName: string
  totalScore: number
  rankNo: number
  boardRank?: number
  medal?: string
  gradeLevel: string
  alertStatus?: string
}
type DeptOpt = { deptId: number; deptName: string }
type DeptAvg = { deptId: number; deptName: string; average: number | null; headcount: number }

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const counts = ref<GradeCounts>({ EXCELLENT: 0, QUALIFIED: 0, IMPROVE: 0 })
const recordGradeLine = ref('优秀 ≥85 · 合格 60~84 · 待改进 <60')
const filters = reactive({ status: '', periodType: '', grade: '', deptId: '', evaluateeName: '', recordNo: '' })
const resultDepts = ref<DeptOpt[]>([])
const topRecords = ref<Row[]>([])
const tailRecords = ref<Row[]>([])
const resultAverage = ref<number | null>(null)
const detail = ref<Row | null>(null)
const alertRow = ref<Row | null>(null)
const rankPeriod = ref(previousMonth())
const rankDept = ref('')
const rankRows = ref<RankRow[]>([])
const top3 = ref<RankRow[]>([])
const tail = ref<RankRow[]>([])
const depts = ref<DeptOpt[]>([])
const deptAverages = ref<DeptAvg[]>([])
const deptAverage = ref<number | null>(null)
const rankEmpty = ref('')
const pipStub = ref('')
const gradeLine = ref('优秀 ≥85 · 合格 60~84 · 待改进 <60')

const deptAverageText = computed(() => {
  if (!deptAverages.value.length) return ''
  return deptAverages.value
    .map((item) => `${item.deptName} ${item.headcount} 人`)
    .join(' · ')
})

function previousMonth() {
  const now = new Date()
  const cursor = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  return `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`
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

function medalText(medal: string | undefined, rankNo: number | undefined) {
  if (medal === 'GOLD' || (!medal && rankNo === 1)) return '金'
  if (medal === 'SILVER' || (!medal && rankNo === 2)) return '银'
  if (medal === 'BRONZE' || (!medal && rankNo === 3)) return '铜'
  return String(rankNo || '—')
}

function onRankPeriod() {
  rankDept.value = ''
  loadRank()
}

async function loadRank() {
  rankEmpty.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 100 }
    if (rankDept.value) params.deptId = Number(rankDept.value)
    const res = await http.get(`/perf/rank/period/${rankPeriod.value}`, { params })
    const data = res.data.data || {}
    rankRows.value = data.list || []
    const board = data.rankBoard || {}
    top3.value = board.top3 || []
    tail.value = board.tail || []
    depts.value = board.depts || []
    deptAverages.value = board.deptAverages || []
    deptAverage.value = board.deptAverage ?? null
    pipStub.value = board.pipStub || ''
    if (board.gradeLine) gradeLine.value = board.gradeLine
    if (board.emptyReason === 'UNPUBLISHED') {
      rankEmpty.value = '本期绩效尚未核准发布，发布后自动生成排名'
    } else if (board.emptyReason === 'DEPT_EMPTY') {
      rankEmpty.value = '当前部门没有排名'
    }
  } catch (err) {
    const body = err as { code?: number; msg?: string }
    rankRows.value = []
    top3.value = []
    tail.value = []
    deptAverage.value = null
    rankEmpty.value = body.code === 403 ? '仅管理者可查看全量排名' : body.msg || '排名加载失败'
  }
}

const filtered = computed(
  () =>
    !!(
      filters.status ||
      filters.periodType ||
      filters.grade ||
      filters.deptId ||
      filters.evaluateeName.trim() ||
      filters.recordNo.trim()
    ),
)
const alertText = computed(() => {
  const row = alertRow.value
  if (!row) return ''
  if (row.grade === 'IMPROVE' || row.alerted) {
    return `${row.evaluateeName} 综合得分 ${scoreText(row.totalScore)}，低于合格线，已触发改进预警`
  }
  return `${row.evaluateeName} 本期未低于合格线，不触发改进预警`
})

const emptyText = computed(() => {
  if (error.value) return error.value
  if (filtered.value) return '当前筛选没有考核结果'
  return '暂无可阅考核结果'
})

const distText = computed(() => {
  const item = counts.value
  return `分档分布 优秀 ${item.EXCELLENT || 0} · 合格 ${item.QUALIFIED || 0} · 待改进 ${item.IMPROVE || 0}（${recordGradeLine.value}）`
})

function listParams() {
  return {
    pageNo: 1,
    pageSize: 50,
    status: filters.status || undefined,
    periodType: filters.periodType || undefined,
    grade: filters.grade || undefined,
    deptId: filters.deptId || undefined,
    evaluateeName: filters.evaluateeName.trim() || undefined,
    recordNo: filters.recordNo.trim() || undefined,
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/perf/result/list', { params: listParams() })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      counts.value = { EXCELLENT: 0, QUALIFIED: 0, IMPROVE: 0 }
      topRecords.value = []
      tailRecords.value = []
      resultAverage.value = null
      return
    }
    rows.value = res.data.data?.list || []
    counts.value = res.data.data?.gradeCounts || { EXCELLENT: 0, QUALIFIED: 0, IMPROVE: 0 }
    if (res.data.data?.gradeLine) recordGradeLine.value = res.data.data.gradeLine
    resultDepts.value = res.data.data?.depts || []
    const board = res.data.data?.resultBoard || {}
    topRecords.value = board.top3 || []
    tailRecords.value = board.tail || []
    resultAverage.value = board.deptAverage ?? null
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = ''
  filters.periodType = ''
  filters.grade = ''
  filters.deptId = ''
  filters.evaluateeName = ''
  filters.recordNo = ''
  exportNote.value = ''
  loadList()
}

async function exportCsv() {
  exportNote.value = ''
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.periodType) params.set('periodType', filters.periodType)
  if (filters.grade) params.set('grade', filters.grade)
  if (filters.deptId) params.set('deptId', filters.deptId)
  const name = filters.evaluateeName.trim()
  if (name) params.set('evaluateeName', name)
  const recordNo = filters.recordNo.trim()
  if (recordNo) params.set('recordNo', recordNo)
  const qs = params.toString()
  const url = `/admin-api/ims/perf/result/export${qs ? `?${qs}` : ''}`
  const token = localStorage.getItem('ims_access')
  try {
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      exportNote.value = `导出失败（${res.status}）`
      return
    }
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const body = (await res.json()) as { msg?: string }
      exportNote.value = body.msg || '导出失败'
      return
    }
    const count = Number(res.headers.get('X-Export-Rows') || '0')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'perf_results.csv'
    a.click()
    URL.revokeObjectURL(a.href)
    exportNote.value =
      count === 0
        ? '当前筛选没有可导出的已确认或已下发结果，已导出空表'
        : `已导出 ${count} 条已确认或已下发结果`
  } catch {
    exportNote.value = '导出网络错误'
  }
}

function openDetail(row: Row) {
  detail.value = row
}

function openAlert(row: Row) {
  alertRow.value = row
}

function exportOne(row: Row) {
  const header = ['recordNo', 'evaluateeName', 'deptName', 'cycle', 'metric', 'weight', 'raw', 'auto', 'adjust', 'final', 'total']
  const lines = row.lines?.length ? row.lines : [null]
  const body = lines
    .map((line) =>
      [
        row.recordNo,
        row.evaluateeName,
        row.deptName || '',
        row.cycleDisplay,
        line?.metricName || '',
        line?.weight ?? '',
        line?.rawValue ?? '',
        line?.autoScore ?? '',
        line?.manualAdjustment ?? '',
        line?.finalScore ?? '',
        row.totalScore ?? '',
      ].join(','),
    )
    .join('\n')
  const blob = new Blob([`\ufeff${header.join(',')}\n${body}\n`], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${row.recordNo}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

onMounted(() => {
  loadList()
  loadRank()
})
</script>
