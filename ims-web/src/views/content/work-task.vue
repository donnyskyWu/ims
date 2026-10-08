<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>工作任务登记</h1>
        <div class="sub">作者×赛事矩阵 · 确认出任务/撤回（CONTENT-104/105）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="loadSheet">刷新登记表</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      运行时 SSOT：登记 <code>/content/work-task/sheet</code>（#8～#10）· 执行情况只读
      <code>/content/task/page</code>（#3）· 矩阵透视自登记表（只读）
    </p>

    <div class="work-task-page">
      <div class="tabs">
        <div class="tab" :class="{ on: tab === 'register' }" @click="switchTab('register')">任务登记</div>
        <div class="tab" :class="{ on: tab === 'execution' }" @click="switchTab('execution')">任务执行情况</div>
        <div class="tab" :class="{ on: tab === 'matrix' }" @click="switchTab('matrix')">任务管理</div>
      </div>

      <div v-show="tab === 'register'" class="qbar">
        <input v-model="ipGroupId" type="number" placeholder="IP 组 id" style="width: 100px" />
        <input v-model="workDate" type="date" style="width: 140px" />
        <button class="btn btn-pri btn-sm" type="button" @click="loadSheet">查询</button>
        <span class="sp"></span>
        <button class="btn btn-sec btn-sm" type="button" :disabled="saving" @click="saveSheet">保存</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="!selectedIds.length" @click="confirmRows">确认出任务</button>
        <button class="btn btn-sec btn-sm" type="button" :disabled="!selectedIds.length" @click="withdrawRows">撤回</button>
      </div>

      <div v-if="tab === 'register'" class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
                <th>行</th>
                <th>作者 id</th>
                <th>营销计划</th>
                <th>赛事</th>
                <th>销售平台</th>
                <th>状态</th>
                <th>已出任务</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!editableRows.length">
                <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无登记行' }}</div></div></td>
              </tr>
              <tr v-for="row in editableRows" v-else :key="row.rowNo">
                <td>
                  <input
                    v-model="selectedIds"
                    type="checkbox"
                    :value="row.id"
                    :disabled="!row.id"
                  />
                </td>
                <td class="num">{{ row.rowNo }}</td>
                <td>
                  <input v-model.number="row.authorId" type="number" style="width: 72px" :disabled="row.rowStatus === 'CONFIRMED'" />
                </td>
                <td>
                  <select v-model="row.marketingPlan" :disabled="row.rowStatus === 'CONFIRMED'">
                    <option value="LIVE_PUBLIC">直播公推</option>
                    <option value="PAID_SALES">付费销售</option>
                  </select>
                </td>
                <td>
                  <input
                    v-model="row.competitionId"
                    placeholder="赛事 id"
                    style="width: 88px"
                    :disabled="row.rowStatus === 'CONFIRMED'"
                  />
                  <input
                    v-model="row.competitionName"
                    placeholder="名称"
                    style="width: 100px; margin-left: 4px"
                    :disabled="row.rowStatus === 'CONFIRMED'"
                  />
                </td>
                <td>
                  <select v-model="row.salesPlatform" :disabled="row.rowStatus === 'CONFIRMED'">
                    <option value="DOUYIN">抖音</option>
                    <option value="KUAISHOU">快手</option>
                    <option value="PRIVATE">私域</option>
                    <option value="NONE">无</option>
                  </select>
                </td>
                <td>{{ row.rowStatus || 'DRAFT' }}</td>
                <td class="mono">{{ (row.generatedTaskIds || []).join(', ') || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pager">
          <span class="pg-total">Sheet {{ sheetId || '—' }} · {{ sheetStatus || '—' }}</span>
        </div>
      </div>

      <div v-if="tab === 'execution'" class="tbl-block">
        <div class="qbar">
          <input v-model="ipGroupId" type="number" placeholder="IP 组 id" style="width: 100px" />
          <input v-model="workDate" type="date" style="width: 140px" />
          <select v-model="execMarketingPlan" style="width: 140px">
            <option value="">全部营销计划</option>
            <option value="LIVE_PUBLIC">直播公推</option>
            <option value="PAID_SALES">付费销售</option>
          </select>
          <button class="btn btn-pri btn-sm" type="button" @click="loadExecution">查询</button>
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>赛事</th>
                <th>营销计划</th>
                <th>作者</th>
                <th>节点名称</th>
                <th>执行人</th>
                <th>直播</th>
                <th>状态</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="execLoading">
                <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!executionRows.length">
                <td colspan="8"><div class="empty"><div class="et">{{ execError || '暂无执行记录' }}</div></div></td>
              </tr>
              <tr v-for="line in executionRows" v-else :key="line.id">
                <td>{{ line.competitionName || '—' }}</td>
                <td>{{ marketingPlanLabel(line.marketingPlan) }}</td>
                <td>{{ line.authorName || line.authorId || '—' }}</td>
                <td>{{ line.nodeName }}</td>
                <td>{{ line.assigneeName || '—' }}</td>
                <td>{{ line.isLive ? `是 · ${line.liveTime || '—'}` : '否' }}</td>
                <td>{{ line.status }}</td>
                <td class="mono">{{ line.createdAt || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pager"><span class="pg-total">共 {{ executionRows.length }} 条（工作任务轨 · 只读）</span></div>
      </div>

      <div v-if="tab === 'matrix'" class="tbl-block">
        <div class="qbar">
          <input v-model="ipGroupId" type="number" placeholder="IP 组 id" style="width: 100px" />
          <input v-model="workDate" type="date" style="width: 140px" />
          <button class="btn btn-pri btn-sm" type="button" @click="loadSheet">查询</button>
        </div>
        <div class="wt-matrix-summary card" style="padding: 10px 14px; margin-bottom: 10px">
          总任务 {{ matrixSummary.totalTasks }} · 赛事行 {{ matrixSummary.matchRows }} · 直播公推
          {{ matrixSummary.livePublic }} · 付费销售 {{ matrixSummary.paidSales }} · 红 {{ matrixSummary.red }} · 黑
          {{ matrixSummary.black }} · 待判定 {{ matrixSummary.unknown }}
        </div>
        <div class="tbl-wrap wt-matrix-table">
          <table>
            <thead>
              <tr>
                <th :colspan="5">赛事信息</th>
                <th v-for="auth in matrixAuthors" :key="auth.authorId" :colspan="4">
                  {{ auth.authorName || auth.authorId }}【{{ sheetIpGroupName }}-{{ sheetIpGroupLeaderName }}】
                </th>
              </tr>
              <tr>
                <th>日期</th>
                <th>场次</th>
                <th>赛事</th>
                <th>比赛名称</th>
                <th>比赛时间</th>
                <template v-for="auth in matrixAuthors" :key="'sub-' + auth.authorId">
                  <th>营销计划</th>
                  <th>直播时间</th>
                  <th>销售平台</th>
                  <th>红黑</th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in matrixTableRows" :key="line.key">
                <td>{{ line.workDate }}</td>
                <td class="num">{{ line.matchNo }}</td>
                <td>{{ line.competitionId }}</td>
                <td>{{ line.competitionName }}</td>
                <td>{{ line.matchTime || '—' }}</td>
                <template v-for="auth in matrixAuthors" :key="line.key + '-' + auth.authorId">
                  <td>{{ cellFor(line, auth.authorId)?.marketingPlanLabel || '—' }}</td>
                  <td>{{ cellFor(line, auth.authorId)?.liveLabel || '—' }}</td>
                  <td>{{ cellFor(line, auth.authorId)?.salesPlatformLabel || '—' }}</td>
                  <td>{{ cellFor(line, auth.authorId)?.winPredictionLabel || '—' }}</td>
                </template>
              </tr>
              <tr v-if="!matrixTableRows.length">
                <td :colspan="5 + matrixAuthors.length * 4">
                  <div class="empty"><div class="et">暂无矩阵数据</div></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'

type Row = {
  id?: number
  rowNo: number
  authorId: number
  authorName?: string
  marketingPlan: string
  salesPlatform: string
  rowStatus?: string
  generatedTaskIds?: number[]
  competitionId: string
  competitionName: string
  workDate: string
  isLive: number
  liveTime?: string
  winPrediction?: string
}

type ExecRow = {
  id: number
  competitionName: string
  marketingPlan: string
  authorId: number
  authorName: string
  nodeName: string
  assigneeName: string
  isLive: number
  liveTime: string
  status: string
  createdAt: string
}

type MatrixCell = {
  marketingPlanLabel: string
  liveLabel: string
  salesPlatformLabel: string
  winPredictionLabel: string
}

const tab = ref<'register' | 'execution' | 'matrix'>('register')
const ipGroupId = ref(1)
const workDate = ref('2026-10-06')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const sheetId = ref<number | null>(null)
const sheetStatus = ref('')
const sheetIpGroupName = ref('')
const sheetIpGroupLeaderName = ref('')
const rows = ref<Row[]>([])
const selectedIds = ref<number[]>([])
const execLoading = ref(false)
const execError = ref('')
const execMarketingPlan = ref('')
const executionRows = ref<ExecRow[]>([])

const editableRows = computed(() => rows.value.filter((r) => r.rowNo <= 10))

const allSelected = computed(
  () => editableRows.value.length > 0 && editableRows.value.every((r) => r.id && selectedIds.value.includes(r.id)),
)

function marketingPlanLabel(code: string) {
  if (code === 'LIVE_PUBLIC') return '直播公推'
  if (code === 'PAID_SALES') return '付费销售'
  return code || '—'
}

function salesPlatformLabel(code: string) {
  const map: Record<string, string> = {
    DOUYIN: '抖音',
    KUAISHOU: '快手',
    PRIVATE: '私域',
    NONE: '无',
  }
  return map[code] || code || '—'
}

function winPredictionLabel(code: string) {
  if (code === 'RED') return '红'
  if (code === 'BLACK') return '黑'
  return '待判定'
}

const matrixAuthors = computed(() => {
  const seen = new Map<number, { authorId: number; authorName: string }>()
  for (const r of editableRows.value) {
    if (r.authorId <= 0) continue
    if (!seen.has(r.authorId)) {
      seen.set(r.authorId, { authorId: r.authorId, authorName: r.authorName || String(r.authorId) })
    }
  }
  return [...seen.values()].sort((a, b) => a.authorId - b.authorId)
})

const matrixTableRows = computed(() => {
  const lines: {
    key: string
    workDate: string
    matchNo: number
    competitionId: string
    competitionName: string
    matchTime: string
    cells: Record<number, MatrixCell>
  }[] = []
  let matchNo = 0
  for (const r of editableRows.value) {
    if (r.authorId <= 0 || !r.competitionId) continue
    matchNo += 1
    const cell: MatrixCell = {
      marketingPlanLabel: marketingPlanLabel(r.marketingPlan),
      liveLabel: r.isLive ? r.liveTime || '—' : '—',
      salesPlatformLabel: salesPlatformLabel(r.salesPlatform),
      winPredictionLabel: winPredictionLabel(r.winPrediction || 'UNKNOWN'),
    }
    lines.push({
      key: `${r.rowNo}-${r.competitionId}`,
      workDate: r.workDate || workDate.value,
      matchNo,
      competitionId: r.competitionId,
      competitionName: r.competitionName || r.competitionId,
      matchTime: '',
      cells: { [r.authorId]: cell },
    })
  }
  return lines
})

const matrixSummary = computed(() => {
  const filled = editableRows.value.filter((r) => r.authorId > 0 && r.competitionId)
  let livePublic = 0
  let paidSales = 0
  let red = 0
  let black = 0
  let unknown = 0
  let totalTasks = 0
  for (const r of filled) {
    if (r.marketingPlan === 'LIVE_PUBLIC') livePublic += 1
    if (r.marketingPlan === 'PAID_SALES') paidSales += 1
    const wp = r.winPrediction || 'UNKNOWN'
    if (wp === 'RED') red += 1
    else if (wp === 'BLACK') black += 1
    else unknown += 1
    totalTasks += (r.generatedTaskIds || []).length
  }
  return {
    totalTasks,
    matchRows: filled.length,
    livePublic,
    paidSales,
    red,
    black,
    unknown,
  }
})

function cellFor(
  line: { cells: Record<number, MatrixCell> },
  authorId: number,
): MatrixCell | undefined {
  return line.cells[authorId]
}

function switchTab(next: 'register' | 'execution' | 'matrix') {
  tab.value = next
  if (next === 'execution') loadExecution()
  if (next === 'matrix') loadSheet()
}

function mapRow(raw: Record<string, unknown>): Row {
  const comps = (raw.competitions as Array<Record<string, string>>) || []
  const first = comps[0] || {}
  return {
    id: raw.id as number | undefined,
    rowNo: Number(raw.rowNo),
    authorId: Number(raw.authorId || 0),
    marketingPlan: String(raw.marketingPlan || 'LIVE_PUBLIC'),
    salesPlatform: String(raw.salesPlatform || 'NONE'),
    rowStatus: String(raw.rowStatus || 'DRAFT'),
    generatedTaskIds: (raw.generatedTaskIds as number[]) || [],
    competitionId: first.competitionId || '',
    competitionName: first.competitionName || '',
    workDate: String(raw.workDate || workDate.value),
    isLive: Number(raw.isLive || 0),
    liveTime: String(raw.liveTime || ''),
    winPrediction: String(raw.winPrediction || 'UNKNOWN'),
    authorName: String(raw.authorName || ''),
  }
}

function toggleAll(ev: Event) {
  const on = (ev.target as HTMLInputElement).checked
  selectedIds.value = on ? editableRows.value.map((r) => r.id).filter((id): id is number => !!id) : []
}

async function loadSheet() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/work-task/sheet', {
      params: { ipGroupId: ipGroupId.value, workDate: workDate.value },
    })
    if (data.code !== 0) {
      error.value = data.msg || '加载失败'
      return
    }
    sheetId.value = data.data.id
    sheetStatus.value = data.data.status
    sheetIpGroupName.value = String(data.data.ipGroupName || '')
    sheetIpGroupLeaderName.value = String(data.data.ipGroupLeaderName || '')
    rows.value = (data.data.assignments || []).map((item: Record<string, unknown>) => mapRow(item))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function loadExecution() {
  execLoading.value = true
  execError.value = ''
  try {
    const params: Record<string, unknown> = {
      pageNo: 1,
      pageSize: 100,
      onlyMine: false,
      ipGroupId: ipGroupId.value,
      workDate: workDate.value,
    }
    const { data } = await http.get('/content/task/page', { params })
    if (data.code !== 0) {
      execError.value = data.msg || '加载失败'
      executionRows.value = []
      return
    }
    let list = (data.data?.list || []) as ExecRow[]
    if (execMarketingPlan.value) {
      list = list.filter((r) => r.marketingPlan === execMarketingPlan.value)
    }
    executionRows.value = list
  } catch (e) {
    execError.value = errorMessage(e)
    executionRows.value = []
  } finally {
    execLoading.value = false
  }
}

function buildSavePayload() {
  const assignments = editableRows.value
    .filter((r) => r.authorId > 0 && r.competitionId)
    .map((r) => ({
      rowNo: r.rowNo,
      authorId: r.authorId,
      workDate: workDate.value,
      marketingPlan: r.marketingPlan,
      isLive: r.isLive,
      salesPlatform: r.salesPlatform,
      competitions: [
        {
          competitionId: r.competitionId,
          competitionName: r.competitionName,
          leagueName: '',
          matchTime: '',
        },
      ],
    }))
  return { ipGroupId: ipGroupId.value, workDate: workDate.value, assignments }
}

async function saveSheet() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await http.post('/content/work-task/sheet', buildSavePayload())
    if (data.code !== 0) {
      error.value = data.msg || '保存失败'
      return
    }
    sheetId.value = data.data.id
    sheetStatus.value = data.data.status
    sheetIpGroupName.value = String(data.data.ipGroupName || '')
    sheetIpGroupLeaderName.value = String(data.data.ipGroupLeaderName || '')
    rows.value = (data.data.assignments || []).map((item: Record<string, unknown>) => mapRow(item))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function confirmRows() {
  if (!sheetId.value) return
  saving.value = true
  try {
    const { data } = await http.post(`/content/work-task/${sheetId.value}/confirm`, {
      assignmentIds: selectedIds.value,
    })
    if (data.code !== 0) {
      error.value = data.msg || '确认失败'
      return
    }
    await loadSheet()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function withdrawRows() {
  if (!sheetId.value) return
  saving.value = true
  try {
    const { data } = await http.post(`/content/work-task/${sheetId.value}/withdraw`, {
      assignmentIds: selectedIds.value,
    })
    if (data.code !== 0) {
      error.value = data.msg || '撤回失败'
      return
    }
    await loadSheet()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

loadSheet()
</script>
