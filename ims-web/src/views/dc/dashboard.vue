<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>全链路数据看板</h1>
        <div class="sub">DC-003 · /ims/dc/dashboard · 经营总览 / 链路健康度 / 维度下钻</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="dc-dash-manage" @click="openManage">看板管理</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/dc/trace">返回穿透查询</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <label class="fld" style="width: auto">
        周期
        <input v-model="period" data-testid="dc-dash-period" type="month" @change="load" />
      </label>
      <span
        data-testid="dc-dash-as-of"
        class="hint"
        :data-alarm="freshness?.isAlarm ? '1' : '0'"
        :style="freshness?.isAlarm ? { color: 'var(--red)', fontWeight: '600' } : undefined"
      >数据截至 {{ overview?.dataAsOf || '—' }}</span>
      <span
        data-testid="dc-dash-asof"
        class="hint"
        :data-alarm="freshness?.isAlarm ? '1' : '0'"
        :style="freshness?.isAlarm ? { color: 'var(--red)', fontWeight: '600' } : undefined"
      >数据截至 {{ freshness?.dataAsOf || overview?.dataAsOf || '—' }}</span>
      <select v-model="selectedId" data-testid="dc-dash-select" style="width: 180px" @change="onSelect">
        <option value="">未选看板</option>
        <option v-for="row in dashboards" :key="row.id" :value="String(row.id)">{{ row.dashboardName }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-dash-refresh">刷新</button>
    </form>

    <p v-if="error" class="hint" data-testid="dc-dash-error" style="color: var(--red)">{{ error }}</p>
    <p v-if="ready && !hasEnabled" class="hint" data-testid="dc-dash-empty-board">
      暂无启用看板，请联系管理员配置（R1/R4）
    </p>
    <p
      v-if="freshness?.isAlarm"
      class="hint"
      data-testid="dc-dash-fresh-alert"
      style="color: var(--red); font-weight: 600"
    >
      <template v-if="syncFailed">同步失败，断点续传中（V3-A2）；当前展示最后成功快照 {{ freshness?.dataAsOf }}</template>
      <template v-else>数据新鲜度超过 1 小时（BR-210），延迟 {{ freshness?.businessToDwsDelayMinutes }} 分钟</template>
    </p>
    <p
      v-if="health?.isAlarm"
      class="hint"
      data-testid="dc-dash-health-alert"
      style="color: var(--red); font-weight: 600"
    >
      资产关联完整率 {{ health.assetRelationCompleteRate }}%，低于目标 98%（BR-208/DC-D-R3），请核查资产-账号-场次关联
    </p>

    <div v-if="overview" class="dash-grid" data-testid="dc-dash-overview">
      <div class="card stat">
        <span class="l">总 GMV</span>
        <div class="n" data-testid="dc-dash-gmv">{{ money(overview.totalGmv) }}</div>
      </div>
      <div class="card stat">
        <span class="l">总成本</span>
        <div class="n" data-testid="dc-dash-cost">{{ money(overview.totalCost) }}</div>
      </div>
      <div class="card stat">
        <span class="l">净利润</span>
        <div class="n" data-testid="dc-dash-profit" :style="neg(overview.netProfit)">{{ money(overview.netProfit) }}</div>
      </div>
      <div class="card stat">
        <span class="l">场次数</span>
        <div class="n" data-testid="dc-dash-sessions">{{ overview.sessionCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">账号数</span>
        <div class="n" data-testid="dc-dash-accounts">{{ overview.accountCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">资产数</span>
        <div class="n" data-testid="dc-dash-assets">{{ overview.assetCount }}</div>
      </div>
    </div>

    <div
      v-if="health"
      class="card"
      data-testid="dc-dash-health"
      :data-alarm="health.isAlarm ? '1' : '0'"
      :style="health.isAlarm ? { outline: '1px solid var(--red)', marginTop: '12px' } : { marginTop: '12px' }"
    >
      <div class="dash-grid">
        <div class="stat">
          <span class="l">资产关联完整率</span>
          <div
            class="n"
            data-testid="dc-dash-complete-rate"
            :style="health.isAlarm ? { color: 'var(--red)' } : undefined"
          >
            {{ health.assetRelationCompleteRate }}%
          </div>
          <div class="d">{{ health.isAlarm ? '低于目标' : '达标' }} · 目标 &gt; {{ health.target }}%</div>
        </div>
        <div class="stat">
          <span class="l">账号线上化率</span>
          <div class="n" data-testid="dc-dash-digit-rate">{{ health.accountDigitizationRate }}%</div>
          <div class="d">场次账号已在账号台账</div>
        </div>
        <div class="stat">
          <span class="l">台账留痕率</span>
          <div class="n" data-testid="dc-dash-ledger-rate">{{ health.ledgerTraceRate }}%</div>
          <div class="d">已写下播报告的场次</div>
        </div>
      </div>
      <div class="tbl-block" data-testid="dc-dash-health-trend" style="margin-top: 8px">
        <p class="hint">近窗每日完整率</p>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>完整率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="point in health.trend" :key="point.statDate">
                <td>{{ point.statDate }}</td>
                <td class="num">{{ point.completeRate }}%</td>
              </tr>
              <tr v-if="!health.trend.length">
                <td colspan="2">所选周期暂无场次</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top: 12px" data-testid="dc-dash-dimension">
      <div class="qbar" style="margin-bottom: 8px">
        <span class="hint">维度</span>
        <label v-for="item in dims" :key="item.value" class="hint" style="margin-right: 10px">
          <input
            v-model="dimensionType"
            type="radio"
            name="dc-dash-dim"
            :value="item.value"
            :data-testid="'dc-dash-dim-' + item.value"
            @change="loadDimension"
          />
          {{ item.label }}
        </label>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>维度值</th>
              <th>GMV</th>
              <th>净利润</th>
              <th>场次数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in rows" :key="row.dimensionValue">
              <tr :data-testid="'dc-dash-dim-row'" :data-value="row.dimensionValue">
                <td>{{ row.dimensionLabel }}</td>
                <td class="num">{{ money(row.gmv) }}</td>
                <td class="num" :style="neg(row.netProfit)">{{ money(row.netProfit) }}</td>
                <td class="num">{{ row.sessionCount }}</td>
                <td>
                  <button
                    v-if="row.children?.length"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="dc-dash-dim-expand"
                    @click="toggle(row.dimensionValue)"
                  >
                    {{ open[row.dimensionValue] ? '收起' : '下钻' }}
                  </button>
                </td>
              </tr>
              <tr
                v-for="child in open[row.dimensionValue] ? row.children || [] : []"
                :key="row.dimensionValue + ':' + child.dimensionValue"
                data-testid="dc-dash-dim-child"
                :data-session="child.dimensionValue"
              >
                <td>
                  <router-link
                    class="btn btn-sec btn-sm"
                    data-testid="dc-dash-session-link"
                    :to="{
                      path: '/ims/dc/trace',
                      query: { entryType: 'SESSION', keyword: child.dimensionValue, openDetail: '1' },
                    }"
                  >
                    {{ child.dimensionValue }}
                  </router-link>
                </td>
                <td class="num">{{ money(child.gmv) }}</td>
                <td class="num" :style="neg(child.netProfit)">{{ money(child.netProfit) }}</td>
                <td class="num">{{ child.sessionCount }}</td>
                <td>
                  <router-link
                    class="btn btn-sec btn-sm"
                    data-testid="dc-dash-profit-link"
                    :to="{ path: '/ims/fin/profit-trace', query: { sessionCode: child.dimensionValue } }"
                  >
                    反查
                  </router-link>
                </td>
              </tr>
            </template>
            <tr v-if="!rows.length" data-testid="dc-dash-dim-empty">
              <td colspan="5">该周期暂无已核算场次</td>
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
        >
          {{ widgetLabel(widget.widgetType) }}
        </div>
      </div>
      <p v-else class="hint" data-testid="dc-dash-layout-empty">该看板尚未配置组件</p>
    </div>

    <div class="card" style="margin-top: 12px">
      <b>同步任务</b>
      <div class="tbl-wrap">
        <table data-testid="dc-dash-freshness">
          <thead>
            <tr><th>任务名</th><th>最近运行</th><th>状态</th><th>延迟分钟</th></tr>
          </thead>
          <tbody>
            <tr
              v-for="task in freshness?.syncTaskStatus || []"
              :key="task.taskName"
              data-testid="dc-dash-sync-row"
              :data-status="task.status"
            >
              <td>{{ task.taskName }}</td>
              <td class="mono">{{ task.lastRunAt }}</td>
              <td :style="statusStyle(task.status)">{{ task.status }}</td>
              <td class="num">{{ task.delayMinutes }}</td>
            </tr>
            <tr v-if="ready && !(freshness?.syncTaskStatus || []).length" data-testid="dc-dash-sync-empty">
              <td colspan="4">暂无同步任务</td>
            </tr>
          </tbody>
        </table>
      </div>
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
              :data-testid="`dc-dash-widget-${item.type}`"
              @click="addWidget(item.type)"
            >
              {{ item.label }}
            </button>
          </div>
          <div>
            <div class="qbar" style="margin-bottom: 10px">
              <input v-model="form.name" data-testid="dc-dash-name" placeholder="看板名称" maxlength="64" style="width: 180px" />
              <input v-model="form.cron" data-testid="dc-dash-cron" placeholder="0 * * * *" style="width: 140px" />
              <button class="btn btn-sec btn-sm" type="button" data-testid="dc-dash-new" @click="resetForm">新建</button>
            </div>
            <div class="canvas" data-testid="dc-dash-canvas">
              <p v-if="!form.layout.length" class="hint" data-testid="dc-dash-canvas-empty">
                从左侧组件库选择组件加入画布
              </p>
              <button
                v-for="(widget, index) in form.layout"
                :key="widget.widgetKey"
                type="button"
                class="canvas-item"
                :class="{ on: selectedWidget === index }"
                data-testid="dc-dash-canvas-widget"
                @click="selectedWidget = index"
              >
                {{ widgetLabel(widget.widgetType) }}
              </button>
            </div>
            <div v-if="activeWidget" class="props" data-testid="dc-dash-props">
              <label>y <input v-model.number="activeWidget.position.y" type="number" data-testid="dc-dash-pos-y" /></label>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Overview = {
  totalGmv: number | null
  totalCost: number | null
  netProfit: number | null
  sessionCount: number
  accountCount: number
  assetCount: number
  dataAsOf: string
  refreshedAt: string
}
type Health = {
  assetRelationCompleteRate: number
  target: number
  isAlarm: boolean
  trend: Array<{ statDate: string; completeRate: number }>
  accountDigitizationRate: number
  ledgerTraceRate: number
}
type WidgetType = 'METRIC_CARD' | 'TREND_CHART' | 'RANK_LIST' | 'HEALTH_PANEL'
type Widget = {
  widgetKey: string
  widgetType: WidgetType
  position: { x: number; y: number; w: number; h: number }
  config: Record<string, string>
}
type Dashboard = {
  id: number
  dashboardName: string
  status: string
  refreshCron: string
  layoutConfig: Widget[]
}
type Freshness = {
  dataAsOf: string
  isAlarm?: boolean
  businessToDwsDelayMinutes?: number
  syncTaskStatus: Array<{ taskName: string; lastRunAt: string; status: string; delayMinutes: number }>
}
type Child = { dimensionValue: string; gmv: number | null; netProfit: number | null; sessionCount: number }
type DimRow = {
  dimensionValue: string
  dimensionLabel: string
  gmv: number | null
  netProfit: number | null
  sessionCount: number
  children?: Child[]
}

const dims = [
  { value: 'PLATFORM', label: '平台' },
  { value: 'ACCOUNT', label: '账号' },
  { value: 'IP_GROUP', label: 'IP组' },
  { value: 'TEAM', label: '团队' },
  { value: 'REALNAME', label: '实名人' },
]

const period = ref(currentPeriod())
const dimensionType = ref('PLATFORM')
const overview = ref<Overview | null>(null)
const health = ref<Health | null>(null)
const rows = ref<DimRow[]>([])
const error = ref('')
const ready = ref(false)
const open = reactive<Record<string, boolean>>({})
let dimensionSeq = 0
const widgetTypes: Array<{ type: WidgetType; label: string }> = [
  { type: 'METRIC_CARD', label: '指标卡' },
  { type: 'TREND_CHART', label: '趋势图' },
  { type: 'RANK_LIST', label: '排行' },
  { type: 'HEALTH_PANEL', label: '健康面板' },
]
const dashboards = ref<Dashboard[]>([])
const selectedId = ref('')
const freshness = ref<Freshness | null>(null)
const drawer = ref(false)
const editingId = ref<number | null>(null)
const selectedWidget = ref(-1)
const saveNote = ref('')
const form = ref({ name: '', cron: '0 * * * *', layout: [] as Widget[] })
const selected = computed(() => dashboards.value.find((row) => String(row.id) === selectedId.value) || null)
const hasEnabled = computed(() => dashboards.value.some((row) => row.status === 'ENABLED'))
const syncFailed = computed(() => (freshness.value?.syncTaskStatus || []).some((task) => task.status === 'FAILED'))
const activeWidget = computed(() => form.value.layout[selectedWidget.value] || null)

function currentPeriod() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${now.getFullYear()}-${month}`
}

function monthBounds(value: string) {
  const [yearText, monthText] = value.split('-')
  const year = Number(yearText)
  const month = Number(monthText)
  const last = new Date(year, month, 0).getDate()
  const mm = String(month).padStart(2, '0')
  return `${yearText}-${mm}-01,${yearText}-${mm}-${String(last).padStart(2, '0')}`
}

function money(value: number | null | undefined) {
  if (value == null) return '—'
  const text = Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return value < 0 ? `(¥${text.replace('-', '')})` : `¥${text}`
}

function neg(value: number | null | undefined) {
  return value != null && value < 0 ? { color: 'var(--red)' } : undefined
}

function statusStyle(status: string) {
  if (status === 'FAILED') return { color: 'var(--red)', fontWeight: '600' }
  if (status === 'DELAYED') return { color: 'var(--orange)', fontWeight: '600' }
  if (status === 'SUCCESS') return { color: 'var(--green)' }
  return undefined
}

function toggle(value: string) {
  open[value] = !open[value]
}

async function loadDimension() {
  const seq = ++dimensionSeq
  const statPeriod = period.value
  const dimensionTypeValue = dimensionType.value
  const res = await http.get('/dc/dashboard/dimension', {
    params: { statPeriod, dimensionType: dimensionTypeValue },
  })
  if (seq !== dimensionSeq) return
  rows.value = res.data.data || []
  for (const key of Object.keys(open)) delete open[key]
}

function widgetLabel(type: string) {
  return widgetTypes.find((item) => item.type === type)?.label || type
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

async function load() {
  error.value = ''
  try {
    const [overviewRes, healthRes, listRes, freshRes] = await Promise.all([
      http.get('/dc/dashboard/overview', { params: { statPeriod: period.value } }),
      http.get('/dc/dashboard/health', { params: { dateRange: monthBounds(period.value) } }),
      http.get('/dc/dashboard/list'),
      http.get('/dc/dashboard/freshness'),
    ])
    overview.value = overviewRes.data.data
    health.value = healthRes.data.data
    dashboards.value = Array.isArray(listRes.data.data) ? listRes.data.data : []
    freshness.value = freshRes.data.data
    if (!dashboards.value.some((row) => String(row.id) === selectedId.value)) {
      const enabled = dashboards.value.find((row) => row.status === 'ENABLED') || dashboards.value[0]
      selectedId.value = enabled ? String(enabled.id) : ''
    }
    await loadDimension()
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    ready.value = true
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
    await load()
    const current = dashboards.value.find((row) => row.id === editingId.value)
    if (current) fillForm(current)
  } catch (err) {
    saveNote.value = errorMessage(err)
  }
}

onMounted(load)
</script>

<style scoped>
.dash-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 1100px) {
  .dash-grid { grid-template-columns: 1fr 1fr 1fr; }
}
.preview { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.preview-item { border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; min-width: 120px; }
.drawer-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); z-index: 90; }
.designer { display: grid; grid-template-columns: 28% 1fr; gap: 16px; min-height: 420px; }
.palette { display: flex; flex-direction: column; gap: 8px; }
.canvas { display: flex; gap: 8px; flex-wrap: wrap; min-height: 160px; border: 1px dashed var(--line2); border-radius: 8px; padding: 8px; }
.canvas-item { border: 1px solid var(--line); background: #fff; border-radius: 8px; padding: 8px 10px; }
.canvas-item.on { border-color: var(--blue); }
</style>
