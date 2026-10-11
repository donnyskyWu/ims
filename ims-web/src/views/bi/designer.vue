<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>报表设计器</h1>
        <div class="sub">
          {{ report?.reportName || '加载中…' }} · {{ report?.status === 'PUBLISHED' ? '已发布' : '新建草稿' }} · v{{ report?.version || 1 }} · 隐藏路由 /ims/bi/report/designer · BI-001
          <span v-if="dirty" data-testid="bi-dirty"> · ● 有未保存修改</span>
        </div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-back" @click="requestLeave()">返回报表管理</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-undo" :disabled="!undoStack.length" @click="undo">撤销</button>
        <button class="btn btn-sm" type="button" data-testid="bi-free-layout" :class="layoutMode === 'FREE' ? 'btn-pri' : 'btn-sec'" @click="useFreeLayout">自由布局</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="bi-device-preview" @click="deviceOpen = !deviceOpen">终端预览</button>
        <button class="btn btn-sec btn-sm" type="button" @click="runPreview">运行预览</button>
        <button v-if="canWrite" v-perm="'bi:report:edit'" class="btn btn-pri btn-sm" type="button" :disabled="saving" data-testid="bi-save" @click="saveLayout()">保存草稿</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="bi-open-drill" @click="openDrill">预览下钻</button>
        <button v-if="canWrite" v-perm="'bi:report:edit'" class="btn btn-pri btn-sm" type="button" data-testid="bi-publish" @click="openPublish()">保存并发布</button>
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
          <div :data-testid="`bi-comp-group-${group.key}`">
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

          <button v-if="canWrite" v-perm="'bi:report:edit'" class="btn btn-sec btn-sm" type="button" style="margin-top: 12px" data-testid="bi-comp-delete" @click="removeSelected">删除组件</button>
        </template>
        <div v-else class="csub" style="margin-top: 12px">选中画布组件以编辑。未选中时这里是报表级属性（名称 / 自由布局）。</div>
      </div>
    </div>

    <div v-if="publishOpen" class="modal-mask" data-testid="bi-publish-drawer" @click.self="publishOpen = false">
      <div class="card" style="width: 520px; padding: 18px">
        <h3 style="margin: 0 0 8px">发布配置</h3>
        <p class="csub">当前版本 v{{ report?.version || 1 }}。立即发布后，可见范围内的用户可以在报表管理看到这张报表。</p>
        <label class="fld">发布去向</label>
        <div data-testid="bi-publish-dest">
          <label class="csub" style="display: block; margin-top: 6px">
            <input v-model="publishForm.dests" type="checkbox" value="CENTER" /> 发布到报表中心
          </label>
          <label class="csub" style="display: block; margin-top: 6px">
            <input v-model="publishForm.dests" type="checkbox" value="MENU" /> 单独发布为菜单
          </label>
        </div>
        <template v-if="publishForm.dests.includes('MENU')">
          <label class="fld">菜单名称</label>
          <input v-model="publishForm.menuName" class="fld-in" data-testid="bi-publish-menu" placeholder="侧栏显示名" />
          <p class="csub">勾选后出现在侧栏「数据决策」，不改菜单权限种子。</p>
        </template>
        <label class="fld">访问方式</label>
        <select v-model="publishForm.accessType" class="fld-in" data-testid="bi-publish-access">
          <option value="SHARE_LINK">发布链接</option>
          <option value="SSO">站内授权</option>
        </select>
        <label class="fld">有效期（天，7~30）</label>
        <input v-model.number="publishForm.expireDays" class="fld-in" type="number" min="7" max="30" data-testid="bi-publish-expire" />
        <label class="csub" style="display: flex; align-items: center; gap: 8px; margin-top: 8px">
          <input v-model="publishForm.passwordEnabled" type="checkbox" data-testid="bi-publish-password-on" /> 访问密码
        </label>
        <input v-if="publishForm.passwordEnabled" v-model="publishForm.password" class="fld-in" type="password" data-testid="bi-publish-password" placeholder="至少 8 位" />
        <label class="fld">可见范围</label>
        <select v-model="publishForm.shareScope" class="fld-in" data-testid="bi-publish-scope">
          <option value="PRIVATE">私有</option>
          <option value="SPECIFIED">指定人</option>
          <option value="ALL">全员</option>
        </select>
        <template v-if="publishForm.shareScope === 'SPECIFIED'">
          <label class="fld">可见用户</label>
          <select v-model="publishForm.viewerId" class="fld-in" data-testid="bi-publish-viewer">
            <option value="">请选择</option>
            <option v-for="user in viewers" :key="user.id" :value="String(user.id)">{{ user.nickname || user.username }}（{{ user.username }}）</option>
          </select>
        </template>
        <label class="fld">操作权限</label>
        <select v-model="publishForm.opPerm" class="fld-in" data-testid="bi-publish-op">
          <option value="READONLY">只读</option>
          <option value="EXPORT">可导出</option>
          <option value="COPY">可复制</option>
        </select>
        <label class="fld">行权限</label>
        <select v-model="publishForm.rowPerm" class="fld-in" data-testid="bi-publish-row">
          <option value="INHERIT">继承数据权限</option>
          <option value="SNAPSHOT">锁定发布快照</option>
        </select>
        <p v-if="publishError" class="hint" data-testid="bi-publish-error" style="color: var(--red)">{{ publishError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="publishOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="bi-publish-now" @click="confirmPublish()">立即发布</button>
        </div>
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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
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
  version?: number
  shareScope?: string
  opPerm?: string
  rowPerm?: string
  publishDest?: string
  menuName?: string
  viewerIds?: number[]
  accessType?: string
  expireDays?: number
  hasPassword?: boolean
  canEdit?: boolean
}

type Viewer = { id: number; username: string; nickname?: string }

/** 与页面规格 BiCompType、后端 app.bi_report.BiCompType 同序，验收 22 格。 */
type BiCompType =
  | 'KPI'
  | 'BAR'
  | 'LINE'
  | 'PIE'
  | 'DONUT'
  | 'RADAR'
  | 'FUNNEL'
  | 'SCATTER'
  | 'TABLE'
  | 'DETAIL_TABLE'
  | 'RICH_TEXT'
  | 'DATE_RANGE'
  | 'SELECT_SINGLE'
  | 'SELECT_MULTI'
  | 'TEXT_INPUT'
  | 'NUMBER_RANGE'
  | 'GROUP'
  | 'CARD'
  | 'TAB'
  | 'BUTTON'
  | 'LINK'
  | 'TRIGGER'

const BI_COMP_TYPES: BiCompType[] = [
  'KPI',
  'BAR',
  'LINE',
  'PIE',
  'DONUT',
  'RADAR',
  'FUNNEL',
  'SCATTER',
  'TABLE',
  'DETAIL_TABLE',
  'RICH_TEXT',
  'DATE_RANGE',
  'SELECT_SINGLE',
  'SELECT_MULTI',
  'TEXT_INPUT',
  'NUMBER_RANGE',
  'GROUP',
  'CARD',
  'TAB',
  'BUTTON',
  'LINK',
  'TRIGGER',
]

type CompMeta = { type: BiCompType; name: string; group?: string; defaultSize: { w: number; h: number } }

type Preview = { columns: string[]; rows: Record<string, unknown>[]; error: string }

const route = useRoute()
const router = useRouter()
const reportId = computed(() => Number(route.query.reportId || 0))
const pendingComp = ref<CompMeta | null>(null)
let html5Handled = false
let droppedOnCanvas = false
const report = ref<ReportVo | null>(null)
const editAllowed = ref(false)
const canWrite = computed(() => editAllowed.value && report.value?.canEdit !== false)
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
const publishOpen = ref(false)
const publishError = ref('')
const viewers = ref<Viewer[]>([])
const publishForm = reactive({
  dests: ['CENTER'] as string[],
  menuName: '',
  shareScope: 'PRIVATE',
  viewerId: '',
  opPerm: 'READONLY',
  rowPerm: 'INHERIT',
  accessType: 'SHARE_LINK',
  expireDays: 7,
  passwordEnabled: false,
  password: '',
})
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

function isCompType(value: string): value is BiCompType {
  return (BI_COMP_TYPES as string[]).includes(value)
}

function readCompLib(raw: unknown): CompMeta[] {
  if (!Array.isArray(raw)) return []
  const items: CompMeta[] = []
  for (const row of raw) {
    if (!row || typeof row !== 'object') continue
    const record = row as { type?: string; name?: string; group?: string; defaultSize?: { w?: number; h?: number } }
    const type = String(record.type || '')
    if (!isCompType(type)) continue
    items.push({
      type,
      name: String(record.name || type),
      group: String(record.group || 'CHART'),
      defaultSize: { w: Number(record.defaultSize?.w || 80), h: Number(record.defaultSize?.h || 80) },
    })
  }
  return items
}

function paletteOf(group: string) {
  const byType = new Map(compLib.value.map((item) => [item.type, item]))
  return BI_COMP_TYPES.flatMap((type) => {
    const item = byType.get(type)
    if (!item || (item.group || 'CHART') !== group) return []
    return [item]
  })
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
  return ['LINE', 'BAR', 'PIE', 'DONUT', 'RADAR', 'FUNNEL', 'SCATTER'].includes(comp.type)
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

function calcLooksIllegal(expr: string) {
  const text = expr.trim()
  if (!text) return false
  return text.split('(').length !== text.split(')').length
}

async function refreshComp(comp: Comp) {
  const calc = String(comp.calcExpression || '')
  if (calcLooksIllegal(calc)) {
    const text = '计算字段表达式非法'
    bindError.value = text
    previewById.value = { ...previewById.value, [comp.id]: { columns: [], rows: [], error: text } }
    return
  }
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
    const text = body.code === 1191 ? '字段引用非法（1191）' : body.code === 1192 ? '计算字段表达式非法' : body.msg || '查询失败'
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
    compLib.value = readCompLib(ds.data.data.compLib)
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
  try {
    const perm = await http.get('/bi/report/edit-perm')
    editAllowed.value = Boolean(perm.data.data?.allowed)
  } catch {
    editAllowed.value = false
  }
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

async function saveLayout(keepVersion = false) {
  if (!reportId.value) return
  // 按钮若写成 @click="saveLayout" 会把 MouseEvent 传进来，后端 keepVersion 不是 bool 会 422。
  const keep = keepVersion === true
  saving.value = true
  try {
    const res = await http.put(`/bi/report/${reportId.value}`, {
      reportName: report.value?.reportName,
      layoutJson: { layoutMode: layoutMode.value || 'FREE', comps: comps.value },
      keepVersion: keep,
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

function fillPublishForm() {
  const current = report.value
  const dests = String(current?.publishDest || 'CENTER')
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item === 'CENTER' || item === 'MENU')
  publishForm.dests = dests.length ? dests : ['CENTER']
  publishForm.menuName = current?.menuName || ''
  publishForm.shareScope = current?.shareScope || 'PRIVATE'
  publishForm.viewerId = current?.viewerIds?.[0] ? String(current.viewerIds[0]) : ''
  publishForm.opPerm = current?.opPerm || 'READONLY'
  publishForm.rowPerm = current?.rowPerm || 'INHERIT'
  publishForm.accessType = current?.accessType || 'SHARE_LINK'
  publishForm.expireDays = current?.expireDays || 7
  publishForm.passwordEnabled = Boolean(current?.hasPassword)
  publishForm.password = ''
}

async function openPublish() {
  publishError.value = ''
  fillPublishForm()
  publishOpen.value = true
  if (viewers.value.length) return
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 50 } })
    viewers.value = (res.data.data?.list || []) as Viewer[]
  } catch {
    viewers.value = []
  }
}

async function confirmPublish() {
  publishError.value = ''
  if (!publishForm.dests.length) {
    publishError.value = '请选择发布去向'
    return
  }
  if (publishForm.dests.includes('MENU') && !publishForm.menuName.trim()) {
    publishError.value = '请填写菜单名称'
    return
  }
  if (publishForm.expireDays < 7 || publishForm.expireDays > 30) {
    publishError.value = '分享有效期须为 7~30 天'
    return
  }
  if (publishForm.passwordEnabled && publishForm.password.trim().length < 8) {
    publishError.value = '密码至少 8 位'
    return
  }
  if (publishForm.shareScope === 'SPECIFIED' && !publishForm.viewerId) {
    publishError.value = '请选择可见用户'
    return
  }
  const again = report.value?.status === 'PUBLISHED'
  await saveLayout(again)
  if (previewMsg.value !== '已保存') {
    publishError.value = previewMsg.value || '请先保存草稿'
    return
  }
  try {
    const res = await http.post(`/bi/report/${reportId.value}/publish`, {
      dests: publishForm.dests,
      menuName: publishForm.menuName.trim(),
      shareScope: publishForm.shareScope,
      opPerm: publishForm.opPerm,
      rowPerm: publishForm.rowPerm,
      viewerIds: publishForm.shareScope === 'SPECIFIED' ? [Number(publishForm.viewerId)] : [],
      accessType: publishForm.accessType,
      expireDays: publishForm.expireDays,
      passwordEnabled: publishForm.passwordEnabled,
      password: publishForm.password,
    })
    const data = res.data.data
    report.value = {
      ...report.value!,
      status: data.status,
      version: data.version,
      shareScope: data.shareScope,
      opPerm: data.opPerm,
      rowPerm: data.rowPerm,
      publishDest: data.publishDest,
      menuName: data.menuName,
      accessType: data.accessType,
      expireDays: data.expireDays,
      hasPassword: data.hasPassword,
      viewerIds: data.viewerIds,
    }
    previewMsg.value = data.menuNote ? `已发布 · v${data.version} · ${data.menuNote}` : `已发布 · v${data.version}`
    dirty.value = false
    publishOpen.value = false
  } catch (err) {
    const body = err as { msg?: string }
    publishError.value = body.msg || '发布失败'
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
