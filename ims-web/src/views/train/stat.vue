<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>培训统计看板</h1>
        <div class="sub">TRAIN-003 · BR-102 完成率 / 逾期督办 · 02 TRAIN</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/train/task">学习任务</router-link>
    </div>

    <form class="qbar" @submit.prevent="loadFinishRate">
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
      <button type="button" class="tab" :class="{ on: tab === 'finish' }" @click="tab = 'finish'">
        完成率总览
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" @click="tab = 'dept'">
        部门统计
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'rank' }" @click="tab = 'rank'">
        时长排行
      </button>
      <button type="button" class="tab" :class="{ on: tab === 'overdue' }" @click="tab = 'overdue'">
        逾期督办
      </button>
    </div>

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
                <td colspan="5"><div class="empty"><div class="et">暂无数据</div></div></td>
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

    <div v-else class="hint" style="margin-top: 16px">
      {{ tabHint }} · 本切片仅交付「完成率总览」Tab（#49）；其余 Tab 待后续切片接 API。
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '../../api/http'

type FinishRow = {
  taskNo: string
  taskName: string
  assignedCount: number
  finishedCount: number
  finishRate: number
}
type DeptRow = {
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
  byDept: DeptRow[]
  byPerson: PersonRow[]
}

const tab = ref<'finish' | 'dept' | 'rank' | 'overdue'>('finish')
const rangePreset = ref<'7' | '30' | 'custom'>('30')
const customRange = ref('')
const finish = ref<FinishResp | null>(null)
const loading = ref(false)
const error = ref('')
const personPage = ref(1)
const personPageSize = 10

const tabHint = computed(() => {
  if (tab.value === 'dept') return '部门统计（TRN-S-R1 日汇总）'
  if (tab.value === 'rank') return '时长排行'
  return '逾期督办（TRN-T-R2）'
})

const personTotalPages = computed(() => {
  const n = finish.value?.byPerson?.length || 0
  return Math.max(1, Math.ceil(n / personPageSize))
})

const personPageRows = computed(() => {
  const all = finish.value?.byPerson || []
  const start = (personPage.value - 1) * personPageSize
  return all.slice(start, start + personPageSize)
})

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
  loadFinishRate()
}

function rateColor(rate: number) {
  if (rate >= 90) return 'var(--green)'
  if (rate >= 70) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

async function loadFinishRate() {
  if (customRange.value.trim()) {
    rangePreset.value = 'custom'
  }
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string> = {}
    const dr = activeDateRange()
    if (dr) params.dateRange = dr
    const res = await http.get('/train/stat/finish-rate', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      finish.value = null
      return
    }
    finish.value = res.data.data
    personPage.value = 1
  } catch {
    error.value = '网络错误'
    finish.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => loadFinishRate())
</script>
