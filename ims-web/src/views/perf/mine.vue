<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>我的绩效</h1>
        <div class="sub">只显示本人已发布结果。发布前不可见（1157）。</div>
      </div>
      <label>
        周期
        <input v-model="period" data-testid="perf-mine-period" type="month" @change="load" />
      </label>
    </div>

    <div v-if="empty" data-testid="perf-mine-empty" class="empty">
      <div class="et">{{ empty }}</div>
    </div>

    <template v-else-if="mine">
      <p class="hint">{{ mine.periodMonth }} · {{ mine.deptName }}</p>
      <p data-testid="perf-mine-score" style="font-size: 32px; font-weight: 600">{{ scoreText(mine.totalScore) }}</p>
      <p>
        <span class="tag" data-testid="perf-mine-grade">{{ gradeText(mine.gradeLevel) }}</span>
        <span data-testid="perf-mine-rank"> 部门排名 第 {{ mine.rankInDept || rank?.rankNo || '—' }} / {{ rank?.deptTotalCount || '—' }}</span>
      </p>
      <p v-if="rank" data-testid="perf-mine-distribution" class="hint">
        部门分布：优秀 {{ rank.scoreDistribution.excellent }} · 合格 {{ rank.scoreDistribution.qualified }} · 待改进
        {{ rank.scoreDistribution.improve }}
      </p>
      <table>
        <thead>
          <tr>
            <th>指标</th>
            <th>原始值</th>
            <th>得分</th>
            <th>权重</th>
            <th>贡献分</th>
            <th>取数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in mine.details || []" :key="item.metricCode" data-testid="perf-mine-detail">
            <td>{{ item.metricName }}</td>
            <td class="num">{{ item.metricValue ?? '—' }}</td>
            <td class="num">{{ scoreText(item.metricScore) }}</td>
            <td class="num">{{ item.weight }}%</td>
            <td class="num">{{ scoreText(item.contribution) }}</td>
            <td>{{ item.dataStatus }}</td>
          </tr>
        </tbody>
      </table>
      <p class="hint">合计 {{ scoreText(mine.totalScore) }} = Σ(得分 × 权重)。绩效结果为周期快照，如有疑问请联系 HR/运营总监。</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http } from '../../api/http'

type Detail = {
  metricCode: string
  metricName: string
  metricValue: number | string | null
  metricScore: number
  weight: number
  dataStatus: string
  contribution: number
}
type Mine = {
  periodMonth: string
  userName: string
  deptName: string
  totalScore: number | null
  rankInDept: number | null
  gradeLevel: string
  details?: Detail[]
}
type Rank = {
  rankNo: number
  gradeLevel: string
  deptTotalCount: number
  scoreDistribution: { excellent: number; qualified: number; improve: number }
}

const period = ref(previousMonth())
const mine = ref<Mine | null>(null)
const rank = ref<Rank | null>(null)
const empty = ref('')

function previousMonth() {
  const now = new Date()
  const cursor = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  return `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`
}

function scoreText(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(2)
}

function gradeText(level: string) {
  if (level === 'EXCELLENT') return '优秀 ≥85'
  if (level === 'QUALIFIED') return '合格 60~84'
  if (level === 'IMPROVE') return '待改进 <60'
  return '—'
}

async function load() {
  empty.value = ''
  mine.value = null
  rank.value = null
  try {
    const res = await http.get(`/perf/calc/${period.value}/mine`)
    if (!res.data.data) {
      empty.value = '本期无绩效记录（入职当月按在职天数折算）'
      return
    }
    mine.value = res.data.data
  } catch (err) {
    const body = err as { code?: number; msg?: string }
    if (body.code === 1157) {
      empty.value = '本期绩效尚未发布，发布后可见（1157 · PER-C-R3）'
      return
    }
    empty.value = body.msg || '加载失败'
    return
  }
  try {
    const res = await http.get('/perf/rank/mine', { params: { periodMonth: period.value } })
    rank.value = res.data.data
  } catch {
    rank.value = null
  }
}

void load()
</script>
