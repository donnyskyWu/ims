<template>
  <div class="page">
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
        <option value="R6">内容运营 R6</option>
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
      <div v-for="row in rows" :key="row.id" class="card hov scheme-card">
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <span class="mono num" style="color: var(--blue); font-size: 12px">{{ row.schemeNo }}</span>
          <span class="sw" :class="{ on: row.status === 'ACTIVE' }"><i></i></span>
        </div>
        <h3 style="font-size: 15px; margin: 0 0 6px">{{ row.templateName }}</h3>
        <div class="csub">{{ row.metricSummary || '—' }}</div>
        <div class="rowline" style="margin-top: 12px; flex-wrap: wrap; gap: 8px">
          <span class="tag" :style="periodStyle(row.periodType)">
            <span class="dot"></span>{{ periodLabel(row.periodType) }}
          </span>
          <span class="csub">{{ row.positionLabel }}</span>
          <span class="csub">{{ row.evaluateeCount }} 名被考核人</span>
          <span class="chip">{{ row.status === 'ACTIVE' ? '生效中' : '已停用' }}</span>
        </div>
        <div class="rowline" style="margin-top: 12px; gap: 8px">
          <button
            class="btn btn-pri btn-sm"
            type="button"
            :disabled="row.status !== 'ACTIVE'"
            @click="launchExec(row)"
          >
            发起考核
          </button>
          <button
            v-if="row.status !== 'ACTIVE'"
            class="btn btn-sec btn-sm"
            type="button"
            @click="activateRow(row)"
          >
            启用
          </button>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 520px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建考核方案</h3>
        <div class="fld"><label>方案名称</label><input v-model="form.templateName" /></div>
        <div class="fld">
          <label>适用岗位</label>
          <select v-model="form.positionCode">
            <option value="R5">直播运营 R5</option>
            <option value="R6">内容运营 R6</option>
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
}

const router = useRouter()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
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

function launchExec(row: Row) {
  router.push({
    path: '/ims/perf/execution',
    query: { schemeId: String(row.id), schemeName: row.templateName },
  })
}

async function activateRow(row: Row) {
  try {
    const res = await http.post(`/perf/scheme/${row.id}/activate`)
    if (res.data.code !== 0) {
      error.value = res.data.msg || '启用失败'
      return
    }
    await loadList()
  } catch {
    error.value = '网络错误'
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
</style>
