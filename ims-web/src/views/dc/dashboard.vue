<template>
  <div class="page" :class="{ screen }" data-testid="dc-dash-page">
    <div class="pg-h">
      <div>
        <h1>全链路数据看板</h1>
        <div class="sub">DC-003 · /ims/dc/dashboard · 布局设计 · BR-210 新鲜度</div>
      </div>
      <div v-if="!screen" class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-screen" @click="screen = true">大屏模式</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="dc-dash-manage" @click="openManage">看板管理</button>
      </div>
      <div v-else class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-screen-exit" @click="screen = false">退出大屏</button>
      </div>
    </div>

    <form v-if="!screen" class="qbar" @submit.prevent="loadAll">
      <input v-model="statPeriod" data-testid="dc-dash-period" placeholder="yyyy-MM" style="width: 120px" />
      <select v-model="selectedId" data-testid="dc-dash-select" style="width: 180px" @change="onSelect">
        <option value="">{{ dashboards.length ? '选择看板' : '暂无启用看板' }}</option>
        <option v-for="row in dashboards" :key="row.id" :value="String(row.id)">
          {{ row.dashboardName }}{{ row.status === 'DISABLED' ? '（停用）' : '' }}
        </option>
      </select>
      <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-refresh" @click="loadAll">刷新</button>
    </form>

    <p v-if="error" class="hint" data-testid="dc-dash-error" style="color: var(--red)">{{ error }}</p>
    <p
      v-if="freshness"
      class="hint"
      data-testid="dc-dash-asof"
      :style="freshness.isAlarm ? { color: 'var(--red)', fontWeight: '600' } : undefined"
    >
      数据截至 {{ freshness.dataAsOf }}
      （{{ freshness.isAlarm ? '超过 1 小时' : '1h 内 ✓' }} · 聚合延迟 {{ freshness.businessToDwsDelayMinutes }} 分钟 / 目标 {{ freshness.target }}）
    </p>
    <p v-if="freshness?.isAlarm" class="hint" data-testid="dc-dash-fresh-alarm" style="color: var(--red)">
      同步延迟超过 1 小时（BR-210）。当前展示最后成功快照。
    </p>
    <p v-if="health?.isAlarm" class="hint" data-testid="dc-dash-health-alarm" style="color: var(--red)">
      资产关联完整率 {{ health.assetRelationCompleteRate }}%，低于目标 {{ health.target }}%（BR-208）。
    </p>
    <p v-if="!dashboards.length && loaded" class="hint" data-testid="dc-dash-empty">暂无启用看板，请由管理员配置布局。</p>

    <div v-if="overview" class="metrics">
      <div class="card stat"><span class="l">总GMV</span><div class="n" data-testid="dc-dash-gmv">{{ money(overview.totalGmv) }}</div></div>
      <div class="card stat"><span class="l">总成本</span><div class="n" data-testid="dc-dash-cost">{{ money(overview.totalCost) }}</div></div>
      <div class="card stat"><span class="l">净利润</span><div class="n" data-testid="dc-dash-profit">{{ money(overview.netProfit) }}</div></div>
      <div class="card stat"><span class="l">场次数</span><div class="n" data-testid="dc-dash-sessions">{{ overview.sessionCount }}</div></div>
      <div class="card stat"><span class="l">账号数</span><div class="n" data-testid="dc-dash-accounts">{{ overview.accountCount }}</div></div>
      <div class="card stat"><span class="l">资产数</span><div class="n" data-testid="dc-dash-assets">{{ overview.assetCount }}</div></div>
    </div>

    <div
      v-if="health"
      class="card"
      data-testid="dc-dash-health"
      :style="health.isAlarm ? { borderColor: 'var(--red)' } : undefined"
    >
      <b>链路健康度</b>
      <div class="health-row">
        <span data-testid="dc-dash-health-rate">资产关联完整率 {{ health.assetRelationCompleteRate }}%（目标 &gt; {{ health.target }}% {{ health.isAlarm ? '告警' : '✓' }}）</span>
        <span>账号线上化率 {{ health.accountDigitizationRate }}%</span>
        <span>台账留痕率 {{ health.ledgerTraceRate }}%</span>
      </div>
      <p v-if="health.trend?.length" class="hint" data-testid="dc-dash-health-trend">近 {{ health.trend.length }} 天有场次的完整率已汇总</p>
    </div>

    <div class="tabs" style="margin: 12px 0 8px">
      <button
        v-for="dim in dimensions"
        :key="dim.value"
        type="button"
        class="tab"
        :class="{ on: dimensionType === dim.value }"
        :data-testid="`dc-dash-dim-${dim.value}`"
        @click="switchDim(dim.value)"
      >
        {{ dim.label }}
      </button>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="dc-dash-dimension">
          <thead>
            <tr><th>维度值</th><th>GMV</th><th>净利润</th><th>场次数</th></tr>
          </thead>
          <tbody>
            <tr v-if="!flatRows.length">
              <td colspan="4"><div class="empty"><div class="et">本周期暂无维度数据</div></div></td>
            </tr>
            <tr v-for="row in flatRows" :key="row.key" :data-testid="row.depth ? 'dc-dash-dim-child' : 'dc-dash-dim-row'">
              <td :style="row.depth ? { paddingLeft: '28px' } : undefined">{{ row.dimensionLabel }}</td>
              <td class="num">{{ money(row.gmv) }}</td>
              <td class="num">{{ money(row.netProfit) }}</td>
              <td class="num">{{ row.sessionCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="card" data-testid="dc-dash-layout-preview" style="margin-top: 12px">
      <b>当前布局 · {{ selected.dashboardName }}</b>
      <p class="hint">刷新策略 {{ selected.refreshCron }}</p>
      <div v-if="selected.layoutConfig?.length" class="preview">
        <div
          v-for="widget in selected.layoutConfig"
          :key="widget.widgetKey"
          class="preview-item"
          data-testid="dc-dash-preview-widget"
          :data-widget-type="widget.widgetType"
        >
          {{ widgetLabel(widget.widgetType) }}
          <small>{{ widget.position.w }}×{{ widget.position.h }}</small>
        </div>
      </div>
      <p v-else class="hint">该看板还没有组件</p>
    </div>

    <div class="card" style="margin-top: 12px">
      <b>同步任务</b>
      <div class="tbl-wrap">
        <table data-testid="dc-dash-freshness">
          <thead>
            <tr><th>任务名</th><th>最近运行</th><th>状态</th><th>延迟分钟</th></tr>
          </thead>
          <tbody>
            <tr v-if="!freshness">
              <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr
              v-for="task in freshness?.syncTaskStatus || []"
              :key="task.taskName"
              data-testid="dc-dash-sync-row"
              :data-status="task.status"
            >
              <td>{{ task.taskName }}</td>
              <td class="mono">{{ task.lastRunAt }}</td>
              <td :style="{ color: statusColor(task.status), fontWeight: '600' }">{{ task.status }}</td>
              <td class="num">{{ task.delayMinutes }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="failedTask" class="hint" data-testid="dc-dash-sync-failed" style="color: var(--red)">
        同步失败，断点续传中。当前展示最后成功快照 {{ freshness?.dataAsOf }}。
      </p>
    </div>

    <div v-if="drawer" class="drawer-mask" @click.self="drawer = false">
      <div class="drawer on" data-testid="dc-dash-drawer" style="width: 960px">
        <div class="drawer-h">
          <b>{{ editingId ? '编辑布局' : '创建看板' }}</b>
          <button type="button" class="btn btn-sec btn-sm" data-testid="dc-dash-drawer-close" @click="drawer = false">关闭</button>
        </div>
        <div class="drawer-b designer">
          <div class="palette">
            <div class="hint">组件库</div>
            <button
              v-for="item in widgetTypes"
              :key="item.type"
              type="button"
              class="btn btn-sec"
              draggable="true"
              :data-testid="`dc-dash-widget-${item.type}`"
              @dragstart="onDragStart(item.type)"
              @click="addWidget(item.type)"
            >
              {{ item.label }}
            </button>
            <p class="hint">点击或拖入右侧画布</p>
          </div>
          <div class="canvas-col">
            <div class="qbar" style="margin-bottom: 10px">
              <input v-model="form.name" data-testid="dc-dash-name" placeholder="看板名称" maxlength="64" style="width: 180px" />
              <input v-model="form.cron" data-testid="dc-dash-cron" placeholder="0 * * * *" style="width: 140px" />
              <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-new" @click="resetForm">新建</button>
            </div>
            <div
              class="canvas"
              data-testid="dc-dash-canvas"
              @dragover.prevent
              @drop="onDrop"
            >
              <button
                v-for="(widget, index) in form.layout"
                :key="widget.widgetKey"
                type="button"
                class="canvas-item"
                :class="{ on: selectedWidget === index }"
                data-testid="dc-dash-canvas-widget"
                :data-widget-type="widget.widgetType"
                :style="widgetStyle(widget)"
                @click="selectedWidget = index"
              >
                {{ widgetLabel(widget.widgetType) }}
              </button>
              <div v-if="!form.layout.length" class="empty"><div class="et">从左侧放入组件</div></div>
            </div>
            <div v-if="activeWidget" class="props" data-testid="dc-dash-props">
              <div class="hint">{{ widgetLabel(activeWidget.widgetType) }} · {{ activeWidget.widgetKey }}</div>
              <label>指标 key <input v-model="activeWidget.config.metricKey" data-testid="dc-dash-metric-key" /></label>
              <label>x <input v-model.number="activeWidget.position.x" type="number" data-testid="dc-dash-pos-x" /></label>
              <label>y <input v-model.number="activeWidget.position.y" type="number" data-testid="dc-dash-pos-y" /></label>
              <label>w <input v-model.number="activeWidget.position.w" type="number" data-testid="dc-dash-pos-w" /></label>
              <label>h <input v-model.number="activeWidget.position.h" type="number" data-testid="dc-dash-pos-h" /></label>
              <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-remove-widget" @click="removeWidget">移除</button>
            </div>
          </div>
        </div>
        <div class="drawer-f">
          <span v-if="saveNote" class="hint" data-testid="dc-dash-save-note">{{ saveNote }}</span>
          <button class="btn btn-pri btn-sm" type="button" data-testid="dc-dash-save" @click="saveLayout">保存布局</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type WidgetType = 'METRIC_CARD' | 'TREND_CHART' | 'RANK_LIST' | 'HEALTH_PANEL'
type Widget = {
  widgetKey: string
  widgetType: WidgetType
  position: { x: number; y: number; w: number; h: number }
  config: Record<string, unknown>
}
type Dashboard = {
  id: number
  dashboardName: string
  status: 'ENABLED' | 'DISABLED'
  refreshCron: string
  refreshedAt: string
  layoutConfig: Widget[]
}
type Overview = {
  totalGmv: number | null
  totalCost: number | null
  netProfit: number | null
  sessionCount: number
  accountCount: number
  assetCount: number
}
type Health = {
  assetRelationCompleteRate: number
  target: number
  isAlarm: boolean
  trend: Array<{ statDate: string; completeRate: number }>
  accountDigitizationRate: number
  ledgerTraceRate: number
}
type Freshness = {
  businessToDwsDelayMinutes: number
  target: number
  isAlarm: boolean
  dataAsOf: string
  syncTaskStatus: Array<{ taskName: string; lastRunAt: string; status: string; delayMinutes: number }>
}
type DimRow = {
  dimensionValue: string
  dimensionLabel: string
  gmv: number | null
  netProfit: number | null
  sessionCount: number
  children?: Array<{ dimensionValue: string; gmv: number | null; netProfit: number | null; sessionCount: number }>
}

const widgetTypes: Array<{ type: WidgetType; label: string }> = [
  { type: 'METRIC_CARD', label: '指标卡' },
  { type: 'TREND_CHART', label: '趋势图' },
  { type: 'RANK_LIST', label: '排行' },
  { type: 'HEALTH_PANEL', label: '健康面板' },
]
const dimensions = [
  { value: 'PLATFORM', label: '平台' },
  { value: 'ACCOUNT', label: '账号' },
  { value: 'IP_GROUP', label: 'IP组' },
  { value: 'TEAM', label: '团队' },
  { value: 'REALNAME', label: '实名人' },
]

const statPeriod = ref(currentPeriod())
const dimensionType = ref('PLATFORM')
const dashboards = ref<Dashboard[]>([])
const selectedId = ref('')
const overview = ref<Overview | null>(null)
const health = ref<Health | null>(null)
const freshness = ref<Freshness | null>(null)
const dimensionRows = ref<DimRow[]>([])
const error = ref('')
const loaded = ref(false)
const screen = ref(false)
const drawer = ref(false)
const editingId = ref<number | null>(null)
const selectedWidget = ref(-1)
const saveNote = ref('')
const dragType = ref<WidgetType | ''>('')
const form = ref({ name: '', cron: '0 * * * *', layout: [] as Widget[] })

const selected = computed(() => dashboards.value.find((row) => String(row.id) === selectedId.value) || null)
const activeWidget = computed(() => form.value.layout[selectedWidget.value] || null)
const failedTask = computed(() => freshness.value?.syncTaskStatus.some((task) => task.status === 'FAILED'))
const flatRows = computed(() => {
  const rows: Array<DimRow & { key: string; depth: number }> = []
  dimensionRows.value.forEach((row) => {
    rows.push({ ...row, key: row.dimensionValue, depth: 0 })
    ;(row.children || []).forEach((child) => {
      rows.push({
        dimensionValue: child.dimensionValue,
        dimensionLabel: child.dimensionValue,
        gmv: child.gmv,
        netProfit: child.netProfit,
        sessionCount: child.sessionCount,
        key: `${row.dimensionValue}:${child.dimensionValue}`,
        depth: 1,
      })
    })
  })
  return rows
})

function currentPeriod() {
  const text = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit' }).format(new Date())
  return text.slice(0, 7)
}

function money(value: number | null | undefined) {
  if (value == null) return '—'
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function widgetLabel(type: string) {
  return widgetTypes.find((item) => item.type === type)?.label || type
}

function statusColor(status: string) {
  if (status === 'FAILED') return 'var(--red)'
  if (status === 'DELAYED') return 'var(--orange)'
  return 'var(--green)'
}

function widgetStyle(widget: Widget) {
  return {
    gridColumn: `${widget.position.x + 1} / span ${Math.max(widget.position.w, 1)}`,
    gridRow: `${widget.position.y + 1} / span ${Math.max(widget.position.h, 1)}`,
  }
}

function resetForm() {
  editingId.value = null
  selectedWidget.value = -1
  saveNote.value = ''
  form.value = { name: '', cron: '0 * * * *', layout: [] }
}

function fillForm(row: Dashboard) {
  editingId.value = row.id
  selectedWidget.value = row.layoutConfig.length ? 0 : -1
  form.value = {
    name: row.dashboardName,
    cron: row.refreshCron || '0 * * * *',
    layout: row.layoutConfig.map((widget) => ({
      widgetKey: widget.widgetKey,
      widgetType: widget.widgetType,
      position: { ...widget.position },
      config: { ...(widget.config || {}) },
    })),
  }
}

function addWidget(type: WidgetType) {
  const y = form.value.layout.reduce((max, widget) => Math.max(max, widget.position.y + widget.position.h), 0)
  form.value.layout.push({
    widgetKey: `${type}-${Date.now()}`,
    widgetType: type,
    position: { x: 0, y, w: type === 'METRIC_CARD' ? 3 : 6, h: 2 },
    config: { metricKey: type === 'HEALTH_PANEL' ? 'assetRelationCompleteRate' : 'totalGmv' },
  })
  selectedWidget.value = form.value.layout.length - 1
}

function removeWidget() {
  if (selectedWidget.value < 0) return
  form.value.layout.splice(selectedWidget.value, 1)
  selectedWidget.value = form.value.layout.length ? 0 : -1
}

function onDragStart(type: WidgetType) {
  dragType.value = type
}

function onDrop() {
  if (!dragType.value) return
  addWidget(dragType.value)
  dragType.value = ''
}

function openManage() {
  drawer.value = true
  saveNote.value = ''
  const current = selected.value
  if (current) fillForm(current)
  else resetForm()
}

function onSelect() {
  const current = selected.value
  if (drawer.value && current) fillForm(current)
}

async function loadDimension() {
  const res = await http.get('/dc/dashboard/dimension', {
    params: { statPeriod: statPeriod.value, dimensionType: dimensionType.value },
  })
  dimensionRows.value = Array.isArray(res.data.data) ? res.data.data : []
}

async function switchDim(value: string) {
  dimensionType.value = value
  try {
    await loadDimension()
    error.value = ''
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function loadAll() {
  error.value = ''
  const period = statPeriod.value
  try {
    const [listRes, freshRes, overRes, healthRes] = await Promise.all([
      http.get('/dc/dashboard/list'),
      http.get('/dc/dashboard/freshness'),
      http.get('/dc/dashboard/overview', { params: { statPeriod: period } }),
      http.get('/dc/dashboard/health'),
    ])
    dashboards.value = Array.isArray(listRes.data.data) ? listRes.data.data : []
    freshness.value = freshRes.data.data
    overview.value = overRes.data.data
    health.value = healthRes.data.data
    if (!dashboards.value.some((row) => String(row.id) === selectedId.value)) {
      const enabled = dashboards.value.find((row) => row.status === 'ENABLED') || dashboards.value[0]
      selectedId.value = enabled ? String(enabled.id) : ''
    }
    await loadDimension()
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loaded.value = true
  }
}

async function saveLayout() {
  saveNote.value = ''
  const payload = {
    dashboardName: form.value.name.trim(),
    refreshCron: form.value.cron.trim() || '0 * * * *',
    layoutConfig: form.value.layout.map((widget) => ({
      widgetKey: widget.widgetKey,
      widgetType: widget.widgetType,
      position: {
        x: Number(widget.position.x) || 0,
        y: Number(widget.position.y) || 0,
        w: Number(widget.position.w) || 1,
        h: Number(widget.position.h) || 1,
      },
      config: widget.config || {},
    })),
  }
  try {
    if (editingId.value) {
      await http.put(`/dc/dashboard/${editingId.value}`, payload)
      saveNote.value = '布局已保存'
    } else {
      const res = await http.post('/dc/dashboard', payload)
      editingId.value = res.data.data.id
      selectedId.value = String(res.data.data.id)
      saveNote.value = '看板已创建'
    }
    await loadAll()
    const current = dashboards.value.find((row) => row.id === editingId.value)
    if (current) fillForm(current)
  } catch (err) {
    saveNote.value = errorMessage(err)
  }
}

onMounted(loadAll)
</script>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin: 12px 0; }
.health-row { display: flex; gap: 18px; margin-top: 8px; flex-wrap: wrap; }
.preview { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.preview-item { border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; min-width: 120px; }
.preview-item small { display: block; color: var(--text2); }
.drawer-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); z-index: 90; }
.designer { display: grid; grid-template-columns: 28% 1fr; gap: 16px; min-height: 420px; }
.palette { display: flex; flex-direction: column; gap: 8px; }
.canvas { display: grid; grid-template-columns: repeat(12, 1fr); grid-auto-rows: 42px; gap: 6px; min-height: 280px; border: 1px dashed var(--line2); border-radius: 8px; padding: 8px; }
.canvas-item { border: 1px solid var(--line); background: #fff; border-radius: 8px; text-align: left; padding: 6px 8px; }
.canvas-item.on { border-color: var(--blue); background: rgba(0, 113, 227, 0.08); }
.props { display: flex; flex-wrap: wrap; gap: 8px; align-items: end; margin-top: 10px; }
.props label { display: flex; flex-direction: column; font-size: 12px; color: var(--text2); }
.props input { width: 120px; }
.page.screen { position: fixed; inset: 0; z-index: 80; background: #fff; overflow: auto; padding: 24px; }
@media (max-width: 900px) {
  .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .designer { grid-template-columns: 1fr; }
}
</style>
