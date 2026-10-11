<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>组织人效</h1>
        <div class="sub">EFF · 页内 Tab 归属/盘点/看板 · /ims/eff</div>
      </div>
      <div class="acts">
        <button v-if="tab === 'board'" class="btn btn-sec btn-sm" type="button" data-testid="eff-export-month" @click="exportMonth">导出月报</button>
        <button v-if="tab === 'relation' && showCreate" class="btn btn-pri btn-sm" type="button" data-testid="eff-create" @click="openCreate">建立归属</button>
      </div>
    </div>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'relation' }" @click="switchTab('relation')">归属关系</div>
      <div class="tab" :class="{ on: tab === 'inventory' }" @click="switchTab('inventory')">人效盘点</div>
      <div class="tab" :class="{ on: tab === 'board' }" @click="switchTab('board')">人效看板</div>
    </div>

    <div v-if="coverage && tab === 'relation'" class="g4" style="margin: 12px 0">
      <div class="card stat">
        <span class="l">在职人数</span>
        <div class="n">{{ coverage.enabledUserCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">已覆盖主归属</span>
        <div class="n">{{ coverage.coveredUserCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">覆盖率</span>
        <div class="n">{{ coverage.coverageRate }}%</div>
        <div class="d">{{ coverage.canPublish ? '可发布盘点' : '未达 100%' }}</div>
      </div>
    </div>

    <template v-if="tab === 'relation'">
      <p v-if="listError" class="hint" style="color: var(--red)" data-testid="eff-list-error">{{ listError }}</p>
      <form class="qbar" @submit.prevent="loadRelations">
        <select v-model="filters.userId" style="width: 160px" data-testid="eff-filter-user">
          <option value="">全部人员</option>
          <option v-for="item in users" :key="item.id" :value="item.id">{{ userLabel(item) }}</option>
        </select>
        <select v-model="filters.relationType" style="width: 110px">
          <option value="">全部类型</option>
          <option value="PRIMARY">主归属</option>
          <option value="PART_TIME">兼职</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>用户</th>
                <th>类型</th>
                <th>归属目标</th>
                <th>分摊%</th>
                <th>生效自</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="7"><div class="empty"><div class="et">加载中</div></div></td></tr>
              <tr v-else-if="!relations.length"><td colspan="7"><div class="empty"><div class="et">暂无归属</div></div></td></tr>
              <tr v-for="row in relations" v-else :key="row.id">
                <td>{{ row.userName || row.userId }}</td>
                <td>{{ row.relationType }}</td>
                <td>{{ row.targetName }}</td>
                <td class="num">{{ row.shareRatio }}%</td>
                <td>{{ row.effectiveFrom }}</td>
                <td>{{ row.status }}</td>
                <td>
                  <button v-if="showCreate && row.status === 'ACTIVE'" class="btn btn-sec btn-sm" type="button" data-testid="eff-change" @click="openChange(row)">变更</button>
                  <button v-if="canDelete" class="btn btn-sec btn-sm" type="button" data-testid="eff-delete" @click="removeRelation(row)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'inventory'">
      <div v-if="inventory" class="g4" style="margin-top: 12px">
        <div class="card stat"><span class="l">周期</span><div class="n mono">{{ inventory.period }}</div></div>
        <div class="card stat"><span class="l">覆盖率</span><div class="n">{{ inventory.coverageRate }}%</div></div>
        <div class="card stat"><span class="l">状态</span><div class="n">{{ inventory.status }}</div></div>
        <div class="card stat"><span class="l">可发布</span><div class="n">{{ inventory.canPublish ? '是' : '否' }}</div></div>
      </div>
      <div class="card hint" style="padding: 16px; margin-top: 12px">{{ inventory?.note || '加载中…' }}</div>
    </template>

    <template v-else>
      <p class="hint" style="margin: 8px 0">IP 组维护在日常运营 · IP 组。人均指标按当月直播报告与内容作品、除以已建主归属人数；没有台账时显示「—」。</p>
      <p v-if="boardError" class="hint" style="color: var(--red)" data-testid="eff-board-error">{{ boardError }}</p>
      <div v-if="board" class="g4" style="margin-top: 12px">
        <div class="card stat" data-testid="eff-card-gmv"><span class="l">人均 GMV</span><div class="n">{{ moneyText(board.avgGmvPerCap) }}</div></div>
        <div class="card stat"><span class="l">人均场次/月</span><div class="n">{{ plainText(board.avgSessionsPerMonth) }}</div><div class="d">直播人员口径</div></div>
        <div class="card stat"><span class="l">人均作品/月</span><div class="n">{{ plainText(board.avgWorksPerMonth) }}</div><div class="d">内容作品口径</div></div>
        <div class="card stat"><span class="l">产能利用率</span><div class="n">{{ pctText(board.capacityUtilization) }}</div><div class="d">分摊&gt;100% {{ board.overShareUserCount }} 人 · 仅统计兼职合计</div></div>
      </div>
      <div v-if="board" class="card" data-testid="eff-board-chart" style="margin-top: 12px; padding: 12px">
        <b style="font-size: 13px">主归属 GMV</b>
        <div v-if="!chartBars.length" class="hint" data-testid="eff-chart-empty">—</div>
        <div v-for="bar in chartBars" :key="bar.label" class="rowline" style="margin-top: 8px">
          <span style="width: 140px">{{ bar.label }}</span>
          <span class="pg" style="width: 160px"><i :style="{ width: bar.width }"></i></span>
          <span class="num">{{ moneyText(bar.gmv) }}</span>
        </div>
      </div>
      <form v-if="board" class="qbar" style="margin-top: 12px" @submit.prevent="loadBoard">
        <input v-model="boardFilters.keyword" placeholder="姓名" style="width: 120px" data-testid="eff-filter-name" />
        <select v-model="boardFilters.dept" style="width: 140px" data-testid="eff-filter-dept">
          <option value="">全部部门</option>
          <option v-for="name in board.depts" :key="name" :value="name">{{ name }}</option>
        </select>
        <select v-model="boardFilters.shareStatus" style="width: 120px" data-testid="eff-filter-share">
          <option value="">分摊状态</option>
          <option value="NORMAL">正常</option>
          <option value="OVER">超 100%</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
        <button class="btn btn-sec btn-sm" type="button" @click="resetBoard">重置</button>
      </form>
      <p v-if="boardToast" class="hint" data-testid="eff-board-toast">{{ boardToast }}</p>
      <div v-if="board" class="tbl-block" style="margin-top: 8px">
        <div class="tbl-wrap">
          <table data-testid="eff-person-table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>部门</th>
                <th>主归属</th>
                <th>兼职归属</th>
                <th>主归属工时占比</th>
                <th>分摊合计</th>
                <th>人效得分</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!board.people.length"><td colspan="8"><div class="empty"><div class="et">暂无人员</div></div></td></tr>
              <tr v-for="row in board.people" :key="row.userId" data-testid="eff-person-row">
                <td>{{ row.userName }}</td>
                <td>{{ row.deptName || '—' }}</td>
                <td>{{ row.primaryName || '—' }}</td>
                <td>{{ row.partTimeNames.length ? row.partTimeNames.join('、') : '—' }}</td>
                <td class="num">{{ pctText(row.primaryShare) }}</td>
                <td class="num" :style="row.overShare ? 'color: var(--red)' : ''">{{ row.shareTotal }}%{{ row.overShare ? ' ⚠' : '' }}</td>
                <td class="num">{{ plainText(row.score) }}</td>
                <td><button class="btn btn-sec btn-sm" type="button" data-testid="eff-person-view" @click="openPerson(row)">查看</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-if="person" class="modal-mask" data-testid="eff-person-drawer" @click.self="person = null">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ person.userName }}</h3>
        <p class="hint">部门 {{ person.deptName || '—' }}</p>
        <p class="hint">主归属 {{ person.primaryName || '—' }}</p>
        <p class="hint">兼职归属 {{ person.partTimeNames.length ? person.partTimeNames.join('、') : '—' }}</p>
        <p class="hint">主归属工时占比 {{ pctText(person.primaryShare) }}</p>
        <p class="hint">分摊合计 {{ person.shareTotal }}%（仅统计兼职合计）</p>
        <p class="hint">人效得分 {{ plainText(person.score) }}</p>
        <p class="hint" data-testid="eff-person-comment">评价 {{ person.comment || '—' }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="person = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="changing" class="modal-mask" data-testid="eff-change-dialog" @click.self="changing = null">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">变更归属</h3>
        <p class="hint">{{ changing.userName || changing.userId }} · {{ changing.targetName }} · {{ changing.shareRatio }}%</p>
        <label class="fld">变更动作</label>
        <select v-model="changeForm.action" class="fld-in" data-testid="eff-change-action">
          <option value="TRANSFER">调岗</option>
          <option value="TO_PART_TIME">转兼职</option>
          <option value="TERMINATE">终止</option>
        </select>
        <template v-if="changeForm.action === 'TRANSFER'">
          <label class="fld">目标类型</label>
          <select v-model="changeForm.targetType" class="fld-in" @change="loadTargets(true)">
            <option value="IP_GROUP">IP 组</option>
            <option value="TEAM">小组</option>
            <option value="ACCOUNT">账号</option>
          </select>
          <label class="fld">新归属目标</label>
          <select v-model="changeForm.targetId" class="fld-in" data-testid="eff-change-target">
            <option value="">请选择目标</option>
            <option v-for="item in targets" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </template>
        <template v-if="changeForm.action === 'TO_PART_TIME'">
          <label class="fld">新分摊比例</label>
          <input v-model.number="changeForm.shareRatio" class="fld-in" type="number" />
        </template>
        <label class="fld">生效日</label>
        <input v-model="changeForm.effectiveDate" class="fld-in" type="date" data-testid="eff-change-date" />
        <p class="hint">旧关系在生效日封口，新关系自该日起生效，历史保留。</p>
        <p v-if="changeError" class="hint" style="color: var(--red)" data-testid="eff-change-error">{{ changeError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="changing = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="eff-change-save" @click="submitChange">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">建立归属</h3>
        <label class="fld">人员</label>
        <select v-model="form.userId" class="fld-in" data-testid="eff-form-user">
          <option value="">请选择人员</option>
          <option v-for="item in users" :key="item.id" :value="item.id">{{ userLabel(item) }}</option>
        </select>
        <label class="fld">类型</label>
        <select v-model="form.relationType" class="fld-in" @change="onTypeChange">
          <option value="PRIMARY">主归属</option>
          <option value="PART_TIME">兼职</option>
        </select>
        <label class="fld">目标类型</label>
        <select v-model="form.targetType" class="fld-in" data-testid="eff-form-target-type" @change="loadTargets(false)">
          <option value="IP_GROUP">IP 组</option>
          <option value="TEAM">小组</option>
          <option value="ACCOUNT">账号</option>
        </select>
        <label class="fld">归属目标</label>
        <select v-model="form.targetId" class="fld-in" data-testid="eff-form-target">
          <option value="">请选择目标</option>
          <option v-for="item in targets" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <label class="fld">分摊比例</label>
        <input v-model.number="form.shareRatio" class="fld-in" type="number" :readonly="form.relationType === 'PRIMARY'" />
        <p v-if="formError" class="hint" style="color: var(--red)" data-testid="eff-form-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type Relation = {
  id: number
  userId: number
  userName: string
  relationType: string
  targetType: string
  targetId: number
  targetName: string
  shareRatio: number
  effectiveFrom: string
  status: string
}

type NamedUser = { id: string; username?: string; nickname?: string }
type TargetOption = { id: string; name: string }

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const tab = ref('board')
const relations = ref<Relation[]>([])
const loading = ref(false)
const coverage = ref<{
  enabledUserCount: number
  coveredUserCount: number
  coverageRate: number
  canPublish: boolean
  canCreate?: boolean
  canDelete?: boolean
} | null>(null)
const users = ref<NamedUser[]>([])
const targets = ref<TargetOption[]>([])
const listError = ref('')
const changing = ref<Relation | null>(null)
const changeError = ref('')
const changeForm = reactive({
  action: 'TRANSFER',
  targetType: 'IP_GROUP',
  targetId: '',
  shareRatio: 60,
  effectiveDate: '',
})
type PersonRow = {
  userId: number
  userName: string
  deptName: string
  primaryName: string
  partTimeNames: string[]
  primaryShare: number | null
  partTimeSum: number
  shareTotal: number
  score: number | null
  comment: string
  overShare: boolean
  attributedGmv: number | null
}

type Board = {
  periodMonth: string
  avgGmvPerCap: number | null
  avgSessionsPerMonth: number | null
  avgWorksPerMonth: number | null
  capacityUtilization: number | null
  overShareUserCount: number
  people: PersonRow[]
  depts: string[]
  chart: { label: string; gmv: number }[]
}

const board = ref<Board | null>(null)
const boardError = ref('')
const boardToast = ref('')
const boardFilters = reactive({ keyword: '', dept: '', shareStatus: '' })
const person = ref<PersonRow | null>(null)
const inventory = ref<{
  period: string
  coverageRate: number
  status: string
  canPublish: boolean
  note: string
} | null>(null)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ userId: '', relationType: '' })
const form = reactive({
  userId: '',
  relationType: 'PRIMARY',
  targetType: 'IP_GROUP',
  targetName: '',
  targetId: '',
  shareRatio: 100,
})
const canCreate = computed(() => Boolean(coverage.value?.canCreate))
const canDelete = computed(() => Boolean(coverage.value?.canDelete))
const showCreate = computed(() => {
  if (!canCreate.value) return false
  if (userStore.permCodes.length === 0) return true
  return userStore.hasPerm('ims_eff_relation')
})

function tabFromRoute() {
  const q = String(route.query.tab || '')
  if (q === 'relation' || route.path.includes('relation')) return 'relation'
  if (q === 'inventory') return 'inventory'
  return 'board'
}

function switchTab(name: string) {
  tab.value = name
  router.replace({ path: '/ims/eff', query: name === 'board' ? {} : { tab: name } })
  if (name === 'relation') loadRelations()
  if (name === 'board') loadBoard()
  if (name === 'inventory') loadInventory()
}

async function loadCoverage() {
  try {
    const res = await http.get('/eff/relation/coverage')
    if (res.data.code === 0) coverage.value = res.data.data
  } catch (error) {
    coverage.value = null
    listError.value = errorMessage(error)
  }
}

function userLabel(item: NamedUser) {
  return item.nickname || item.username || item.id
}

function onTypeChange() {
  form.shareRatio = form.relationType === 'PRIMARY' ? 100 : 60
}

async function loadUsers() {
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    users.value = (res.data.data?.list || []) as NamedUser[]
  } catch (error) {
    formError.value = errorMessage(error)
  }
}

async function loadTargets(forChange = false) {
  const type = forChange ? changeForm.targetType : form.targetType
  if (forChange) changeForm.targetId = ''
  else form.targetId = ''
  targets.value = []
  try {
    if (type === 'ACCOUNT') {
      const res = await http.get('/corp/account/page', { params: { pageNo: 1, pageSize: 100 } })
      const list = (res.data.data?.list || []) as { id: string | number; accountName?: string; nickname?: string; accountNo?: string }[]
      targets.value = list.map((item) => ({
        id: String(item.id),
        name: item.accountName || item.nickname || item.accountNo || String(item.id),
      }))
      return
    }
    const res = await http.get('/ip-group/list', {
      params: { pageNo: 1, pageSize: 100, groupType: type === 'TEAM' ? 'SMALL' : 'BIG' },
    })
    const list = (res.data.data?.list || []) as { id: string | number; groupName?: string }[]
    targets.value = list.map((item) => ({ id: String(item.id), name: item.groupName || String(item.id) }))
  } catch (error) {
    const text = errorMessage(error)
    if (forChange) changeError.value = text
    else formError.value = text
  }
}

async function loadRelations() {
  loading.value = true
  listError.value = ''
  try {
    const res = await http.get('/eff/relation/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        userId: filters.userId || undefined,
        relationType: filters.relationType || undefined,
      },
    })
    if (res.data.code === 0) relations.value = res.data.data.list || []
  } catch (error) {
    relations.value = []
    listError.value = errorMessage(error)
  } finally {
    loading.value = false
  }
}

function moneyText(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `¥${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

function plainText(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return String(value)
}

function pctText(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${value}%`
}

const chartBars = computed(() => {
  const rows = board.value?.chart || []
  const max = Math.max(0, ...rows.map((item) => item.gmv))
  return rows.map((item) => ({
    ...item,
    width: max > 0 ? `${Math.max(4, Math.round((item.gmv / max) * 100))}%` : '0%',
  }))
})

function csvCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`
}

function exportMonth() {
  boardToast.value = ''
  const data = board.value
  if (!data) {
    boardToast.value = '看板尚未加载'
    return
  }
  const lines = [
    ['周期', data.periodMonth].map(csvCell).join(','),
    ['人均GMV', moneyText(data.avgGmvPerCap)].map(csvCell).join(','),
    ['人均场次/月', plainText(data.avgSessionsPerMonth)].map(csvCell).join(','),
    ['人均作品/月', plainText(data.avgWorksPerMonth)].map(csvCell).join(','),
    ['产能利用率', pctText(data.capacityUtilization)].map(csvCell).join(','),
    '',
    ['姓名', '部门', '主归属', '兼职归属', '主归属工时占比', '分摊合计', '人效得分', '评价'].map(csvCell).join(','),
    ...data.people.map((row) =>
      [
        row.userName,
        row.deptName || '—',
        row.primaryName || '—',
        row.partTimeNames.join('、') || '—',
        pctText(row.primaryShare),
        `${row.shareTotal}%`,
        plainText(row.score),
        row.comment || '—',
      ]
        .map(csvCell)
        .join(','),
    ),
  ]
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `组织人效月报-${data.periodMonth}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  boardToast.value = '月报已导出'
}

function openPerson(row: PersonRow) {
  person.value = row
}

function resetBoard() {
  boardFilters.keyword = ''
  boardFilters.dept = ''
  boardFilters.shareStatus = ''
  loadBoard()
}

async function loadBoard() {
  boardError.value = ''
  try {
    const res = await http.get('/eff/metrics/board', {
      params: {
        keyword: boardFilters.keyword || undefined,
        dept: boardFilters.dept || undefined,
        shareStatus: boardFilters.shareStatus || undefined,
      },
    })
    if (res.data.code === 0) board.value = res.data.data
  } catch (error) {
    boardError.value = errorMessage(error)
  }
}

async function loadInventory() {
  const res = await http.get('/eff/inventory/snapshot')
  if (res.data.code === 0) inventory.value = res.data.data
}

function openCreate() {
  formError.value = ''
  form.relationType = 'PRIMARY'
  form.shareRatio = 100
  changing.value = null
  showForm.value = true
  loadUsers()
  loadTargets(false)
}

function selectedTargetName() {
  return targets.value.find((item) => item.id === String(form.targetId))?.name || ''
}

async function submitCreate() {
  formError.value = ''
  if (!form.userId) {
    formError.value = '请选择人员'
    return
  }
  if (!form.targetId) {
    formError.value = '请选择归属目标'
    return
  }
  try {
    await http.post('/eff/relation', {
      userId: Number(form.userId),
      relationType: form.relationType,
      targetType: form.targetType,
      targetId: Number(form.targetId),
      targetName: selectedTargetName(),
      shareRatio: form.relationType === 'PRIMARY' ? 100 : form.shareRatio,
    })
    showForm.value = false
    await loadCoverage()
    await loadRelations()
    if (tab.value === 'board') await loadBoard()
  } catch (error) {
    formError.value = errorMessage(error)
  }
}

function openChange(row: Relation) {
  changing.value = row
  changeError.value = ''
  changeForm.action = 'TRANSFER'
  changeForm.targetType = row.targetType || 'IP_GROUP'
  changeForm.targetId = ''
  changeForm.shareRatio = row.relationType === 'PART_TIME' ? row.shareRatio : 60
  const next = new Date()
  next.setDate(next.getDate() + 1)
  const month = String(next.getMonth() + 1).padStart(2, '0')
  const day = String(next.getDate()).padStart(2, '0')
  changeForm.effectiveDate = `${next.getFullYear()}-${month}-${day}`
  loadTargets(true)
}

async function submitChange() {
  if (!changing.value) return
  changeError.value = ''
  const picked = targets.value.find((item) => item.id === String(changeForm.targetId))
  try {
    await http.put(`/eff/relation/${changing.value.id}`, {
      action: changeForm.action,
      newTargetType: changeForm.targetType,
      newTargetId: changeForm.targetId ? Number(changeForm.targetId) : undefined,
      newTargetName: picked?.name || '',
      newShareRatio: changeForm.action === 'TO_PART_TIME' ? changeForm.shareRatio : undefined,
      effectiveDate: changeForm.effectiveDate,
    })
    changing.value = null
    await loadRelations()
    await loadCoverage()
  } catch (error) {
    changeError.value = errorMessage(error)
  }
}

async function removeRelation(row: Relation) {
  if (!window.confirm('仅限误操作场景物理删除；正常人员变动请走【变更】')) return
  listError.value = ''
  try {
    await http.delete(`/eff/relation/${row.id}`)
    await loadRelations()
    await loadCoverage()
  } catch (error) {
    listError.value = errorMessage(error)
  }
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(async () => {
  tab.value = tabFromRoute()
  await loadCoverage()
  await loadUsers()
  if (tab.value === 'relation') await loadRelations()
  else if (tab.value === 'inventory') await loadInventory()
  else await loadBoard()
})
</script>
