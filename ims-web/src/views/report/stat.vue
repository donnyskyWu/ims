<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>完成率统计</h1>
        <div class="sub">REPORT-004 · BR-106 质量口径 · 09 REPORT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/submission')">填报单管理</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      分子 = 审核通过（APPROVED）填报单；分母 = 非草稿应报单数。目标 &gt;95%（BR-106）。
    </p>
    <form class="qbar" @submit.prevent="loadAll">
      <input v-model="statPeriod" placeholder="统计周期 YYYY-MM-DD" style="width: 160px" />
      <input v-model.number="templateId" type="number" placeholder="模板 ID" style="width: 100px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="button" @click="loadAll">刷新</button>
    </form>

    <div v-if="summary" class="g3" style="margin: 12px 0">
      <div class="card stat">
        <span class="l">总完成率</span>
        <div class="n" :style="{ color: rateColor(summary.totalCompleteRate) }">
          {{ summary.totalCompleteRate }}%
        </div>
        <div class="d">BR-106 目标 &gt;95%</div>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'template' }"
        @click="tab = 'template'"
      >
        按模板
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" @click="tab = 'dept'">
        按部门
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'trend' }" @click="tab = 'trend'">
        周期趋势
      </button>
    </div>

    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>

    <div v-if="tab === 'template'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>模板</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!summary?.byTemplate?.length">
              <td colspan="4"><div class="empty"><div class="et">暂无数据</div></div></td>
            </tr>
            <tr v-for="row in summary?.byTemplate || []" v-else :key="row.templateId">
              <td>{{ row.templateName }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td :style="{ color: rateColor(row.completeRate) }">{{ row.completeRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'dept'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>部门</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary?.byDept || []" :key="row.deptName">
              <td>{{ row.deptName }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td :style="{ color: rateColor(row.completeRate) }">{{ row.completeRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>周期</th>
              <th>应报</th>
              <th>已通过</th>
              <th>完成率</th>
              <th>退回率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!trend.length">
              <td colspan="5"><div class="empty"><div class="et">暂无趋势</div></div></td>
            </tr>
            <tr v-for="row in trend" v-else :key="row.statPeriod">
              <td class="mono">{{ row.statPeriod }}</td>
              <td class="num">{{ row.shouldCount }}</td>
              <td class="num">{{ row.approvedCount }}</td>
              <td>{{ row.completeRate }}%</td>
              <td>{{ row.rejectRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type Summary = {
  totalCompleteRate: number
  byTemplate: Array<{
    templateId: number
    templateName: string
    shouldCount: number
    approvedCount: number
    completeRate: number
  }>
  byDept: Array<{
    deptName: string
    shouldCount: number
    approvedCount: number
    completeRate: number
  }>
}

type TrendRow = {
  statPeriod: string
  shouldCount: number
  approvedCount: number
  completeRate: number
  rejectRate: number
}

const router = useRouter()
const statPeriod = ref('')
const templateId = ref<number | undefined>()
const summary = ref<Summary | null>(null)
const trend = ref<TrendRow[]>([])
const tab = ref<'template' | 'dept' | 'trend'>('template')
const loading = ref(false)
const error = ref('')

function go(path: string) {
  router.push(path)
}

function rateColor(rate: number) {
  if (rate >= 95) return 'var(--green)'
  if (rate >= 90) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {}
    if (statPeriod.value.trim()) params.statPeriod = statPeriod.value.trim()
    if (templateId.value) params.templateId = templateId.value
    const res = await http.get('/report/stat/complete-rate', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      summary.value = null
      return
    }
    summary.value = res.data.data

    const trendParams: Record<string, string | number> = { dateRange: '2026-01-01,2026-12-31' }
    if (templateId.value) trendParams.templateId = templateId.value
    const tr = await http.get('/report/stat/trend', { params: trendParams })
    if (tr.data.code === 0) trend.value = tr.data.data || []
  } catch {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.g3 {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.stat .l {
  font-size: 12px;
  color: var(--text2);
}
.stat .n {
  font-size: 28px;
  font-weight: 600;
  margin: 4px 0;
}
.stat .d {
  font-size: 11px;
  color: var(--text2);
}
.tabs .tab {
  background: none;
  border: none;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text2);
  border-bottom: 2px solid transparent;
}
.tabs .tab.on {
  color: var(--text);
  border-bottom-color: var(--blue);
  font-weight: 600;
}
</style>
