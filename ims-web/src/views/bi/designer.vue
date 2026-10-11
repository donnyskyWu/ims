<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表设计器</h1>
        <div class="sub">
          {{ report?.reportName || '加载中…' }} · 隐藏路由 /ims/bi/report/designer · BI-001 P0
          <span v-if="dirty" data-testid="bi-unsaved"> · ● 有未保存修改</span>
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-back" @click="goBack">返回报表管理</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-undo" :disabled="!undoStack.length" @click="undo">撤销</button>
        <button
          class="btn btn-sm"
          type="button"
          data-testid="bi-free-layout"
          :class="layoutMode === 'FREE' ? 'btn-pri' : 'btn-sec'"
          @click="toggleLayout"
        >
          自由布局
        </button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-terminal" @click="terminalOpen = true">终端预览</button>
        <button class="btn btn-sec btn-sm" type="button" @click="runPreview">预览</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="saving" data-testid="bi-save" @click="saveLayout">保存草稿</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="bi-open-drill" @click="openDrill">预览下钻</button>
        <button class="btn btn-pri btn-sm" type="button" @click="publish">保存并发布</button>
      </div>
    </div>

    <div v-if="loadError" class="card"><div class="empty"><div class="et">{{ loadError }}</div></div></div>

    <div v-else class="bidsn" style="display: grid; grid-template-columns: 220px 1fr 300px; gap: 12px; min-height: 520px">
      <div class="card" style="padding: 12px; max-height: calc(100vh - 160px); overflow: auto">
        <b style="font-size: 13px">数据集</b>
        <div v-for="ds in datasets" :key="ds.code" style="margin-top: 8px">
          <button
            class="btn btn-sec btn-sm"
            type="button"
            style="width: 100%"
            :data-testid="`bi-dataset-${ds.code}`"
            @click="toggleDataset(ds.code)"
          >
            {{ ds.name }}
          </button>
          <div v-if="openDataset === ds.code" data-testid="bi-field-list" style="margin-top: 6px">
            <div class="csub">维度</div>
            <div
              v-for="field in fieldsOf(ds, 'DIMENSION')"
              :key="field.name"
              draggable="true"
              class="csub"
              style="padding: 4px 0; cursor: grab"
              :data-testid="`bi-field-${field.name}`"
              @dragstart="onFieldDrag(field, $event)"
            >
              {{ field.label }}
            </div>
            <div class="csub" style="margin-top: 6px">指标</div>
            <div
              v-for="field in fieldsOf(ds, 'METRIC')"
              :key="field.name"
              draggable="true"
              class="csub"
              style="padding: 4px 0; cursor: grab"
              :data-testid="`bi-field-${field.name}`"
              @dragstart="onFieldDrag(field, $event)"
            >
              {{ field.label }}<span v-if="field.metricCode">（{{ field.metricCode }}）</span>
            </div>
          </div>
        </div>

        <b style="font-size: 13px; display: block; margin-top: 16px">组件库</b>
        <template v-for="group in compGroups" :key="group.code">
          <div class="csub" style="margin-top: 10px">{{ group.label }}</div>
          <div
            v-for="c in group.items"
            :key="c.type"
            class="btn btn-sec btn-sm"
            role="button"
            draggable="true"
            :data-testid="`bi-palette-${c.type}`"
            style="display: block; width: 100%; margin-top: 6px; text-align: center; user-select: none"
            @mousedown="onPaletteDown(c)"
            @dragstart="onHtml5Start(c, $event)"
            @click="onPaletteClick(c)"
          >
            + {{ c.name }}
          </div>
        </template>
      </div>

      <div
        class="card"
        data-testid="bi-canvas"
        :style="{
          padding: '12px',
          position: 'relative',
          minHeight: '480px',
          width: canvasWidth,
          background: 'repeating-linear-gradient(0deg, #f5f7fa, #f5f7fa 39px, #e8ecf0 40px)',
        }"
        @dragover="onCanvasDragOver"
        @drop="onCanvasDrop"
      >
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <span class="csub">画布 · {{ layoutMode }} · {{ comps.length }} 组件 · 从组件库拖入</span>
          <span v-if="previewMsg" class="tag tag-info" data-testid="bi-save-status">{{ previewMsg }}</span>
        </div>
        <div
          v-for="comp in comps"
          :key="comp.id"
          class="card hov"
          data-testid="bi-canvas-comp"
          :data-comp-type="comp.type"
          :style="{
            position: 'absolute',
            left: comp.x + 'px',
            top: comp.y + 'px',
            width: comp.w + 'px',
            minHeight: comp.h + 'px',
            padding: '8px',
            outline: selectedId === comp.id ? '2px solid var(--blue)' : '',
            cursor: 'pointer',
            overflow: 'hidden',
          }"
          @click.stop="selectedId = comp.id"
        >
          <b>{{ comp.title }}</b>
          <div class="csub">{{ comp.type }} · {{ comp.dataset || openDataset || 'METRIC_LIB' }}</div>
          <div v-if="vizOf(comp.id).error" class="hint bad" data-testid="bi-comp-error">{{ vizOf(comp.id).error }}</div>
          <div v-else-if="comp.metricKey" :data-testid="`bi-viz-${comp.type}`">
            <div v-if="comp.type === 'KPI'" style="font-size: 22px; font-weight: 700; margin-top: 8px">
              {{ formatNum(vizOf(comp.id).total) }}
            </div>
            <table v-else-if="comp.type === 'TABLE' || comp.type === 'DETAIL_TABLE'" style="width: 100%; margin-top: 6px; font-size: 12px">
              <tbody>
                <tr v-for="(row, idx) in vizOf(comp.id).rows" :key="idx">
                  <td>{{ row.label }}</td>
                  <td style="text-align: right">{{ formatNum(Number(row.value)) }}</td>
                </tr>
              </tbody>
            </table>
            <svg v-else-if="isTrend(comp.type)" viewBox="0 0 200 72" width="100%" height="72" style="margin-top: 6px">
              <polyline :points="linePoints(comp)" fill="none" stroke="#0071e3" stroke-width="2" />
            </svg>
            <div v-else class="csub" style="margin-top: 6px">
              <div v-for="(row, idx) in vizOf(comp.id).rows" :key="idx">{{ row.label }} · {{ formatNum(Number(row.value)) }}</div>
            </div>
          </div>
          <div v-else class="csub" style="margin-top: 6px">未绑定数据</div>
        </div>
        <div v-if="!comps.length" class="empty" style="margin-top: 120px"><div class="et">从左侧拖入组件（也可点击添加）</div></div>
      </div>

      <div class="card" style="padding: 12px; max-height: calc(100vh - 160px); overflow: auto">
        <b style="font-size: 13px">属性</b>
        <template v-if="selected">
          <div class="rowline" style="gap: 6px; margin-top: 8px">
            <button class="btn btn-sm" type="button" :class="propTab === 'base' ? 'btn-pri' : 'btn-sec'" @click="propTab = 'base'">基础</button>
            <button class="btn btn-sm" type="button" data-testid="bi-prop-data" :class="propTab === 'data' ? 'btn-pri' : 'btn-sec'" @click="propTab = 'data'">数据源</button>
            <button class="btn btn-sm" type="button" data-testid="bi-prop-interact" :class="propTab === 'interact' ? 'btn-pri' : 'btn-sec'" @click="propTab = 'interact'">交互</button>
          </div>

          <template v-if="propTab === 'base'">
            <label class="fld">标题</label>
            <input v-model="selected.title" class="fld-in" @focus="armUndo" />
            <label class="fld">X / Y</label>
            <div class="rowline" style="gap: 8px">
              <input v-model.number="selected.x" type="number" class="fld-in" style="width: 48%" @focus="armUndo" />
              <input v-model.number="selected.y" type="number" class="fld-in" style="width: 48%" @focus="armUndo" />
            </div>
            <label class="fld">宽 / 高</label>
            <div class="rowline" style="gap: 8px">
              <input v-model.number="selected.w" type="number" class="fld-in" style="width: 48%" @focus="armUndo" />
              <input v-model.number="selected.h" type="number" class="fld-in" style="width: 48%" @focus="armUndo" />
            </div>
          </template>

          <template v-else-if="propTab === 'data'">
            <label class="fld">数据集</label>
            <select v-model="selected.dataset" class="fld-in" data-testid="bi-bind-dataset" @focus="armUndo" @change="openDataset = selected.dataset || ''">
              <option v-for="ds in datasets" :key="ds.code" :value="ds.code">{{ ds.name }}</option>
            </select>
            <label class="fld">维度</label>
            <select v-model="selected.dimensionKey" class="fld-in" data-testid="bi-bind-dimension" @focus="armUndo" @change="onBindChange">
              <option value="">不分组</option>
              <option v-for="field in fieldsOf(activeDs, 'DIMENSION')" :key="field.name" :value="field.name">{{ field.label }}</option>
            </select>
            <label class="fld">指标</label>
            <select v-model="selected.metricKey" class="fld-in" data-testid="bi-bind-metric" @focus="armUndo" @change="onMetricChange">
              <option value="">请选择指标</option>
              <option v-for="field in fieldsOf(activeDs, 'METRIC')" :key="field.name" :value="field.name">
                {{ metricLabel(field) }}
              </option>
            </select>
            <div
              data-testid="bi-value-drop"
              class="hint"
              style="margin-top: 8px; padding: 8px; border: 1px dashed var(--line)"
              @dragover.prevent
              @drop="onFieldDrop"
            >
              值区：拖入指标{{ selected.metricCode ? ` · ${selected.metricCode}` : '' }}
            </div>
            <label class="fld">聚合</label>
            <select v-model="selected.agg" class="fld-in" @focus="armUndo" @change="onBindChange">
              <option value="SUM">SUM</option>
              <option value="AVG">AVG</option>
              <option value="COUNT">COUNT</option>
              <option value="MAX">MAX</option>
              <option value="MIN">MIN</option>
            </select>
            <label class="fld">字段引用</label>
            <input
              v-model="selected.customField"
              class="fld-in"
              data-testid="bi-custom-field"
              placeholder="未登记字段将提示 1191"
              @focus="armUndo"
              @change="onBindChange"
            />
            <label class="fld">计算表达式</label>
            <input
              v-model="selected.calcExpression"
              class="fld-in"
              data-testid="bi-calc-expr"
              placeholder="(SUM(gmv) - SUM(cost)) / SUM(gmv)"
              @focus="armUndo"
              @change="onBindChange"
            />
            <p v-if="vizOf(selected.id).error" class="hint bad" data-testid="bi-field-error">{{ vizOf(selected.id).error }}</p>
          </template>

          <template v-else>
            <label class="fld">跳转目标</label>
            <input v-model="selected.jumpTarget" class="fld-in" placeholder="报表 / 下钻详情 / 外部链接" @focus="armUndo" />
            <label class="fld">自动刷新（秒，最小 30）</label>
            <input v-model.number="selected.refreshInterval" type="number" min="30" class="fld-in" @focus="armUndo" />
            <p class="hint">联动目标取画布上的其他组件。刷新间隔小于 30 秒时保存会被拒绝。</p>
          </template>

          <button class="btn btn-sec btn-sm" type="button" style="margin-top: 12px" @click="removeSelected">删除组件</button>
        </template>
        <div v-else class="csub" style="margin-top: 12px">
          <div>选中画布组件以编辑</div>
          <label class="fld">报表名称</label>
          <input v-if="report" v-model="report.reportName" class="fld-in" @focus="armUndo" />
          <p class="hint">未选中组件时这里是报表级属性。可见范围和分类在新建报表时设定。</p>
        </div>
      </div>
    </div>

    <div v-if="terminalOpen" class="modal-mask" @click.self="terminalOpen = false">
      <div class="card" style="width: 360px; padding: 20px" data-testid="bi-terminal-panel">
        <h3 style="margin: 0 0 12px">终端预览</h3>
        <div class="rowline" style="gap: 8px">
          <button class="btn btn-sm" type="button" :class="terminalPreset === 'PC' ? 'btn-pri' : 'btn-sec'" @click="terminalPreset = 'PC'">PC</button>
          <button class="btn btn-sm" type="button" :class="terminalPreset === 'TV' ? 'btn-pri' : 'btn-sec'" @click="terminalPreset = 'TV'">TV</button>
          <button class="btn btn-sm" type="button" :class="terminalPreset === 'MOBILE' ? 'btn-pri' : 'btn-sec'" @click="terminalPreset = 'MOBILE'">移动</button>
        </div>
        <p class="hint">只切换画布宽度，组件绑定保持不变。</p>
        <div class="acts" style="justify-content: flex-end">
          <button class="btn btn-pri btn-sm" type="button" @click="terminalOpen = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'

type Field = {
  name: string
  label: string
  type: string
  fieldType?: 'DIMENSION' | 'METRIC'
  dataType?: string
  metricCode?: string
}

type Dataset = { code: string; name: string; fields: Field[] }

type Comp = {
  id: string
  type: string
  title: string
  x: number
  y: number
  w: number
  h: number
  dataset?: string
  dimensionKey?: string
  metricKey?: string
  metricCode?: string
  agg?: string
  calcExpression?: string
  customField?: string
  jumpTarget?: string
  refreshInterval?: number
}

type ReportVo = {
  id: number
  reportName: string
  status: string
  comps: Comp[]
  layoutMode: string
}

type CompMeta = { type: string; name: string; group?: string; defaultSize: { w: number; h: number } }

type Viz = { rows: Array<Record<string, string | number>>; total: number; error: string }

const GROUP_LABEL: Record<string, string> = {
  CHART: '图表',
  FILTER: '查询条件',
  CONTAINER: '容器',
  ACTION: '交互',
}

const route = useRoute()
const router = useRouter()
const reportId = computed(() => Number(route.query.reportId || 0))
const pendingComp = ref<CompMeta | null>(null)
let html5Handled = false
let droppedOnCanvas = false
const report = ref<ReportVo | null>(null)
const comps = ref<Comp[]>([])
const datasets = ref<Dataset[]>([])
const compLib = ref<CompMeta[]>([])
const openDataset = ref('')
const selectedId = ref('')
const saving = ref(false)
const loadError = ref('')
const previewMsg = ref('')
const layoutMode = ref<'FREE' | 'GRID'>('FREE')
const propTab = ref<'base' | 'data' | 'interact'>('base')
const undoStack = ref<string[]>([])
const savedSnap = ref('[]')
const series = ref<Record<string, Viz>>({})
const terminalOpen = ref(false)
const terminalPreset = ref<'PC' | 'TV' | 'MOBILE'>('PC')
let leaveConfirmed = false

const selected = computed(() => comps.value.find((c) => c.id === selectedId.value) || null)
const savedName = ref('')
const savedLayout = ref<'FREE' | 'GRID'>('FREE')
const dirty = computed(
  () =>
    JSON.stringify(comps.value) !== savedSnap.value ||
    (report.value?.reportName || '') !== savedName.value ||
    layoutMode.value !== savedLayout.value,
)
const compGroups = computed(() => {
  const order = ['CHART', 'FILTER', 'CONTAINER', 'ACTION']
  return order
    .map((code) => ({
      code,
      label: GROUP_LABEL[code],
      items: compLib.value.filter((item) => (item.group || 'CHART') === code),
    }))
    .filter((group) => group.items.length)
})
const activeDs = computed(() => datasets.value.find((ds) => ds.code === (selected.value?.dataset || openDataset.value)) || datasets.value[0])
const canvasWidth = computed(() => {
  if (!terminalOpen.value && terminalPreset.value === 'PC') return 'auto'
  if (terminalPreset.value === 'TV') return '960px'
  if (terminalPreset.value === 'MOBILE') return '375px'
  return 'auto'
})

function fieldsOf(ds: Dataset | undefined, kind: 'DIMENSION' | 'METRIC') {
  return (ds?.fields || []).filter((field) => field.fieldType === kind)
}

function vizOf(id: string): Viz {
  return series.value[id] || { rows: [], total: 0, error: '' }
}

function formatNum(n: number) {
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('zh-CN')
}

function isTrend(type: string) {
  return type === 'LINE' || type === 'AREA' || type === 'BAR'
}

function linePoints(comp: Comp) {
  const rows = vizOf(comp.id).rows
  if (!rows.length) return ''
  const vals = rows.map((row) => Number(row.value || 0))
  const max = Math.max(...vals, 1)
  return vals
    .map((value, index) => {
      const x = rows.length === 1 ? 100 : (index / (rows.length - 1)) * 190 + 5
      const y = 66 - (value / max) * 58
      return `${x},${y}`
    })
    .join(' ')
}

function uid() {
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
}

function armUndo() {
  const snap = JSON.stringify(comps.value)
  if (undoStack.value.at(-1) === snap) return
  undoStack.value.push(snap)
}

function undo() {
  const prev = undoStack.value.pop()
  if (prev == null) return
  comps.value = JSON.parse(prev) as Comp[]
  previewMsg.value = ''
  for (const comp of comps.value) {
    if (comp.metricKey || comp.dimensionKey || comp.customField || comp.calcExpression) void refreshComp(comp)
  }
}

function metricLabel(field: Field) {
  return field.metricCode ? `${field.label}（${field.metricCode}）` : field.label
}

function toggleLayout() {
  layoutMode.value = layoutMode.value === 'FREE' ? 'GRID' : 'FREE'
}

function toggleDataset(code: string) {
  openDataset.value = openDataset.value === code ? '' : code
}

function addComp(meta: CompMeta) {
  armUndo()
  const id = uid()
  const w = Math.max(80, meta.defaultSize.w)
  const h = Math.max(80, meta.defaultSize.h)
  comps.value.push({
    id,
    type: meta.type,
    title: meta.name,
    x: 40 + (comps.value.length % 4) * 24,
    y: 72 + comps.value.length * 16,
    w,
    h,
    dataset: openDataset.value || 'METRIC_LIB',
    dimensionKey: '',
    metricKey: '',
    metricCode: '',
    agg: 'SUM',
    calcExpression: '',
    customField: '',
    jumpTarget: '',
    refreshInterval: 30,
  })
  selectedId.value = id
  propTab.value = 'data'
}

function onPaletteDown(meta: CompMeta) {
  pendingComp.value = meta
}

function onPaletteClick(meta: CompMeta) {
  if (droppedOnCanvas) return
  addComp(meta)
}

function onHtml5Start(meta: CompMeta, ev: DragEvent) {
  pendingComp.value = meta
  ev.dataTransfer?.setData('text/bi-comp', meta.type)
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'copy'
}

function onFieldDrag(field: Field, ev: DragEvent) {
  ev.dataTransfer?.setData('text/bi-field', field.name)
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'copy'
}

function onCanvasDragOver(ev: DragEvent) {
  ev.preventDefault()
}

function onCanvasDrop(ev: DragEvent) {
  const fieldName = ev.dataTransfer?.getData('text/bi-field') || ''
  if (fieldName) {
    ev.preventDefault()
    return
  }
  ev.preventDefault()
  const type = ev.dataTransfer?.getData('text/bi-comp') || pendingComp.value?.type || ''
  const meta = compLib.value.find((item) => item.type === type) || null
  html5Handled = true
  pendingComp.value = null
  if (meta) addComp(meta)
}

function onWindowMouseUp(ev: MouseEvent) {
  if (html5Handled) {
    html5Handled = false
    pendingComp.value = null
    return
  }
  const meta = pendingComp.value
  pendingComp.value = null
  if (!meta) return
  const canvas = document.querySelector('[data-testid="bi-canvas"]')
  if (canvas && ev.target instanceof Node && canvas.contains(ev.target)) {
    droppedOnCanvas = true
    addComp(meta)
    window.setTimeout(() => {
      droppedOnCanvas = false
    }, 0)
  }
}

function removeSelected() {
  if (!selectedId.value) return
  armUndo()
  comps.value = comps.value.filter((c) => c.id !== selectedId.value)
  selectedId.value = ''
}

function findField(name: string) {
  for (const ds of datasets.value) {
    const field = ds.fields.find((item) => item.name === name || item.metricCode === name)
    if (field) return field
  }
  return undefined
}

async function onFieldDrop(ev: DragEvent) {
  ev.preventDefault()
  ev.stopPropagation()
  const key = ev.dataTransfer?.getData('text/bi-field') || ''
  if (!selected.value || !key) return
  armUndo()
  const field = findField(key)
  if (field?.fieldType === 'METRIC') {
    selected.value.metricKey = field.name
    selected.value.metricCode = field.metricCode || ''
    selected.value.customField = ''
  } else if (field?.fieldType === 'DIMENSION') {
    selected.value.metricKey = field.name
    selected.value.metricCode = ''
  } else {
    selected.value.customField = key
  }
  await refreshComp(selected.value)
}

function onMetricChange() {
  const field = findField(selected.value?.metricKey || '')
  if (selected.value) {
    selected.value.metricCode = field?.metricCode || ''
    if (field?.fieldType === 'METRIC') selected.value.customField = ''
  }
  void onBindChange()
}

async function onBindChange() {
  if (!selected.value) return
  await refreshComp(selected.value)
}

async function refreshComp(comp: Comp) {
  if (!comp.metricKey && !comp.dimensionKey && !comp.customField && !comp.calcExpression) {
    series.value = { ...series.value, [comp.id]: { rows: [], total: 0, error: '' } }
    return
  }
  const res = await http.post('/bi/report/query', {
    reportId: reportId.value || undefined,
    compId: comp.id,
    components: comps.value,
  })
  if (res.data.code !== 0) {
    series.value = {
      ...series.value,
      [comp.id]: { rows: [], total: 0, error: res.data.msg || '字段引用非法（1191）' },
    }
    return
  }
  const rows = (res.data.data.rows || []) as Array<Record<string, string | number>>
  series.value = {
    ...series.value,
    [comp.id]: { rows, total: Number(res.data.data.metricTotal ?? 0), error: '' },
  }
}

async function loadMeta() {
  const ds = await http.get('/bi/report/datasets')
  if (ds.data.code === 0) {
    datasets.value = ds.data.data.datasets || []
    compLib.value = ds.data.data.compLib || []
  }
}

function markClean() {
  savedSnap.value = JSON.stringify(comps.value)
  savedName.value = report.value?.reportName || ''
  savedLayout.value = layoutMode.value
}

async function loadReport() {
  loadError.value = ''
  if (!reportId.value) {
    loadError.value = '缺少 reportId 参数'
    return
  }
  const res = await http.get(`/bi/report/${reportId.value}`)
  if (res.data.code !== 0) {
    loadError.value = res.data.msg || '加载失败'
    return
  }
  report.value = res.data.data
  comps.value = ((res.data.data.comps || []) as Comp[]).map((comp) => ({
    ...comp,
    w: Math.max(80, Number(comp.w) || 80),
    h: Math.max(80, Number(comp.h) || 80),
    agg: comp.agg || 'SUM',
    dataset: comp.dataset || 'METRIC_LIB',
  }))
  layoutMode.value = res.data.data.layoutMode === 'GRID' ? 'GRID' : 'FREE'
  if (comps.value.length) selectedId.value = comps.value[0].id
  markClean()
  for (const comp of comps.value) {
    if (comp.metricKey || comp.dimensionKey) void refreshComp(comp)
  }
}

async function saveLayout() {
  if (!reportId.value) return
  const tooSmall = comps.value.some((comp) => comp.w < 80 || comp.h < 80)
  const tooFast = comps.value.some((comp) => comp.refreshInterval != null && comp.refreshInterval > 0 && comp.refreshInterval < 30)
  if (tooSmall) {
    previewMsg.value = '组件尺寸不能小于 80×80'
    return
  }
  if (tooFast) {
    previewMsg.value = '刷新间隔不能小于 30 秒'
    return
  }
  saving.value = true
  try {
    const res = await http.put(`/bi/report/${reportId.value}`, {
      reportName: report.value?.reportName,
      layoutJson: { layoutMode: layoutMode.value, comps: comps.value },
    })
    if (res.data.code !== 0) {
      previewMsg.value = res.data.msg || '保存失败'
      if (selected.value && (res.data.code === 1191 || res.data.code === 1192)) {
        series.value = {
          ...series.value,
          [selected.value.id]: { rows: [], total: 0, error: res.data.msg },
        }
      }
      return
    }
    report.value = { ...report.value!, ...res.data.data, reportName: report.value?.reportName || res.data.data.reportName }
    previewMsg.value = '已保存'
    markClean()
  } finally {
    saving.value = false
  }
}

async function openDrill() {
  try {
    await saveLayout()
  } catch {
    return
  }
  if (!reportId.value || previewMsg.value !== '已保存') return
  leaveConfirmed = true
  await router.push({ path: '/ims/bi/report/preview', query: { reportId: String(reportId.value) } })
}

async function publish() {
  await saveLayout()
  if (previewMsg.value !== '已保存') return
  const res = await http.post(`/bi/report/${reportId.value}/publish`)
  if (res.data.code === 0) {
    previewMsg.value = `已发布 · ${res.data.data.status}`
    report.value = { ...report.value!, status: res.data.data.status }
    markClean()
  } else {
    previewMsg.value = res.data.msg || '发布失败'
  }
}

async function runPreview() {
  const res = await http.post('/bi/report/query', {
    reportId: reportId.value,
    compId: selectedId.value || 'preview',
    components: comps.value,
  })
  if (res.data.code === 0) {
    previewMsg.value = `预览 ${res.data.data.total} 行 · ${res.data.data.status}`
    if (selected.value) {
      series.value = {
        ...series.value,
        [selected.value.id]: {
          rows: res.data.data.rows || [],
          total: Number(res.data.data.metricTotal ?? 0),
          error: '',
        },
      }
    }
  } else if (selected.value) {
    previewMsg.value = res.data.msg || '预览失败'
    series.value = {
      ...series.value,
      [selected.value.id]: { rows: [], total: 0, error: res.data.msg || '字段引用非法（1191）' },
    }
  }
}

function goBack() {
  router.push('/ims/bi/report/list')
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(() => {
  if (leaveConfirmed || !dirty.value) return true
  const ok = window.confirm('有未保存修改')
  return ok
})

onMounted(async () => {
  window.addEventListener('mouseup', onWindowMouseUp, true)
  window.addEventListener('beforeunload', onBeforeUnload)
  await loadMeta()
  await loadReport()
})

onUnmounted(() => {
  window.removeEventListener('mouseup', onWindowMouseUp, true)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>
