<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表设计器</h1>
        <div class="sub">
          {{ report?.reportName || '加载中…' }} · 隐藏路由 /ims/bi/report/designer · BI-001
          <span v-if="dirty" data-testid="bi-dirty"> · ● 有未保存修改</span>
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-back" @click="requestLeave()">返回报表管理</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-undo" :disabled="!undoStack.length" @click="undo">撤销</button>
        <button class="btn btn-sm" type="button" data-testid="bi-free-layout" :class="layoutMode === 'FREE' ? 'btn-pri' : 'btn-sec'" @click="useFreeLayout">自由布局</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-device-preview" @click="deviceOpen = !deviceOpen">终端预览</button>
        <button class="btn btn-sec btn-sm" type="button" @click="runPreview">运行预览</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="saving" data-testid="bi-save" @click="saveLayout">保存草稿</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="bi-open-drill" @click="openDrill">预览下钻</button>
        <button class="btn btn-pri btn-sm" type="button" @click="publish">保存并发布</button>
      </div>
    </div>

    <div v-if="deviceOpen" class="rowline" data-testid="bi-device-bar" style="gap: 8px; margin-bottom: 8px">
      <span class="csub">终端</span>
      <button v-for="item in devices" :key="item" class="btn btn-sm" :class="device === item ? 'btn-pri' : 'btn-sec'" type="button" @click="device = item">{{ item }}</button>
    </div>

    <div v-if="loadError" class="card"><div class="empty"><div class="et">{{ loadError }}</div></div></div>

    <div v-else class="bidsn" style="display: grid; grid-template-columns: 220px 1fr 280px; gap: 12px; min-height: 520px">
      <div class="card" style="padding: 12px; max-height: 720px; overflow: auto">
        <b style="font-size: 13px">数据集</b>
        <div v-for="ds in datasets" :key="ds.code" style="margin-top: 8px">
          <div
            class="csub"
            style="cursor: pointer"
            data-testid="bi-dataset"
            :data-dataset="ds.code"
            @click="toggleDataset(ds)"
          >
            {{ ds.name }}<span v-if="ds.enabled === false"> · P2+</span>
          </div>
          <div v-if="openDataset === ds.code" data-testid="bi-field-list" style="margin: 6px 0 0 8px">
            <div
              v-for="field in ds.fields"
              :key="field.fieldKey"
              class="csub"
              draggable="true"
              :data-testid="`bi-field-${field.fieldKey}`"
              style="cursor: grab; margin-top: 4px"
              @dragstart="onFieldDrag(field, $event)"
              @click.stop="bindField(field)"
            >
              {{ field.fieldType === 'DIMENSION' ? '维度' : '指标' }} · {{ field.fieldLabel }}
              <span v-if="field.metricCode" class="mono"> {{ field.metricCode }}</span>
            </div>
            <div v-if="!ds.fields.length" class="csub">暂无字段</div>
          </div>
        </div>
        <p v-if="datasetHint" class="csub" style="margin-top: 8px">{{ datasetHint }}</p>

        <template v-for="group in paletteGroups" :key="group.key">
          <b style="font-size: 13px; display: block; margin-top: 16px">{{ group.label }}</b>
          <div
            v-for="c in paletteOf(group.key)"
            :key="c.type"
            class="btn btn-sec btn-sm"
            role="button"
            draggable="true"
            :data-testid="`bi-palette-${c.type}`"
            style="display: block; width: 100%; margin-top: 8px; text-align: center; user-select: none"
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
          maxWidth: canvasMax,
          background: 'repeating-linear-gradient(0deg, #f5f7fa, #f5f7fa 39px, #e8ecf0 40px)',
        }"
        @dragover="onCanvasDragOver"
        @drop="onCanvasDrop"
      >
        <div class="rowline" style="justify-content: space-between; margin-bottom: 8px">
          <span class="csub">画布 · {{ layoutMode }} · {{ comps.length }} 组件 · {{ device }} · 从组件库拖入</span>
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
          <div class="csub">{{ comp.type }} · {{ comp.dataset || activeDataset }}</div>
          <div v-if="comp.metric || comp.dimension" class="csub">
            {{ fieldLabel(comp.dataset, comp.dimension) }}<span v-if="comp.dimension && comp.metric"> × </span>{{ fieldLabel(comp.dataset, comp.metric) }}
          </div>
          <div v-if="isKpi(comp) && previewOf(comp).rows.length" data-testid="bi-comp-value" style="font-size: 22px; font-weight: 700; margin-top: 6px">
            {{ formatNum(previewOf(comp).rows[0].value) }}
          </div>
          <svg v-else-if="isChart(comp) && previewOf(comp).rows.length" :width="Math.max(comp.w - 24, 80)" height="72" style="margin-top: 6px">
            <polyline fill="none" stroke="#0071e3" stroke-width="2" :points="linePoints(comp)" />
          </svg>
          <table v-else-if="isTable(comp) && previewOf(comp).rows.length" style="width: 100%; margin-top: 6px; font-size: 12px">
            <thead>
              <tr>
                <th v-for="col in previewOf(comp).columns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in previewOf(comp).rows" :key="idx">
                <td v-for="col in previewOf(comp).columns" :key="col">{{ row[col] }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else-if="previewOf(comp).rows.length" class="csub" style="margin-top: 6px">{{ previewOf(comp).rows.length }} 行</div>
        </div>
        <div v-if="!comps.length" class="empty" style="margin-top: 120px"><div class="et">从左侧拖入组件（也可点击添加）</div></div>
      </div>

      <div class="card" style="padding: 12px; max-height: 720px; overflow: auto">
        <b style="font-size: 13px">属性</b>
        <template v-if="selected">
          <div class="rowline" style="gap: 6px; margin-top: 8px">
            <button class="btn btn-sm" :class="propTab === 'base' ? 'btn-pri' : 'btn-sec'" type="button" @click="propTab = 'base'">基础</button>
            <button class="btn btn-sm" :class="propTab === 'data' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="bi-prop-data" @click="propTab = 'data'">数据源</button>
            <button class="btn btn-sm" :class="propTab === 'act' ? 'btn-pri' : 'btn-sec'" type="button" data-testid="bi-prop-act" @click="propTab = 'act'">交互</button>
          </div>

          <template v-if="propTab === 'base'">
            <label class="fld">标题</label>
            <input v-model="selected.title" class="fld-in" @focus="armSnapshot" @blur="disarm" @input="dirty = true" />
            <label class="fld">X / Y</label>
            <div class="rowline" style="gap: 8px">
              <input v-model.number="selected.x" type="number" class="fld-in" style="width: 48%" @focus="armSnapshot" @input="dirty = true" />
              <input v-model.number="selected.y" type="number" class="fld-in" style="width: 48%" @focus="armSnapshot" @input="dirty = true" />
            </div>
            <label class="fld">宽 / 高</label>
            <div class="rowline" style="gap: 8px">
              <input v-model.number="selected.w" type="number" class="fld-in" style="width: 48%" @focus="armSnapshot" @input="dirty = true" />
              <input v-model.number="selected.h" type="number" class="fld-in" style="width: 48%" @focus="armSnapshot" @input="dirty = true" />
            </div>
          </template>

          <template v-else-if="propTab === 'data'">
            <label class="fld">数据集</label>
            <select v-model="selected.dataset" class="fld-in" data-testid="bi-comp-dataset" @mousedown="armSnapshot" @change="onBindChange">
              <option v-for="ds in bindableDatasets" :key="ds.code" :value="ds.code">{{ ds.name }}</option>
            </select>
            <label class="fld">维度</label>
            <div
              data-testid="bi-dim-drop"
              class="csub"
              style="border: 1px dashed var(--line); border-radius: 6px; padding: 6px; margin-bottom: 6px"
              @dragover.prevent
              @drop="onDimDrop"
            >
              维度区
            </div>
            <select v-model="selected.dimension" class="fld-in" data-testid="bi-dim" @mousedown="armSnapshot" @change="onBindChange">
              <option value="">不选</option>
              <option v-for="field in dimFields" :key="field.fieldKey" :value="field.fieldKey">{{ field.fieldLabel }}</option>
            </select>
            <label class="fld">指标</label>
            <div
              data-testid="bi-value-drop"
              class="csub"
              style="border: 1px dashed var(--line); border-radius: 6px; padding: 6px; margin-bottom: 6px"
              @dragover.prevent
              @drop="onValueDrop"
            >
              值区：拖入指标
            </div>
            <select v-model="selected.metric" class="fld-in" data-testid="bi-metric" @mousedown="armSnapshot" @change="onBindChange">
              <option value="">不选</option>
              <option v-for="field in metricFields" :key="field.fieldKey" :value="field.fieldKey">
                {{ field.fieldLabel }}<template v-if="field.metricCode">（{{ field.metricCode }}）</template>
              </option>
            </select>
            <label class="fld">聚合</label>
            <select v-model="selected.agg" class="fld-in" data-testid="bi-agg" @mousedown="armSnapshot" @change="onBindChange">
              <option value="SUM">SUM</option>
              <option value="AVG">AVG</option>
              <option value="COUNT">COUNT</option>
              <option value="MAX">MAX</option>
              <option value="MIN">MIN</option>
            </select>
            <label class="fld">计算表达式</label>
            <input v-model="selected.calcExpression" class="fld-in" data-testid="bi-calc" placeholder="SUM(gmv)" @focus="armSnapshot" @change="onBindChange" />
            <label class="fld">字段引用</label>
            <input v-model="fieldRef" class="fld-in" data-testid="bi-field-ref" placeholder="未登记字段将提示 1191" @change="applyFieldRef" />
            <p v-if="bindError" class="hint" data-testid="bi-bind-error" style="color: var(--red)">{{ bindError }}</p>
          </template>

          <template v-else>
            <label class="fld">跳转</label>
            <input v-model="selected.jumpTo" class="fld-in" placeholder="报表 / 下钻详情" @focus="armSnapshot" @input="dirty = true" />
            <label class="fld">联动目标</label>
            <input v-model="selected.linkTarget" class="fld-in" placeholder="目标组件 id" @focus="armSnapshot" @input="dirty = true" />
          </template>

          <button class="btn btn-sec btn-sm" type="button" style="margin-top: 12px" @click="removeSelected">删除组件</button>
        </template>
        <div v-else class="csub" style="margin-top: 12px">选中画布组件以编辑。未选中时这里是报表级属性（名称 / 自由布局）。</div>
      </div>
    </div>

    <div v-if="leaveAsk" class="modal-mask" data-testid="bi-leave-dialog">
      <div class="card" style="width: 380px; padding: 20px">
        <h3 style="margin: 0 0 8px">● 有未保存修改</h3>
        <p class="csub">离开设计器将丢失尚未保存的修改。</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-leave-stay" @click="stay">留下</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-leave-confirm" @click="confirmLeave">离开</button>
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
  fieldKey: string
  fieldLabel: string
  fieldType: 'DIMENSION' | 'METRIC' | string
  dataType?: string
  metricCode?: string
}

type Dataset = {
  code: string
  name: string
  enabled?: boolean
  fields: Field[]
  rowCountEstimate?: number
}

type Comp = {
  id: string
  type: string
  title: string
  x: number
  y: number
  w: number
  h: number
  dataset?: string
  dimension?: string
  metric?: string
  agg?: string
  calcExpression?: string
  source?: string
  jumpTo?: string
  linkTarget?: string
}

type ReportVo = {
  id: number
  reportName: string
  status: string
  comps: Comp[]
  layoutMode: string
}

type CompMeta = { type: string; name: string; group?: string; defaultSize: { w: number; h: number } }

type Preview = { columns: string[]; rows: Record<string, unknown>[]; error: string }

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
const activeDataset = ref('METRIC_LIB')
const openDataset = ref('')
const datasetHint = ref('')
const selectedId = ref('')
const saving = ref(false)
const loadError = ref('')
const previewMsg = ref('')
const propTab = ref<'base' | 'data' | 'act'>('base')
const bindError = ref('')
const fieldRef = ref('')
const dirty = ref(false)
const leaveAsk = ref(false)
const leaveTo = ref('/ims/bi/report/list')
const undoStack = ref<string[]>([])
const layoutMode = ref('FREE')
const deviceOpen = ref(false)
const device = ref<'PC' | 'TV' | '移动'>('PC')
const devices = ['PC', 'TV', '移动'] as const
const previewById = ref<Record<string, Preview>>({})
let allowLeave = false
let editArmed = false

const paletteGroups = [
  { key: 'CHART', label: '图表' },
  { key: 'FILTER', label: '查询条件' },
  { key: 'CONTAINER', label: '容器' },
  { key: 'ACTION', label: '交互' },
]

const selected = computed(() => comps.value.find((c) => c.id === selectedId.value) || null)
const bindableDatasets = computed(() => datasets.value.filter((ds) => ds.enabled !== false))
const canvasMax = computed(() => (device.value === '移动' ? '420px' : device.value === 'TV' ? '100%' : '100%'))
const dimFields = computed(() => fieldsOf(selected.value?.dataset || activeDataset.value).filter((f) => f.fieldType === 'DIMENSION'))
const metricFields = computed(() => fieldsOf(selected.value?.dataset || activeDataset.value).filter((f) => f.fieldType === 'METRIC'))

function paletteOf(group: string) {
  return compLib.value.filter((item) => (item.group || 'CHART') === group)
}

function fieldsOf(code?: string) {
  return datasets.value.find((ds) => ds.code === (code || activeDataset.value))?.fields || []
}

function fieldLabel(dataset: string | undefined, key: string | undefined) {
  if (!key) return ''
  return fieldsOf(dataset).find((f) => f.fieldKey === key)?.fieldLabel || key
}

function uid() {
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
}

function snapshot() {
  undoStack.value.push(JSON.stringify(comps.value))
  if (undoStack.value.length > 40) undoStack.value.shift()
}

function armSnapshot() {
  if (editArmed) return
  snapshot()
  editArmed = true
}

function disarm() {
  editArmed = false
}

function undo() {
  const raw = undoStack.value.pop()
  if (!raw) return
  const parsed = JSON.parse(raw) as Comp[]
  comps.value = parsed
  if (!parsed.some((item) => item.id === selectedId.value)) selectedId.value = parsed[0]?.id || ''
  dirty.value = true
  previewMsg.value = '已撤销'
}

function useFreeLayout() {
  layoutMode.value = 'FREE'
  previewMsg.value = '自由布局'
}

function addComp(meta: CompMeta) {
  snapshot()
  const id = uid()
  const width = Math.max(meta.defaultSize.w, 80)
  const height = Math.max(meta.defaultSize.h, 80)
  dirty.value = true
  comps.value.push({
    id,
    type: meta.type,
    title: meta.name,
    x: 40 + (comps.value.length - 0) * 24,
    y: 72 + comps.value.length * 16,
    w: width,
    h: height,
    dataset: activeDataset.value === 'DWS_AGGREGATION' ? 'METRIC_LIB' : activeDataset.value,
    dimension: '',
    metric: '',
    agg: 'SUM',
    calcExpression: '',
    source: 'DATASET_FIELD',
    jumpTo: '',
    linkTarget: '',
  })
  selectedId.value = id
  propTab.value = 'data'
  bindError.value = ''
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

function onCanvasDragOver(ev: DragEvent) {
  ev.preventDefault()
}

function onCanvasDrop(ev: DragEvent) {
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
  snapshot()
  comps.value = comps.value.filter((c) => c.id !== selectedId.value)
  selectedId.value = ''
  dirty.value = true
}

function toggleDataset(ds: Dataset) {
  datasetHint.value = ''
  if (ds.enabled === false) {
    datasetHint.value = '宽表聚合为 P2+，暂不开放'
    return
  }
  openDataset.value = openDataset.value === ds.code ? '' : ds.code
  activeDataset.value = ds.code
  if (ds.rowCountEstimate && ds.rowCountEstimate > 100000) {
    datasetHint.value = `数据量约 ${ds.rowCountEstimate} 行，查询可能较慢`
  }
}

function onFieldDrag(field: Field, ev: DragEvent) {
  ev.dataTransfer?.setData('text/bi-field', field.fieldKey)
  ev.dataTransfer?.setData('text/bi-field-type', field.fieldType)
  if (ev.dataTransfer) ev.dataTransfer.effectAllowed = 'copy'
}

function bindField(field: Field) {
  if (!selected.value) {
    propTab.value = 'data'
    return
  }
  snapshot()
  if (field.fieldType === 'DIMENSION') selected.value.dimension = field.fieldKey
  else selected.value.metric = field.fieldKey
  selected.value.dataset = activeDataset.value
  bindError.value = ''
  dirty.value = true
  void refreshSelected()
}

function onDimDrop(ev: DragEvent) {
  ev.preventDefault()
  if (!selected.value) return
  const key = ev.dataTransfer?.getData('text/bi-field') || ''
  const ftype = ev.dataTransfer?.getData('text/bi-field-type') || ''
  snapshot()
  if (!key || ftype !== 'DIMENSION') {
    bindError.value = '字段引用非法（1191）'
    dirty.value = true
    return
  }
  selected.value.dimension = key
  bindError.value = ''
  dirty.value = true
  void refreshSelected()
}

function onValueDrop(ev: DragEvent) {
  ev.preventDefault()
  if (!selected.value) return
  const key = ev.dataTransfer?.getData('text/bi-field') || ''
  const ftype = ev.dataTransfer?.getData('text/bi-field-type') || ''
  snapshot()
  if (!key || ftype !== 'METRIC') {
    selected.value.metric = key
    bindError.value = '字段引用非法（1191）'
    dirty.value = true
    return
  }
  selected.value.metric = key
  bindError.value = ''
  dirty.value = true
  void refreshSelected()
}

async function onBindChange() {
  if (!editArmed) snapshot()
  disarm()
  dirty.value = true
  bindError.value = ''
  await refreshSelected()
}

async function applyFieldRef() {
  if (!selected.value) return
  const key = fieldRef.value.trim()
  if (!key) return
  snapshot()
  const known = fieldsOf(selected.value.dataset).find((field) => field.fieldKey === key)
  if (!known || known.fieldType !== 'METRIC') {
    selected.value.metric = key
    bindError.value = '字段引用非法（1191）'
    dirty.value = true
    await refreshSelected()
    return
  }
  selected.value.metric = key
  bindError.value = ''
  dirty.value = true
  await refreshSelected()
}

function isKpi(comp: Comp) {
  return comp.type === 'KPI'
}
function isTable(comp: Comp) {
  return comp.type === 'TABLE' || comp.type === 'DETAIL_TABLE'
}
function isChart(comp: Comp) {
  return ['LINE', 'BAR', 'AREA', 'PIE', 'DONUT', 'RADAR', 'FUNNEL', 'SCATTER'].includes(comp.type)
}

function previewOf(comp: Comp): Preview {
  return previewById.value[comp.id] || { columns: [], rows: [], error: '' }
}

function formatNum(value: unknown) {
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value ?? '')
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function linePoints(comp: Comp) {
  const rows = previewOf(comp).rows
  const width = Math.max(comp.w - 24, 80)
  if (!rows.length) return ''
  return rows
    .map((row, index) => {
      const x = rows.length === 1 ? width / 2 : (index / (rows.length - 1)) * (width - 8) + 4
      const value = Number(row.value ?? 0)
      const max = Math.max(...rows.map((item) => Number(item.value ?? 0)), 1)
      const y = 68 - (value / max) * 60
      return `${x},${y}`
    })
    .join(' ')
}

async function refreshComp(comp: Comp) {
  try {
    const res = await http.post('/bi/report/query', {
      reportId: reportId.value,
      compId: comp.id,
      components: comps.value,
    })
    previewById.value = {
      ...previewById.value,
      [comp.id]: { columns: res.data.data.columns || [], rows: res.data.data.rows || [], error: '' },
    }
    bindError.value = ''
  } catch (err) {
    const body = err as { code?: number; msg?: string }
    const text = body.code === 1191 ? '字段引用非法（1191）' : body.code === 1192 ? '计算字段表达式非法（1192）' : body.msg || '查询失败'
    if (body.code === 1191 || body.code === 1192) bindError.value = text
    previewById.value = { ...previewById.value, [comp.id]: { columns: [], rows: [], error: text } }
  }
}

async function refreshSelected() {
  if (selected.value) await refreshComp(selected.value)
}

async function loadMeta() {
  const ds = await http.get('/bi/report/datasets')
  if (ds.data.code === 0) {
    datasets.value = ds.data.data.datasets || []
    compLib.value = ds.data.data.compLib || []
  }
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
  layoutMode.value = res.data.data.layoutMode || 'FREE'
  comps.value = ((res.data.data.comps || []) as Comp[]).map((item) => ({
    dimension: '',
    metric: '',
    agg: 'SUM',
    calcExpression: '',
    dataset: 'METRIC_LIB',
    ...item,
  }))
  dirty.value = false
  undoStack.value = []
  if (comps.value.length) {
    selectedId.value = comps.value[0].id
    await Promise.all(comps.value.filter((item) => item.metric || item.type === 'TABLE').map((item) => refreshComp(item)))
  }
}

async function saveLayout() {
  if (!reportId.value) return
  saving.value = true
  try {
    const res = await http.put(`/bi/report/${reportId.value}`, {
      reportName: report.value?.reportName,
      layoutJson: { layoutMode: layoutMode.value || 'FREE', comps: comps.value },
    })
    if (res.data.code !== 0) {
      previewMsg.value = res.data.msg || '保存失败'
      return
    }
    report.value = res.data.data
    dirty.value = false
    previewMsg.value = '已保存'
  } catch (err) {
    const body = err as { msg?: string }
    previewMsg.value = body.msg || '保存失败'
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
  allowLeave = true
  await router.push({ path: '/ims/bi/report/preview', query: { reportId: String(reportId.value) } })
}

async function publish() {
  await saveLayout()
  if (previewMsg.value !== '已保存') return
  try {
    const res = await http.post(`/bi/report/${reportId.value}/publish`)
    previewMsg.value = `已发布 · ${res.data.data.status}`
    report.value = { ...report.value!, status: res.data.data.status }
    dirty.value = false
  } catch (err) {
    const body = err as { msg?: string }
    previewMsg.value = body.msg || '发布失败'
  }
}

async function runPreview() {
  const comp = selected.value
  if (comp) {
    await refreshComp(comp)
    const view = previewOf(comp)
    previewMsg.value = view.error || `预览 ${view.rows.length} 行 · SYNC`
    return
  }
  try {
    const res = await http.post('/bi/report/query', {
      reportId: reportId.value,
      compId: 'preview',
      components: comps.value,
    })
    previewMsg.value = `预览 ${res.data.data.total} 行 · ${res.data.data.status}`
  } catch (err) {
    const body = err as { msg?: string }
    previewMsg.value = body.msg || '预览失败'
  }
}

function requestLeave(path = '/ims/bi/report/list') {
  leaveTo.value = path
  if (!dirty.value) {
    allowLeave = true
    void router.push(path)
    return
  }
  leaveAsk.value = true
}

function stay() {
  leaveAsk.value = false
}

function confirmLeave() {
  leaveAsk.value = false
  allowLeave = true
  dirty.value = false
  void router.push(leaveTo.value)
}

function onUnload(event: BeforeUnloadEvent) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave((to) => {
  if (allowLeave || !dirty.value) return true
  leaveTo.value = to.fullPath
  leaveAsk.value = true
  return false
})

onMounted(async () => {
  window.addEventListener('mouseup', onWindowMouseUp, true)
  window.addEventListener('beforeunload', onUnload)
  await loadMeta()
  await loadReport()
})

onUnmounted(() => {
  window.removeEventListener('mouseup', onWindowMouseUp, true)
  window.removeEventListener('beforeunload', onUnload)
})
</script>
