<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>培训统计看板</h1>
        <div class="sub">TRAIN-003 · BR-102 完成率 / 逾期督办 · 02 TRAIN</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/train/task">学习任务</router-link>
    </div>

    <form class="qbar" @submit.prevent="reloadAll">
      <button
        type="button"
        class="btn btn-sm"
        :class="rangePreset === '7' ? 'btn-pri' : 'btn-sec'"
        @click="setPreset('7')"
      >
        近7天
      </button>
      <button
        type="button"
        class="btn btn-sm"
        :class="rangePreset === '30' ? 'btn-pri' : 'btn-sec'"
        @click="setPreset('30')"
      >
        近30天
      </button>
      <input v-model="customRange" placeholder="自定义 yyyy-MM-dd,yyyy-MM-dd" style="width: 220px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
    </form>

    <div class="tabs" style="margin-top: 12px">
      <button type="button" class="tab" :class="{ on: tab === 'finish' }" data-testid="train-stat-tab-finish" @click="selectTab('finish')">
        完成率总览
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" data-testid="train-stat-tab-dept" @click="selectTab('dept')">
        部门统计
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'rank' }" data-testid="train-stat-tab-rank" @click="selectTab('rank')">
        时长排行
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'overdue' }" data-testid="train-stat-tab-overdue" @click="selectTab('overdue')">
        逾期督办
      </button>
    </div>

    <div class="stat-body">
      <div class="stat-main">
        <div v-if="tab === 'finish'">
          <div v-if="finish" class="g3" style="margin: 12px 0">
            <div class="card stat">
              <span class="l">总完成率</span>
              <div class="n" data-testid="train-stat-total-rate" :style="{ color: rateColor(finish.totalFinishRate) }">
                {{ finish.totalFinishRate }}%
              </div>
              <div class="d">BR-102 目标 &gt;90%</div>
            </div>
            <div class="card stat">
              <span class="l">按任务条目</span>
              <div class="n">{{ finish.byTask.length }}</div>
              <div class="d">Top10 完成率</div>
            </div>
            <div class="card stat">
              <span class="l">按部门</span>
              <div class="n">{{ finish.byDept.length }}</div>
            </div>
          </div>

          <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

          <h3 style="margin: 8px 0 6px; font-size: 14px">按任务（Top10）</h3>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>任务编号</th>
                    <th>任务名称</th>
                    <th>应完成</th>
                    <th>已完成</th>
                    <th>完成率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="loading">
                    <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
                  </tr>
                  <tr v-else-if="!finish?.byTask?.length">
                    <td colspan="5"><div class="empty"><div class="et">暂无统计数据</div></div></td>
                  </tr>
                  <tr v-for="row in (finish?.byTask || []).slice(0, 10)" v-else :key="row.taskNo">
                    <td class="mono">{{ row.taskNo }}</td>
                    <td>{{ row.taskName }}</td>
                    <td class="num">{{ row.assignedCount }}</td>
                    <td class="num">{{ row.finishedCount }}</td>
                    <td :style="{ color: rateColor(row.finishRate) }">{{ row.finishRate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 style="margin: 12px 0 6px; font-size: 14px">按部门</h3>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>部门</th>
                    <th>应完成</th>
                    <th>已完成</th>
                    <th>完成率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in finish?.byDept || []" :key="row.deptId">
                    <td>{{ row.deptName }}</td>
                    <td class="num">{{ row.assignedCount }}</td>
                    <td class="num">{{ row.finishedCount }}</td>
                    <td :style="{ color: rateColor(row.finishRate) }">{{ row.finishRate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <h3 style="margin: 12px 0 6px; font-size: 14px">按个人</h3>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>姓名</th>
                    <th>部门</th>
                    <th>应完成</th>
                    <th>已完成</th>
                    <th>完成率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in personPageRows" :key="row.userId">
                    <td>{{ row.userName || `用户#${row.userId}` }}</td>
                    <td>{{ row.deptName }}</td>
                    <td class="num">{{ row.assignedCount }}</td>
                    <td class="num">{{ row.finishedCount }}</td>
                    <td :style="{ color: rateColor(row.finishRate) }">{{ row.finishRate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="personTotalPages > 1" class="hint" style="margin-top: 8px">
              <button type="button" class="btn btn-sec btn-sm" :disabled="personPage <= 1" @click="personPage--">
                上一页
              </button>
              <span style="margin: 0 8px">{{ personPage }} / {{ personTotalPages }}</span>
              <button
                type="button"
                class="btn btn-sec btn-sm"
                :disabled="personPage >= personTotalPages"
                @click="personPage++"
              >
                下一页
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="tab === 'dept'" data-testid="train-stat-dept-panel">
          <p class="hint" data-testid="train-stat-as-of">
            数据截至 {{ asOf || '—' }} · 来源 ims_train_stat_daily（读取时按完成率口径重算）
          </p>
          <p v-if="panelError" class="hint" style="color: var(--red)">{{ panelError }}</p>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>统计日期</th>
                    <th>部门</th>
                    <th>应完成</th>
                    <th>已完成</th>
                    <th>完成率</th>
                    <th>人均时长</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="panelLoading">
                    <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
                  </tr>
                  <tr v-else-if="!deptRows.length">
                    <td colspan="6"><div class="empty"><div class="et">暂无统计数据</div></div></td>
                  </tr>
                  <tr v-for="row in deptRows" v-else :key="`${row.statDate}-${row.deptId}`" :data-testid="'train-stat-dept-row'">
                    <td class="mono">{{ row.statDate }}</td>
                    <td :style="row.alertPushed ? { color: 'var(--red)', fontWeight: '600' } : undefined">
                      {{ row.deptName }}
                      <span v-if="row.alertPushed" data-testid="train-stat-alert-tag">已推送负责人</span>
                    </td>
                    <td class="num">{{ row.assignedCount }}</td>
                    <td class="num">{{ row.finishedCount }}</td>
                    <td :style="{ color: rateColor(row.finishRate) }">{{ row.finishRate }}%</td>
                    <td>{{ formatDuration(row.avgDurationMinutes) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-else-if="tab === 'rank'" data-testid="train-stat-rank-panel">
          <form class="qbar" @submit.prevent="loadRank">
            <button
              type="button"
              class="btn btn-sm"
              :class="rankDimension === 'DEPT' ? 'btn-pri' : 'btn-sec'"
              data-testid="train-stat-rank-dept"
              @click="setRankDimension('DEPT')"
            >
              部门
            </button>
            <button
              type="button"
              class="btn btn-sm"
              :class="rankDimension === 'PERSON' ? 'btn-pri' : 'btn-sec'"
              data-testid="train-stat-rank-person"
              @click="setRankDimension('PERSON')"
            >
              个人
            </button>
            <select v-model.number="topN" data-testid="train-stat-topn" @change="loadRank">
              <option :value="10">Top 10</option>
              <option :value="20">Top 20</option>
              <option :value="50">Top 50</option>
            </select>
          </form>
          <p v-if="panelError" class="hint" style="color: var(--red)">{{ panelError }}</p>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>名次</th>
                    <th>名称</th>
                    <th>总时长</th>
                    <th>完成率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="panelLoading">
                    <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
                  </tr>
                  <tr v-else-if="!rankRows.length">
                    <td colspan="4"><div class="empty"><div class="et">暂无统计数据</div></div></td>
                  </tr>
                  <tr v-for="row in rankRows" v-else :key="`${row.rank}-${rankName(row)}`" data-testid="train-stat-rank-row">
                    <td class="num">{{ row.rank }}</td>
                    <td>{{ rankName(row) }}</td>
                    <td>{{ formatDuration(row.totalDurationMinutes) }}</td>
                    <td :style="{ color: rateColor(row.finishRate) }">{{ row.finishRate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-else data-testid="train-stat-overdue-panel">
          <form class="qbar" @submit.prevent="loadOverdue">
            <input v-model="overdueTaskId" placeholder="任务 ID" style="width: 120px" data-testid="train-stat-overdue-task" />
            <input v-model="overdueDeptId" placeholder="部门 ID" style="width: 120px" data-testid="train-stat-overdue-dept" />
            <button class="btn btn-pri btn-sm" type="submit">筛选</button>
            <span class="sp"></span>
            <button class="btn btn-sec btn-sm" type="button" data-testid="train-stat-export" @click="exportOverdue">
              导出 Excel
            </button>
          </form>
          <p v-if="exportMsg" class="hint" data-testid="train-stat-export-msg">{{ exportMsg }}</p>
          <p v-if="panelError" class="hint" style="color: var(--red)">{{ panelError }}</p>
          <div class="tbl-block">
            <div class="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>任务编号</th>
                    <th>任务名称</th>
                    <th>学员</th>
                    <th>部门</th>
                    <th>截止时间</th>
                    <th>逾期天数</th>
                    <th>进度</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="panelLoading">
                    <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
                  </tr>
                  <tr v-else-if="!overdueRows.length">
                    <td colspan="8"><div class="empty"><div class="et">暂无统计数据</div></div></td>
                  </tr>
                  <tr v-for="row in overdueRows" v-else :key="`${row.taskId}-${row.userId}`" data-testid="train-stat-overdue-row">
                    <td class="mono">{{ row.taskNo }}</td>
                    <td>{{ row.taskName }}</td>
                    <td>{{ row.userName || `用户#${row.userId}` }}</td>
                    <td>{{ row.deptName }}</td>
                    <td class="mono">{{ row.deadline }}</td>
                    <td class="num" style="color: var(--red)" data-testid="train-stat-overdue-days">{{ row.overdueDays }}</td>
                    <td>{{ row.progress }}%</td>
                    <td>
                      <button class="btn btn-txt" type="button" @click="goSupervise(row)">去督办</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <aside class="card stat-heat" data-testid="train-stat-heat">
        <h3 style="margin: 0 0 8px; font-size: 14px">资料热度</h3>
        <p class="hint">学习人次 Top10</p>
        <p v-if="heatError" class="hint" style="color: var(--red)">{{ heatError }}</p>
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>标题</th>
              <th>类型</th>
              <th>人次</th>
              <th>人均时长</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!heatRows.length">
              <td colspan="5"><div class="empty"><div class="et">暂无统计数据</div></div></td>
            </tr>
            <tr v-for="row in heatRows" :key="row.materialId" data-testid="train-stat-heat-row">
              <td class="mono">{{ row.materialNo }}</td>
              <td>{{ row.title }}</td>
              <td>{{ materialTypeLabel(row.materialType) }}</td>
              <td class="num">{{ row.studyCount }}</td>
              <td>{{ formatDuration(row.avgDurationMinutes) }}</td>
            </tr>
          </tbody>
        </table>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type FinishRow = {
  taskNo: string
  taskName: string
  assignedCount: number
  finishedCount: number
  finishRate: number
}
type DeptFinishRow = {
  deptId: number
  deptName: string
  assignedCount: number
  finishedCount: number
  finishRate: number
}
type PersonRow = {
  userId: number
  userName: string
  deptName: string
  assignedCount: number
  finishedCount: number
  finishRate: number
}
type FinishResp = {
  totalFinishRate: number
  byTask: FinishRow[]
  byDept: DeptFinishRow[]
  byPerson: PersonRow[]
}
type DeptStatRow = {
  statDate: string
  deptId: number
  deptName: string
  assignedCount: number
  finishedCount: number
  finishRate: number
  avgDurationMinutes: number
  alertPushed?: boolean
}
type RankRow = {
  rank: number
  deptName?: string
  userName?: string
  userId?: number
  totalDurationMinutes: number
  finishRate: number
}
type OverdueRow = {
  taskId: number
  taskNo: string
  taskName: string
  userId: number
  userName: string
  deptName: string
  deadline: string
  overdueDays: number
  progress: number
}
type HeatRow = {
  materialId: number
  materialNo: string
  title: string
  materialType: string
  studyCount: number
  avgDurationMinutes: number
}

const router = useRouter()
const tab = ref<'finish' | 'dept' | 'rank' | 'overdue'>('finish')
const rangePreset = ref<'7' | '30' | 'custom'>('30')
const customRange = ref('')
const finish = ref<FinishResp | null>(null)
const loading = ref(false)
const error = ref('')
const personPage = ref(1)
const personPageSize = 10
const deptRows = ref<DeptStatRow[]>([])
const rankRows = ref<RankRow[]>([])
const rankDimension = ref<'DEPT' | 'PERSON'>('DEPT')
const topN = ref(10)
const overdueRows = ref<OverdueRow[]>([])
const overdueTaskId = ref('')
const overdueDeptId = ref('')
const exportMsg = ref('')
const heatRows = ref<HeatRow[]>([])
const heatError = ref('')
const panelLoading = ref(false)
const panelError = ref('')

const personTotalPages = computed(() => {
  const n = finish.value?.byPerson?.length || 0
  return Math.max(1, Math.ceil(n / personPageSize))
})

const personPageRows = computed(() => {
  const all = finish.value?.byPerson || []
  const start = (personPage.value - 1) * personPageSize
  return all.slice(start, start + personPageSize)
})

const asOf = computed(() => deptRows.value[0]?.statDate || '')

function fmtDate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function activeDateRange(): string | undefined {
  if (rangePreset.value === 'custom' && customRange.value.trim()) {
    return customRange.value.trim()
  }
  const end = new Date()
  const start = new Date()
  const days = rangePreset.value === '7' ? 7 : 30
  start.setDate(end.getDate() - (days - 1))
  return `${fmtDate(start)},${fmtDate(end)}`
}

function setPreset(p: '7' | '30') {
  rangePreset.value = p
  customRange.value = ''
  void reloadAll()
}

function rateColor(rate: number) {
  if (rate >= 90) return 'var(--green)'
  if (rate >= 70) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

function formatDuration(minutes: number) {
  const total = Math.max(0, Math.round(Number(minutes) || 0))
  const hours = Math.floor(total / 60)
  const rest = total % 60
  return `${hours} 小时 ${rest} 分钟`
}

function materialTypeLabel(kind: string) {
  if (kind === 'VIDEO') return '视频'
  if (kind === 'LINK') return '链接'
  return '文档'
}

function rankName(row: RankRow) {
  if (rankDimension.value === 'PERSON') return row.userName || `用户#${row.userId ?? ''}`
  return row.deptName || '未分配'
}

function errText(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'msg' in err && typeof (err as { msg?: string }).msg === 'string') {
    return (err as { msg: string }).msg
  }
  return fallback
}

async function loadFinishRate() {
  if (customRange.value.trim()) rangePreset.value = 'custom'
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string> = {}
    const dr = activeDateRange()
    if (dr) params.dateRange = dr
    const res = await http.get('/train/stat/finish-rate', { params })
    finish.value = res.data.data
    personPage.value = 1
  } catch (err) {
    error.value = errText(err, '网络错误')
    finish.value = null
  } finally {
    loading.value = false
  }
}

async function loadHeat() {
  heatError.value = ''
  try {
    const params: Record<string, string | number> = { topN: 10 }
    const dr = activeDateRange()
    if (dr) params.dateRange = dr
    const res = await http.get('/train/stat/material-heat', { params })
    heatRows.value = res.data.data || []
  } catch (err) {
    heatError.value = errText(err, '资料热度加载失败')
    heatRows.value = []
  }
}

async function loadDept() {
  panelLoading.value = true
  panelError.value = ''
  try {
    const params: Record<string, string> = {}
    const dr = activeDateRange()
    if (dr) params.statDateRange = dr
    const res = await http.get('/train/stat/dept', { params })
    deptRows.value = res.data.data || []
  } catch (err) {
    panelError.value = errText(err, '部门统计加载失败')
    deptRows.value = []
  } finally {
    panelLoading.value = false
  }
}

async function loadRank() {
  panelLoading.value = true
  panelError.value = ''
  try {
    const params: Record<string, string | number> = { dimension: rankDimension.value, topN: topN.value }
    const dr = activeDateRange()
    if (dr) params.dateRange = dr
    const res = await http.get('/train/stat/rank', { params })
    rankRows.value = res.data.data || []
  } catch (err) {
    panelError.value = errText(err, '排行加载失败')
    rankRows.value = []
  } finally {
    panelLoading.value = false
  }
}

function setRankDimension(next: 'DEPT' | 'PERSON') {
  rankDimension.value = next
  void loadRank()
}

async function fetchOverduePage(pageNo: number) {
  const params: Record<string, string | number> = { pageNo, pageSize: 100 }
  const taskId = Number(overdueTaskId.value)
  const deptId = overdueDeptId.value.trim()
  if (taskId > 0) params.taskId = taskId
  if (deptId !== '' && !Number.isNaN(Number(deptId))) params.deptId = Number(deptId)
  const res = await http.get('/train/stat/overdue', { params })
  return res.data.data as { list: OverdueRow[]; total: number }
}

async function loadOverdue() {
  panelLoading.value = true
  panelError.value = ''
  exportMsg.value = ''
  try {
    const data = await fetchOverduePage(1)
    overdueRows.value = data.list || []
  } catch (err) {
    panelError.value = errText(err, '逾期清单加载失败')
    overdueRows.value = []
  } finally {
    panelLoading.value = false
  }
}

function xmlEscape(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function goSupervise(row: OverdueRow) {
  router.push({
    path: '/ims/train/task',
    query: { taskId: String(row.taskId), taskName: row.taskName },
  })
}

async function exportOverdue() {
  exportMsg.value = '导出任务已提交'
  try {
    const data = await fetchOverduePage(1)
    const rows = data.list || []
    overdueRows.value = rows
    const header = ['任务编号', '任务名称', '学员', '部门', '截止时间', '逾期天数', '进度']
    const body = rows.map((row) => [
      row.taskNo,
      row.taskName,
      row.userName,
      row.deptName,
      row.deadline,
      String(row.overdueDays),
      `${row.progress}%`,
    ])
    const xmlRows = [header, ...body]
      .map(
        (cols) =>
          `<Row>${cols.map((col) => `<Cell><Data ss:Type="String">${xmlEscape(String(col ?? ''))}</Data></Cell>`).join('')}</Row>`,
      )
      .join('')
    const xml = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="逾期督办"><Table>${xmlRows}</Table></Worksheet>
</Workbook>`
    const blob = new Blob([xml], { type: 'application/vnd.ms-excel' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'train_overdue.xls'
    link.click()
  } catch (err) {
    exportMsg.value = ''
    panelError.value = errText(err, '导出失败')
  }
}

async function selectTab(next: 'finish' | 'dept' | 'rank' | 'overdue') {
  tab.value = next
  if (next === 'finish') await loadFinishRate()
  else if (next === 'dept') await loadDept()
  else if (next === 'rank') await loadRank()
  else await loadOverdue()
}

async function reloadAll() {
  await Promise.all([loadFinishRate(), loadHeat()])
  if (tab.value === 'dept') await loadDept()
  else if (tab.value === 'rank') await loadRank()
  else if (tab.value === 'overdue') await loadOverdue()
}

onMounted(() => {
  void reloadAll()
})
</script>

<style scoped>
.stat-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-top: 12px;
}
.stat-main {
  flex: 1;
  min-width: 0;
}
.stat-heat {
  width: 360px;
  flex: none;
  padding: 12px;
}
.stat-heat table {
  width: 100%;
}
@media (max-width: 960px) {
  .stat-body {
    flex-direction: column;
  }
  .stat-heat {
    width: 100%;
  }
}
</style>
