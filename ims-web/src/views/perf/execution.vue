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
      状态 ADR-IMS-005 · canonical 七态 · P2 列表 Tag 四别名（草稿/计算中/已计算/已确认）
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
                  @click="confirmRow(row)"
                >确认</span>
                <span
                  v-if="row.status === 'REVIEWED' || row.status === 'CONFIRMED'"
                  class="btn-txt btn"
                  @click="issueRow(row)"
                >下发</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showAdjust" class="modal-mask" @click.self="showAdjust = false">
      <div class="modal card" style="max-width: 400px; padding: 20px">
        <h3 style="margin: 0 0 12px">人工调整 · {{ adjustTarget?.recordNo }}</h3>
        <p class="hint">基础分 {{ adjustTarget?.calcBaseScore ?? adjustTarget?.totalScore }} · ±20% 上限</p>
        <div class="fld">
          <label>调整分值（±）</label>
          <input v-model.number="adjustForm.manualAdjustment" type="number" step="0.1" />
        </div>
        <div class="fld">
          <label>说明</label>
          <input v-model="adjustForm.remark" placeholder="场次补录等" />
        </div>
        <p v-if="adjustError" class="hint" style="color: var(--red)">{{ adjustError }}</p>
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
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
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
}

const route = useRoute()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const showAdjust = ref(false)
const adjustTarget = ref<Row | null>(null)
const adjustError = ref('')
const adjustForm = reactive({ manualAdjustment: 0, remark: '' })
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
  } catch {
    formError.value = '网络错误'
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

async function confirmRow(row: Row) {
  const res = await http.post(`/perf/execution/${row.id}/confirm`)
  if (res.data.code !== 0) {
    alert(res.data.msg || '确认失败')
    return
  }
  await loadList()
}

async function issueRow(row: Row) {
  const res = await http.put(`/perf/execution/${row.id}/issue`)
  if (res.data.code !== 0) {
    alert(res.data.msg || '下发失败')
    return
  }
  await loadList()
}

function openAdjust(row: Row) {
  adjustTarget.value = row
  adjustForm.manualAdjustment = row.manualAdjustment ?? 0
  adjustForm.remark = ''
  adjustError.value = ''
  showAdjust.value = true
}

async function submitAdjust() {
  if (!adjustTarget.value) return
  adjustError.value = ''
  try {
    const res = await http.put(`/perf/execution/${adjustTarget.value.id}/adjust`, {
      manualAdjustment: adjustForm.manualAdjustment,
      remark: adjustForm.remark,
    })
    if (res.data.code !== 0) {
      adjustError.value = res.data.msg || '调整失败'
      return
    }
    showAdjust.value = false
    await loadList()
  } catch {
    adjustError.value = '网络错误'
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
