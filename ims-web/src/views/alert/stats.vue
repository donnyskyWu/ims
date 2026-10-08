<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预警统计</h1>
        <div class="sub">ALERT-004 · GET /alert/stats/overview · 响应时长 / 响应率 / 解决率</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <input v-model="start" data-testid="alert-stats-start" type="date" />
      <input v-model="end" data-testid="alert-stats-end" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
      <button class="btn btn-sec btn-sm" type="button" @click="clearRange">全部</button>
    </form>

    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div v-if="overview" class="g4" style="margin-top: 12px">
      <div class="card stat">
        <span class="l">预警总量</span>
        <div class="n" data-testid="alert-stats-total">{{ overview.totalAlertCount }}</div>
        <div class="d">当前筛选范围内</div>
      </div>
      <div class="card stat">
        <span class="l">响应时长</span>
        <div class="n" data-testid="alert-stats-avg-minutes">{{ overview.avgResponseMinutes }}</div>
        <div class="d">分钟 · 已响应记录从发生到最近处置</div>
      </div>
      <div class="card stat">
        <span class="l">响应率</span>
        <div class="n" data-testid="alert-stats-response-rate" :style="{ color: rateColor(overview.responseRate, 90) }">
          {{ overview.responseRate }}%
        </div>
        <div class="d">已响应 {{ overview.respondedCount }} / {{ overview.totalAlertCount }} · BR-112 &gt;90%</div>
      </div>
      <div class="card stat">
        <span class="l">解决率</span>
        <div class="n" data-testid="alert-stats-resolution-rate">{{ overview.resolutionRate }}%</div>
        <div class="d" data-testid="alert-stats-resolved-count">
          已解决 {{ overview.resolvedCount }} / {{ overview.totalAlertCount }}
        </div>
      </div>
    </div>

    <div v-if="overview" class="g4">
      <div class="card stat">
        <span class="l">送达率</span>
        <div class="n" data-testid="alert-stats-delivery-rate" :style="{ color: rateColor(overview.deliveryRate, 99) }">
          {{ overview.deliveryRate }}%
        </div>
        <div class="d">工作台已记录 · 不含钉钉/短信外发</div>
      </div>
      <div class="card stat">
        <span class="l">误报率</span>
        <div class="n" data-testid="alert-stats-false-rate" :style="{ color: overview.falseAlarmRate > 5 ? 'var(--orange, #d97706)' : undefined }">
          {{ overview.falseAlarmRate }}%
        </div>
        <div class="d">&gt;5% 提示复核阈值</div>
      </div>
      <div class="card stat">
        <span class="l">升级率</span>
        <div class="n" data-testid="alert-stats-escalate-rate">{{ overview.escalateRate }}%</div>
        <div class="d">无升级台账，固定 0</div>
      </div>
      <div class="card stat">
        <span class="l">级别分布</span>
        <div class="n" style="font-size: 16px; margin-top: 10px">
          <span data-testid="alert-stats-l1">L1 {{ overview.byLevel.L1 }}</span>
          ·
          <span data-testid="alert-stats-l2">L2 {{ overview.byLevel.L2 }}</span>
          ·
          <span data-testid="alert-stats-l3">L3 {{ overview.byLevel.L3 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Overview = {
  totalAlertCount: number
  byLevel: { L1: number; L2: number; L3: number }
  responseRate: number
  resolutionRate: number
  deliveryRate: number
  falseAlarmRate: number
  escalateRate: number
  avgResponseMinutes: number
  respondedCount: number
  resolvedCount: number
}

const overview = ref<Overview | null>(null)
const error = ref('')
const start = ref('')
const end = ref('')

function rateColor(value: number, target: number) {
  return value >= target ? 'var(--green, #15803d)' : 'var(--orange, #d97706)'
}

function clearRange() {
  start.value = ''
  end.value = ''
  load()
}

async function load() {
  error.value = ''
  const params: Record<string, string> = {}
  if (start.value && end.value) params.dateRange = `${start.value},${end.value}`
  else if (start.value || end.value) {
    error.value = '请同时填写起止日期'
    return
  }
  try {
    const res = await http.get('/alert/stats/overview', { params })
    overview.value = res.data.data
  } catch (err) {
    const body = err as { msg?: string }
    error.value = body?.msg || '加载失败'
    overview.value = null
  }
}

onMounted(load)
</script>
