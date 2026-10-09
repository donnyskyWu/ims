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
      <select v-model="filters.grade" data-testid="perf-result-grade-filter" style="width: 130px">
        <option value="">全部等级</option>
        <option value="S">S ≥90</option>
        <option value="A">A 80-89</option>
        <option value="B">B 70-79</option>
        <option value="C">C 60-69</option>
        <option value="D">D &lt;60</option>
      </select>
      <input v-model="filters.evaluateeName" data-testid="perf-result-name" placeholder="被考核人" style="width: 120px" />
      <input v-model="filters.recordNo" data-testid="perf-result-no" placeholder="单号" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="perf-result-query">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="perf-result-reset" @click="resetFilters">重置</button>
    </form>
    <p class="hint" data-testid="perf-result-dist">{{ distText }}</p>
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
              <td colspan="7">
                <div class="empty" data-testid="perf-result-empty"><div class="et">{{ emptyText }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" data-testid="perf-result-row">
              <td class="mono">{{ row.recordNo }}</td>
              <td>{{ row.evaluateeName }}</td>
              <td>{{ row.position }}</td>
              <td>{{ row.cycleDisplay }}</td>
              <td class="num">{{ row.totalScore ?? '—' }}</td>
              <td><span class="tag" data-testid="perf-result-grade">{{ row.gradeEdge || row.grade }}</span></td>
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
  gradeEdge?: string
  status: string
}

type GradeCounts = { S: number; A: number; B: number; C: number; D: number }

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const exportNote = ref('')
const counts = ref<GradeCounts>({ S: 0, A: 0, B: 0, C: 0, D: 0 })
const filters = reactive({ status: '', periodType: '', grade: '', evaluateeName: '', recordNo: '' })

const filtered = computed(
  () => !!(filters.status || filters.periodType || filters.grade || filters.evaluateeName.trim() || filters.recordNo.trim()),
)

const emptyText = computed(() => {
  if (error.value) return error.value
  if (filtered.value) return '当前筛选没有考核结果'
  return '暂无可阅考核结果'
})

const distText = computed(() => {
  const item = counts.value
  return `等级分布 S ${item.S} · A ${item.A} · B ${item.B} · C ${item.C} · D ${item.D}（边界 90 / 80 / 70 / 60）`
})

function listParams() {
  return {
    pageNo: 1,
    pageSize: 50,
    status: filters.status || undefined,
    periodType: filters.periodType || undefined,
    grade: filters.grade || undefined,
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
      counts.value = { S: 0, A: 0, B: 0, C: 0, D: 0 }
      return
    }
    rows.value = res.data.data?.list || []
    counts.value = res.data.data?.gradeCounts || { S: 0, A: 0, B: 0, C: 0, D: 0 }
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

onMounted(loadList)
</script>
