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
      <div v-if="dashReady && !kpis.length" class="card" data-testid="home-kpi-empty">
        <div class="empty">
          <div class="et">{{ error || '暂无指标' }}</div>
          <div class="es">当前筛选下没有可展示的指标卡片</div>
        </div>
      </div>
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
        <div v-if="dashReady && !trend.length" class="empty" data-testid="home-trend-empty">
          <div class="et">暂无播放趋势</div>
        </div>
        <div v-else class="bars">
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
        <div v-if="!dashReady" class="empty"><div class="et">加载中</div></div>
        <div v-else-if="!todos.length" class="empty" data-testid="home-todo-empty"><div class="et">暂无待办</div></div>
        <div
          v-for="(row, idx) in todos"
          v-else
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
    <div class="card" style="margin-top: 16px" data-testid="home-ip-output">
      <div class="hd-row">
        <h3>IP 组产出</h3>
        <span class="csub">柱状占位 · 不请求 Football</span>
      </div>
      <div v-if="!ipGroupOutput.length" class="empty" data-testid="home-ip-output-empty">
        <div class="et">暂无 IP 组产出</div>
        <div class="es">本地统计桩，不汇总播放与互动</div>
      </div>
      <div v-else class="bars">
        <div
          v-for="(bar, idx) in ipGroupOutput"
          :key="idx"
          class="b"
          :style="{ height: `${Math.min(90, bar.value)}%` }"
          :title="bar.label"
        />
      </div>
    </div>
    <div class="sec">快捷入口</div>
    <div v-if="dashReady && !shortcuts.length" class="card" data-testid="home-shortcut-empty">
      <div class="empty">
        <div class="et">暂无可用快捷入口</div>
        <div class="es">当前账号没有可打开的快捷入口</div>
      </div>
    </div>
    <div v-else-if="shortcuts.length" style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px">
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
const ipGroupOutput = ref<{ label: string; value: number }[]>([])
const error = ref('')
const dashReady = ref(false)
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
    ipGroupOutput.value = data.ipGroupOutput || []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    dashReady.value = true
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
