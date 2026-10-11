<template>
  <div class="page">
    <div class="toasts" aria-live="polite">
      <div
        v-if="toast"
        class="toast"
        :class="toastKind === 'warn' ? 't-warn' : 't-success'"
        data-testid="scheme-toast"
      >
        {{ toast }}
      </div>
    </div>
    <div class="pg-h">
      <div>
        <h1>考核方案</h1>
        <div class="sub">FR-M3-001 · /admin-api/ims/perf/scheme · 05 PERF</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建方案</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 12px">
      主路径：考核方案 → 执行考核 → 考核结果（对齐 OPS M3 · 指标权重合计 100%）
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.templateName" data-testid="perf-scheme-name" placeholder="方案名称" style="width: 160px" />
      <select v-model="filters.positionCode" style="width: 130px">
        <option value="">全部岗位</option>
        <option value="R5">直播运营 R5</option>
        <option value="R6">短视频运营 R6</option>
        <option value="R2">行政管理 R2</option>
      </select>
      <select v-model="filters.periodType" style="width: 110px">
        <option value="">全部周期</option>
        <option value="MONTHLY">月度</option>
        <option value="QUARTERLY">季度</option>
        <option value="HALF_YEAR">半年度</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ACTIVE">生效中</option>
        <option value="INACTIVE">已停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>

    <div v-if="loading" class="empty" style="margin-top: 24px"><div class="et">加载中</div></div>
    <div v-else-if="error" class="empty" style="margin-top: 24px"><div class="et">{{ error }}</div></div>
    <div v-else-if="!rows.length" class="empty" data-testid="perf-scheme-empty" style="margin-top: 24px">
      <div class="et">{{ schemeEmpty }}</div>
    </div>
    <div v-else class="scheme-grid">
      <div v-for="row in rows" :key="row.id" class="card hov scheme-card" :data-testid="`scheme-card-${row.id}`">
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <span class="mono num" style="color: var(--blue); font-size: 12px">{{ row.schemeNo }}</span>
          <button
            class="sw"
            :class="{ on: row.status === 'ACTIVE' }"
            type="button"
            data-testid="scheme-toggle"
            :aria-label="row.status === 'ACTIVE' ? '停用方案' : '启用方案'"
            @click="toggleStatus(row)"
          >
            <i></i>
          </button>
        </div>
        <h3 style="font-size: 15px; margin: 0 0 6px">{{ row.templateName }}</h3>
        <div class="csub">{{ row.metricSummary || '—' }}</div>
        <div class="rowline" style="margin-top: 12px; flex-wrap: wrap; gap: 8px">
          <span class="tag" :style="periodStyle(row.periodType)">
            <span class="dot"></span>{{ periodLabel(row.periodType) }}
          </span>
          <span class="csub">{{ row.positionLabel }}</span>
          <span class="csub">{{ row.evaluateeCount }} 名被考核人</span>
          <span class="chip" data-testid="scheme-status">{{ row.status === 'ACTIVE' ? '生效中' : '已停用' }}</span>
        </div>
        <div class="rowline" style="margin-top: 12px; gap: 8px">
          <button class="btn btn-sec btn-sm" type="button" data-testid="scheme-edit-metrics" @click="openEdit(row)">
            编辑指标
          </button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="scheme-launch"
            :style="row.status === 'ACTIVE' ? undefined : { opacity: 0.45 }"
            @click="launchExec(row)"
          >
            发起考核
          </button>
        </div>
      </div>
    </div>

    <ProtoDrawer :open="editOpen" :title="editTitle" width="640px" @close="editOpen = false">
      <p class="hint">勾选指标并填写权重。权重合计须为 100%，否则返回 1154。</p>
      <div v-if="!editItems.length" class="empty"><div class="et">请先在指标配置中创建指标</div></div>
      <div v-else class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>选用</th>
              <th>指标</th>
              <th>权重（%）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in editItems" :key="item.metricId">
              <td>
                <input v-model="item.checked" type="checkbox" :data-testid="`scheme-check-${item.metricCode}`" />
              </td>
              <td>
                {{ item.metricName }}
                <div class="csub mono">{{ item.metricCode }}</div>
              </td>
              <td>
                <input
                  v-model="item.weight"
                  :data-testid="`scheme-weight-${item.metricCode}`"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  style="width: 120px"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        data-testid="scheme-weight-total"
        class="hint"
        :style="{ color: editWeightOk ? 'inherit' : 'var(--red)', marginTop: '10px' }"
      >
        Σ 权重 = {{ editTotal }}%
      </p>
      <p v-if="editError" data-testid="scheme-edit-error" class="hint" style="color: var(--red)">{{ editError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="editOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="scheme-edit-save" @click="submitEdit">保存</button>
      </template>
    </ProtoDrawer>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 520px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建考核方案</h3>
        <div class="fld"><label>方案名称</label><input v-model="form.templateName" /></div>
        <div class="fld">
          <label>适用岗位</label>
          <select v-model="form.positionCode">
            <option value="R5">直播运营 R5</option>
            <option value="R6">短视频运营 R6</option>
            <option value="R2">行政管理 R2</option>
          </select>
        </div>
        <div class="fld">
          <label>考核周期</label>
          <select v-model="form.periodType">
            <option value="MONTHLY">月度</option>
            <option value="QUARTERLY">季度</option>
            <option value="HALF_YEAR">半年度</option>
          </select>
        </div>
        <div class="fld"><label>指标摘要</label><input v-model="form.metricSummary" placeholder="开播场次 · GMV · …" /></div>
        <div class="fld"><label>被考核人规模</label><input v-model.number="form.evaluateeCount" type="number" min="0" /></div>
        <div class="fld">
          <label>示例指标（权重各 50%）</label>
          <input v-model="form.metricA" placeholder="指标 A" />
          <input v-model="form.metricB" placeholder="指标 B" style="margin-top: 6px" />
        </div>
        <label class="hint" style="display: flex; align-items: center; gap: 8px; margin-top: 8px">
          <input v-model="form.activate" type="checkbox" /> 保存后立即启用（同岗位其他方案将停用）
        </label>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
        <p v-if="formError" class="hint" style="color: var(--red); margin-top: 8px">{{ formError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type SchemeItem = { metricId?: number; metricName: string; weight: number; calcRule?: string }
type Row = {
  id: number
  schemeNo: string
  templateName: string
  positionCode: string
  positionLabel: string
  periodType: string
  status: string
  metricSummary: string
  evaluateeCount: number
  itemCount: number
  items?: SchemeItem[]
}
type MetricOpt = { id: number; metricCode: string; metricName: string; status: string }
type EditItem = { metricId: number; metricCode: string; metricName: string; checked: boolean; weight: string }

const router = useRouter()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const toast = ref('')
const toastKind = ref<'success' | 'warn'>('success')
const editOpen = ref(false)
const editTitle = ref('编辑指标')
const editSchemeId = ref(0)
const editItems = ref<EditItem[]>([])
const editError = ref('')
const catalog = ref<MetricOpt[]>([])
const filters = reactive({ templateName: '', positionCode: '', periodType: '', status: '' })
const schemeFiltered = computed(
  () => !!(filters.templateName.trim() || filters.positionCode || filters.periodType || filters.status),
)
const schemeEmpty = computed(() =>
  schemeFiltered.value ? '当前筛选下暂无考核方案' : '暂无考核方案',
)
const form = reactive({
  templateName: '',
  positionCode: 'R5',
  periodType: 'QUARTERLY',
  metricSummary: '',
  evaluateeCount: 0,
  metricA: '核心指标 A',
  metricB: '核心指标 B',
  activate: true,
})

function periodLabel(period: string) {
  const map: Record<string, string> = {
    MONTHLY: '月度',
    QUARTERLY: '季度',
    HALF_YEAR: '半年度',
    WEEKLY: '周度',
    YEAR: '年度',
  }
  return map[period] || period
}

function periodStyle(period: string) {
  if (period === 'MONTHLY') return { background: 'rgba(255,149,0,.12)', color: '#c46a00' }
  if (period === 'HALF_YEAR') return { background: 'rgba(90,200,250,.12)', color: '#0e7fb8' }
  return { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
}

let schemeSeq = 0
async function loadList() {
  const seq = ++schemeSeq
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 24 }
    if (filters.templateName) params.templateName = filters.templateName
    if (filters.positionCode) params.positionCode = filters.positionCode
    if (filters.periodType) params.periodType = filters.periodType
    if (filters.status) params.status = filters.status
    const res = await http.get('/perf/scheme/list', { params })
    if (seq !== schemeSeq) return
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    if (seq !== schemeSeq) return
    error.value = '网络错误'
    rows.value = []
  } finally {
    if (seq === schemeSeq) loading.value = false
  }
}

function resetFilters() {
  filters.templateName = ''
  filters.positionCode = ''
  filters.periodType = ''
  filters.status = ''
  loadList()
}

function openCreate() {
  form.templateName = ''
  form.positionCode = 'R5'
  form.periodType = 'QUARTERLY'
  form.metricSummary = ''
  form.evaluateeCount = 0
  form.metricA = '核心指标 A'
  form.metricB = '核心指标 B'
  form.activate = true
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  if (!form.templateName.trim()) {
    formError.value = '请填写方案名称'
    return
  }
  if (!form.metricA.trim() || !form.metricB.trim()) {
    formError.value = '请填写两项示例指标'
    return
  }
  try {
    const res = await http.post('/perf/scheme', {
      templateName: form.templateName.trim(),
      positionCode: form.positionCode,
      periodType: form.periodType,
      metricSummary: form.metricSummary.trim(),
      evaluateeCount: form.evaluateeCount || 0,
      activate: form.activate,
      items: [
        { metricName: form.metricA.trim(), weight: 50, calcRule: 'AUTO' },
        { metricName: form.metricB.trim(), weight: 50, calcRule: 'AUTO' },
      ],
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    showForm.value = false
    await loadList()
  } catch {
    formError.value = '网络错误'
  }
}

const editTotal = computed(() => {
  let sum = 0
  for (const item of editItems.value) {
    if (!item.checked) continue
    const raw = Number(item.weight)
    if (Number.isFinite(raw)) sum += raw
  }
  return Math.round(sum * 100) / 100
})
const editWeightOk = computed(() => Math.abs(editTotal.value - 100) < 0.001)

function showToast(message: string, kind: 'success' | 'warn' = 'success') {
  toastKind.value = kind
  toast.value = message
}

function rejectText(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    return `${body.code ?? ''} ${body.msg || ''}`.trim()
  }
  return '网络错误'
}

function launchExec(row: Row) {
  if (row.status !== 'ACTIVE') {
    showToast('方案已停用，需启用后发起', 'warn')
    return
  }
  router.push({
    path: '/ims/perf/execution',
    query: { schemeId: String(row.id), schemeName: row.templateName },
  })
}

async function loadCatalog() {
  const res = await http.get('/perf/metric/list', { params: { pageNo: 1, pageSize: 100 } })
  catalog.value = (res.data.data.list || []).filter(
    (item: MetricOpt) => item.status === 'ENABLED' && item.metricCode !== 'COMPETE_SUBMIT_RATE',
  )
}

async function openEdit(row: Row) {
  editError.value = ''
  editSchemeId.value = row.id
  editTitle.value = `编辑指标 · ${row.templateName}`
  try {
    await loadCatalog()
  } catch (err) {
    editError.value = rejectText(err)
  }
  const saved = row.items || []
  editItems.value = catalog.value.map((metric) => {
    const hit = saved.find((item) => item.metricId === metric.id || item.metricName === metric.metricName)
    return {
      metricId: metric.id,
      metricCode: metric.metricCode,
      metricName: metric.metricName,
      checked: !!hit,
      weight: hit ? String(hit.weight) : '',
    }
  })
  editOpen.value = true
}

async function submitEdit() {
  editError.value = ''
  const items = editItems.value
    .filter((item) => item.checked)
    .map((item) => ({
      metricId: item.metricId,
      metricName: item.metricName,
      weight: Number(item.weight),
      calcRule: 'AUTO',
    }))
  try {
    await http.put(`/perf/scheme/${editSchemeId.value}`, { items })
    editOpen.value = false
    showToast('方案已保存')
    await loadList()
  } catch (err) {
    editError.value = rejectText(err)
  }
}

async function toggleStatus(row: Row) {
  const turningOff = row.status === 'ACTIVE'
  try {
    await http.post(`/perf/scheme/${row.id}/${turningOff ? 'deactivate' : 'activate'}`)
    showToast(turningOff ? '方案已停用' : '方案已启用')
    await loadList()
  } catch (err) {
    showToast(rejectText(err), 'warn')
  }
}

onMounted(loadList)
</script>

<style scoped>
.scheme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.scheme-card {
  padding: 16px;
}
button.sw {
  border: 0;
}
</style>
