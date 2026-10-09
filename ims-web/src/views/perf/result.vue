<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>考核结果</h1>
        <div class="sub">FR-M3-003 · GET /perf/result/list · GET /perf/result/export · 05 PERF</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="exportCsv">导出 CSV</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/perf/execution">执行考核</router-link>
      </div>
    </div>
    <p class="hint">仅展示 CALCULATED 及以上态；草稿/算分中仍留在执行考核页。</p>

    <section data-testid="perf-rank-board" style="margin-bottom: 16px">
      <div class="pg-h" style="margin-bottom: 8px">
        <div>
          <div class="sub">PERF-004 排名区 · {{ gradeLine }}</div>
          <p class="hint">V2 排名不含竞品分析维度（BR-110）。</p>
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
      <select v-model="filters.status" style="width: 130px">
        <option value="">全部可阅态</option>
        <option value="CONFIRMED">已确认</option>
        <option value="ISSUED">已下发</option>
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
              <th>被考核人</th>
              <th>岗位</th>
              <th>周期</th>
              <th>得分</th>
              <th>等级</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无已发布结果' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.recordNo }}</td>
              <td>{{ row.evaluateeName }}</td>
              <td>{{ row.position }}</td>
              <td>{{ row.cycleDisplay }}</td>
              <td class="num">{{ row.totalScore ?? '—' }}</td>
              <td><span class="tag">{{ row.grade }}</span></td>
              <td>{{ row.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = {
  id: number
  recordNo: string
  evaluateeName: string
  position: string
  cycleDisplay: string
  totalScore?: number
  grade: string
  status: string
}

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
const filters = reactive({ status: '' })
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

function medalText(medal: string, rankNo: number) {
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

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/perf/result/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        status: filters.status || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  const qs = params.toString()
  const url = `/admin-api/ims/perf/result/export${qs ? `?${qs}` : ''}`
  const token = localStorage.getItem('ims_access')
  try {
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      error.value = `导出失败（${res.status}）`
      return
    }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'perf_results.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    error.value = '导出网络错误'
  }
}

onMounted(() => {
  loadList()
  loadRank()
})
</script>
