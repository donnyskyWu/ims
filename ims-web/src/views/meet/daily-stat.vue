<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>提交率统计</h1>
        <div class="sub">MEET-003 · BR-103 按时提交率 · 03 MEET</div>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      分子 = 22:00 前提交（isOnTime）；分母 = 已提交日报（非草稿）。目标 &gt;95%（BR-103）。
    </p>
    <form class="qbar" @submit.prevent="load">
      <input v-model="dateFrom" placeholder="起始 yyyy-MM-dd" style="width: 140px" />
      <input v-model="dateTo" placeholder="结束 yyyy-MM-dd" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div v-if="summary" class="g3" style="margin: 12px 0">
      <div class="card stat">
        <span class="l">总按时率</span>
        <div class="n" :style="{ color: rateColor(summary.totalOnTimeRate) }">
          {{ summary.totalOnTimeRate }}%
        </div>
        <div class="d">{{ summary.dateFrom }} ~ {{ summary.dateTo }}</div>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab" :class="{ on: tab === 'dept' }" @click="tab = 'dept'">按部门</button>
      <button type="button" class="tab" :class="{ on: tab === 'person' }" @click="tab = 'person'">按人员</button>
      <button type="button" class="tab" :class="{ on: tab === 'trend' }" @click="tab = 'trend'">日趋势</button>
    </div>

    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>

    <div v-if="tab === 'dept'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>部门</th>
              <th>按时率</th>
              <th>提交率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="3"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!summary?.byDept?.length">
              <td colspan="3"><div class="empty"><div class="et">暂无数据</div></div></td>
            </tr>
            <tr v-for="row in summary?.byDept || []" v-else :key="row.deptId">
              <td>{{ row.deptName }}</td>
              <td :style="{ color: rateColor(row.onTimeRate) }">{{ row.onTimeRate }}%</td>
              <td>{{ row.submitRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'person'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>姓名</th>
              <th>部门</th>
              <th>应报天</th>
              <th>已报天</th>
              <th>按时天</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary?.byPerson || []" :key="row.userId">
              <td>{{ row.userName }}</td>
              <td>{{ row.deptName }}</td>
              <td class="num">{{ row.shouldDays }}</td>
              <td class="num">{{ row.submittedDays }}</td>
              <td class="num">{{ row.onTimeDays }}</td>
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
              <th>日期</th>
              <th>按时率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in summary?.trend || []" :key="row.date">
              <td class="mono">{{ row.date }}</td>
              <td :style="{ color: rateColor(row.onTimeRate) }">{{ row.onTimeRate }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Summary = {
  totalOnTimeRate: number
  dateFrom: string
  dateTo: string
  byDept: { deptId: number; deptName: string; onTimeRate: number; submitRate: number }[]
  byPerson: {
    userId: number
    userName: string
    deptName: string
    shouldDays: number
    submittedDays: number
    onTimeDays: number
  }[]
  trend: { date: string; onTimeRate: number }[]
}

const summary = ref<Summary | null>(null)
const loading = ref(false)
const error = ref('')
const tab = ref<'dept' | 'person' | 'trend'>('dept')
const dateFrom = ref('')
const dateTo = ref('')

function rateColor(rate: number) {
  if (rate >= 95) return 'var(--green)'
  if (rate >= 80) return 'var(--orange, #e6a23c)'
  return 'var(--red)'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/meet/stat/on-time-rate', {
      params: {
        dateFrom: dateFrom.value || undefined,
        dateTo: dateTo.value || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      summary.value = null
      return
    }
    summary.value = res.data.data
  } catch {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
