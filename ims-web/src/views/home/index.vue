<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>运营仪表盘</h1>
        <div class="sub">IP 组筛选、核心指标、待办与快捷入口（HOME-001）</div>
      </div>
      <div class="acts">
        <input v-model.number="ipGroupId" type="number" placeholder="IP 组 id" style="width: 120px" />
        <select v-model="rangeDays" style="width: 110px">
          <option :value="7">近 7 天</option>
          <option :value="30">近 30 天</option>
        </select>
        <button class="btn btn-pri btn-sm" type="button" @click="loadDashboard">刷新</button>
      </div>
    </div>
    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>
    <div class="g4">
      <div
        v-for="kpi in kpis"
        :key="kpi.key"
        class="card stat hov"
        @click="onKpiClick(kpi.key)"
      >
        <span class="l">{{ kpi.label }}</span>
        <div class="n">{{ kpi.value }}</div>
        <div v-if="kpi.wow" class="d">{{ kpi.wow }}</div>
      </div>
    </div>
    <div class="g2" style="margin-top: 16px">
      <div class="card">
        <div class="hd-row">
          <h3>播放 / 互动</h3>
          <span class="csub">占位趋势 · 不请求 Football</span>
        </div>
        <div class="bars">
          <div
            v-for="(pt, idx) in trend"
            :key="idx"
            class="b"
            :style="{ height: `${Math.min(90, pt.play)}%` }"
          />
        </div>
      </div>
      <div class="card">
        <div class="hd-row">
          <h3>待办聚合</h3>
          <span class="csub">不请求 OPS</span>
        </div>
        <div v-if="!todos.length" class="empty"><div class="et">暂无待办</div></div>
        <div
          v-for="(row, idx) in todos"
          :key="idx"
          class="mg-i"
          style="border-radius: 8px; cursor: pointer"
          @click="go(row.url)"
        >
          <div>
            <div class="mt">{{ row.title }}</div>
            <div class="md">{{ row.type }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="sec">快捷入口</div>
    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px">
      <div
        v-for="sc in shortcuts"
        :key="sc.code"
        class="card hov"
        style="padding: 13px 8px; text-align: center; box-shadow: none; border: 1px solid var(--line); cursor: pointer"
        @click="go(sc.route)"
      >
        <div style="font-size: 12px; font-weight: 500">{{ sc.name }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()
const kpis = ref<{ key: string; label: string; value: string; wow?: string }[]>([])
const todos = ref<{ type: string; title: string; bizId: string; url: string }[]>([])
const shortcuts = ref<{ code: string; name: string; route: string }[]>([])
const trend = ref<{ label: string; play: number; engage: number }[]>([])
const error = ref('')
const ipGroupId = ref<number | null>(null)
const rangeDays = ref(7)

function dateParams() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - rangeDays.value)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { dateFrom: fmt(start), dateTo: fmt(end) }
}

async function loadDashboard() {
  error.value = ''
  try {
    const params: Record<string, string | number> = { ...dateParams() }
    if (ipGroupId.value) params.ipGroupId = ipGroupId.value
    const res = await http.get('/home/dashboard', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      return
    }
    const data = res.data.data
    kpis.value = data.kpis || []
    todos.value = data.todos || []
    shortcuts.value = data.shortcuts || []
    trend.value = data.trendPlayEngage || []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  }
}

function go(path: string) {
  router.push(path)
}

function onKpiClick(key: string) {
  const map: Record<string, string> = {
    accounts: '/ims/corp/account/douyin',
    worksToday: '/ims/collect/log',
    pendingTodos: '/ims/workbench',
    collectAlert: '/ims/collect/log',
  }
  if (map[key]) go(map[key])
}

onMounted(loadDashboard)
</script>
