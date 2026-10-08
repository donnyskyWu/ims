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
import { onMounted, reactive, ref } from 'vue'
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

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ status: '' })

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

onMounted(loadList)
</script>
