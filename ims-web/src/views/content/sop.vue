<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>SOP 管理</h1>
        <div class="sub">SOP 模板列表与节点编排（CONTENT-100 · SOP 免审）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openCreate">新增模板</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      运行时 SSOT：<code>/admin-api/ims/content/**</code> · 保存即启用新版本，无 SOP 审核页。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="keyword" placeholder="模板名称" style="width: 160px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>内容类型</th>
              <th>级别</th>
              <th>版本</th>
              <th>节点数</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8">
                <div class="empty"><div class="et">{{ error || '暂无 SOP 模板' }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.sopCode }}</td>
              <td><b>{{ row.sopName }}</b></td>
              <td>{{ row.contentType }}</td>
              <td>{{ row.sopLevel }}</td>
              <td class="num">v{{ row.version }}</td>
              <td class="num">{{ row.nodeCount }}</td>
              <td>{{ row.status }}</td>
              <td class="acts-inline">
                <button class="btn btn-sec btn-sm" type="button" @click="openNodes(row)">节点</button>
                <button class="btn btn-sec btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn btn-sec btn-sm" type="button" @click="removeSop(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="editorOpen" :title="editorTitle" width="1100px" @close="editorOpen = false">
      <p v-if="editingId" class="hint">
        当前 v{{ editingVersion }}，保存生成 v{{ editingVersion + 1 }}。进行中计划沿用旧版本。SOP 免审，保存即启用。
      </p>
      <p v-else class="hint">保存即启用（免审）。从左侧节点库加入画布，用前置节点连成 DAG。</p>
      <div class="formrow">
        <div class="fld">
          <label>模板名称 *</label>
          <input v-model="form.sopName" maxlength="128" />
        </div>
        <div class="fld">
          <label>内容类型 *</label>
          <input v-model="form.contentType" placeholder="SHORT_VIDEO" />
        </div>
        <div class="fld">
          <label>级别</label>
          <select v-model="form.sopLevel">
            <option value="STANDARD">STANDARD</option>
            <option value="GUIDE">GUIDE</option>
          </select>
        </div>
        <div class="fld">
          <label>营销计划（工作任务匹配）</label>
          <select v-model="form.marketingPlan">
            <option value="">— 计划轨 —</option>
            <option value="LIVE_PUBLIC">LIVE_PUBLIC · 直播公推</option>
            <option value="PAID_SALES">PAID_SALES · 付费销售</option>
          </select>
        </div>
      </div>
      <p v-if="banner" class="hint bad" data-testid="sop-dag-error">{{ banner }}</p>
      <div class="dag-wrap sop-dag">
        <div class="dag-pal">
          <h4>节点库</h4>
          <button class="dag-item" type="button" @click="addNode('CONTENT_GENERATION')">
            内容生成<small>CONTENT_GENERATION</small>
          </button>
          <button class="dag-item" type="button" @click="addNode('CONTENT_PUBLISH')">
            内容发布<small>CONTENT_PUBLISH</small>
          </button>
          <button class="dag-item" type="button" @click="addNode('NORMAL')">
            普通节点<small>NORMAL</small>
          </button>
        </div>
        <div class="dag-canvas" data-testid="sop-dag-canvas" :style="{ height: canvasHeight + 'px' }">
          <svg class="dag-svg" :width="canvasWidth" :height="canvasHeight">
            <defs>
              <marker id="sop-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#8e8e93" />
              </marker>
            </defs>
            <line
              v-for="edge in edges"
              :key="edge.key"
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              stroke="#8e8e93"
              stroke-width="1.5"
              marker-end="url(#sop-arrow)"
            />
          </svg>
          <div
            v-for="node in nodes"
            :key="node.key"
            class="dag-node"
            :class="{ on: node.key === selectedKey }"
            :style="{ left: node.x + 'px', top: node.y + 'px' }"
            :data-testid="'sop-dag-node'"
            @pointerdown="onDragStart($event, node)"
          >
            <div class="dn">{{ node.nodeName || '未命名' }}</div>
            <div class="dt">{{ nodeTypeLabel(node.nodeType) }}</div>
          </div>
        </div>
        <div v-if="selected" class="dag-prop">
          <h4>节点属性</h4>
          <div class="fld">
            <label>{{ isFirst ? '首节点名称 *' : '节点名称 *' }}</label>
            <input v-model="selected.nodeName" :placeholder="isFirst ? '脚本' : '节点名称'" maxlength="64" />
          </div>
          <div class="fld">
            <label>{{ isFirst ? '首节点类型' : '节点类型' }}</label>
            <select v-model="selected.nodeType">
              <option value="NORMAL">NORMAL</option>
              <option value="CONTENT_GENERATION">CONTENT_GENERATION</option>
              <option value="CONTENT_PUBLISH">CONTENT_PUBLISH</option>
            </select>
          </div>
          <div v-if="selected.nodeType === 'CONTENT_GENERATION'" class="fld">
            <label>文档类型</label>
            <select v-model="selected.documentType">
              <option value="COPY">COPY</option>
              <option value="SCRIPT">SCRIPT</option>
              <option value="OFFICIAL_PLAN">OFFICIAL_PLAN</option>
            </select>
          </div>
          <div class="fld">
            <label>执行岗位 *</label>
            <select v-model="selected.ownerRole">
              <option value="">— 请选择 —</option>
              <option value="R6">R6</option>
              <option value="R8">R8</option>
              <option value="R10">R10</option>
              <option value="R4">R4</option>
            </select>
          </div>
          <div class="fld">
            <label>前置节点</label>
            <div v-if="!otherNodes.length" class="hint">无其它节点</div>
            <label v-for="other in otherNodes" :key="other.key" class="dag-pred">
              <input
                type="checkbox"
                :checked="selected.predecessorKeys.includes(other.key)"
                @change="togglePred(other.key)"
              />
              {{ other.nodeName || '未命名' }}
            </label>
          </div>
          <div class="fld">
            <label>并行组</label>
            <input v-model="selected.parallelGroup" maxlength="64" placeholder="可空" />
          </div>
          <div class="fld">
            <label>SLA（小时）*</label>
            <input v-model.number="selected.slaHours" type="number" min="1" />
          </div>
          <div class="fld">
            <label>执行标准</label>
            <input v-model="selected.standardDesc" maxlength="1024" />
          </div>
          <div class="fld">
            <label>节点需审核</label>
            <select v-model.number="selected.needReview">
              <option :value="0">0 · 否（模板本身免审）</option>
              <option :value="1">1 · 是</option>
            </select>
          </div>
          <div v-if="selected.needReview === 1" class="fld">
            <label>审核岗位</label>
            <select v-model="selected.reviewerRole">
              <option value="">— 请选择 —</option>
              <option value="R8">R8</option>
              <option value="R4">R4</option>
              <option value="R1">R1</option>
            </select>
          </div>
          <button class="btn btn-sec btn-sm" type="button" :disabled="nodes.length < 2" @click="removeNode(selected.key)">
            移除节点
          </button>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="editorOpen = false">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving || !!dagError" @click="saveSop">
          {{ editingId ? '保存新版本' : '保存' }}
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="nodesOpen" :title="nodeTitle" width="640px" @close="nodesOpen = false">
      <div v-if="nodesLoading" class="empty"><div class="et">加载中</div></div>
      <ul v-else class="tl">
        <li v-for="n in detailNodes" :key="n.id" class="tl-i">
          <b>{{ n.nodeOrder }}. {{ n.nodeName }}</b>
          <div class="hint">
            {{ n.nodeType || 'NORMAL' }}
            <span v-if="n.documentType"> · {{ n.documentType }}</span>
            · 岗位 {{ n.ownerRole || '—' }}
            · 前置 {{ predLabel(n) }}
            <span v-if="n.parallelGroup"> · 并行 {{ n.parallelGroup }}</span>
          </div>
          <div class="hint">{{ n.standardDesc || '—' }}</div>
        </li>
      </ul>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type SopRow = {
  id: number
  sopName: string
  sopCode?: string
  contentType?: string
  sopLevel?: string
  version: number
  marketingPlan?: string
}

type EditorNode = {
  key: string
  nodeName: string
  nodeType: string
  documentType: string
  standardDesc: string
  ownerRole: string
  slaHours: number
  predecessorKeys: string[]
  parallelGroup: string
  needReview: number
  reviewerRole: string
  x: number
  y: number
}

type NodeVo = {
  id: number
  nodeOrder: number
  nodeName: string
  nodeType?: string
  documentType?: string
  standardDesc?: string
  ownerRole?: string
  slaHours?: number
  predecessors?: number[]
  parallelGroup?: string
  needReview?: number
  reviewerRole?: string
}

const rows = ref<SopRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const editorOpen = ref(false)
const saving = ref(false)
const saveError = ref('')
const editingId = ref<number | null>(null)
const editingVersion = ref(1)
const form = ref({
  sopName: '',
  contentType: 'SHORT_VIDEO',
  sopLevel: 'STANDARD',
  marketingPlan: '',
})
const nodes = ref<EditorNode[]>([])
const selectedKey = ref('')
let keySeq = 1

const nodesOpen = ref(false)
const nodesLoading = ref(false)
const detailNodes = ref<NodeVo[]>([])
const nodeTitle = ref('节点详情')

const editorTitle = computed(() => (editingId.value ? '编辑 SOP 模板' : '新增 SOP 模板'))
const selectedIndex = computed(() => nodes.value.findIndex((n) => n.key === selectedKey.value))
const selected = computed(() => (selectedIndex.value >= 0 ? nodes.value[selectedIndex.value] : null))
const isFirst = computed(() => selectedIndex.value === 0)
const otherNodes = computed(() => nodes.value.filter((n) => n.key !== selectedKey.value))

const dagError = computed(() => validateLocal())
const banner = computed(() => saveError.value || dagError.value)

const canvasWidth = computed(() => {
  const maxX = nodes.value.reduce((m, n) => Math.max(m, n.x + 180), 480)
  return Math.max(520, maxX)
})
const canvasHeight = computed(() => {
  const maxY = nodes.value.reduce((m, n) => Math.max(m, n.y + 90), 280)
  return Math.max(360, maxY)
})

const edges = computed(() => {
  const byKey = new Map(nodes.value.map((n) => [n.key, n]))
  const lines: { key: string; x1: number; y1: number; x2: number; y2: number }[] = []
  for (const node of nodes.value) {
    for (const predKey of node.predecessorKeys) {
      const pred = byKey.get(predKey)
      if (!pred) continue
      lines.push({
        key: `${pred.key}->${node.key}`,
        x1: pred.x + 156,
        y1: pred.y + 28,
        x2: node.x,
        y2: node.y + 28,
      })
    }
  }
  return lines
})

function nodeTypeLabel(nodeType: string) {
  if (nodeType === 'CONTENT_GENERATION') return '内容生成'
  if (nodeType === 'CONTENT_PUBLISH') return '内容发布'
  return '普通节点'
}

function nextKey() {
  keySeq += 1
  return `k${keySeq}`
}

function placeAt(index: number) {
  return { x: 24 + (index % 3) * 190, y: 24 + Math.floor(index / 3) * 110 }
}

function makeNode(partial: Partial<EditorNode> & { nodeType: string }, index: number): EditorNode {
  const pos = placeAt(index)
  return {
    key: partial.key || nextKey(),
    nodeName: partial.nodeName || nodeTypeLabel(partial.nodeType),
    nodeType: partial.nodeType,
    documentType: partial.documentType || (partial.nodeType === 'CONTENT_GENERATION' ? 'COPY' : ''),
    standardDesc: partial.standardDesc || '执行标准',
    ownerRole: partial.ownerRole || 'R6',
    slaHours: partial.slaHours || 24,
    predecessorKeys: partial.predecessorKeys || [],
    parallelGroup: partial.parallelGroup || '',
    needReview: partial.needReview || 0,
    reviewerRole: partial.reviewerRole || '',
    x: partial.x ?? pos.x,
    y: partial.y ?? pos.y,
  }
}

function defaultNodes(): EditorNode[] {
  return [makeNode({ key: 'k1', nodeName: '脚本', nodeType: 'NORMAL' }, 0)]
}

function validateLocal(): string {
  if (!nodes.value.length) return '请填写节点名称'
  const names = nodes.value.map((n) => n.nodeName.trim()).filter(Boolean)
  if (names.length !== nodes.value.length) return '请填写节点名称'
  if (new Set(names).size !== names.length) return '节点名重复'
  for (const node of nodes.value) {
    if (!node.ownerRole.trim()) return '节点缺执行岗位'
    if (node.nodeType === 'CONTENT_GENERATION' && !node.documentType) return '内容生成节点须填写文档类型'
    if (node.needReview === 1 && !node.reviewerRole) return '审核岗位必填'
    if (!node.slaHours || node.slaHours < 1) return 'SLA 须 ≥ 1'
  }
  const color = new Map<string, number>()
  const byKey = new Map(nodes.value.map((n) => [n.key, n]))
  function walk(key: string): boolean {
    color.set(key, 1)
    const node = byKey.get(key)
    if (!node) return false
    for (const pred of node.predecessorKeys) {
      const state = color.get(pred) || 0
      if (state === 1) return true
      if (state === 0 && walk(pred)) return true
    }
    color.set(key, 2)
    return false
  }
  for (const node of nodes.value) {
    if (!color.get(node.key) && walk(node.key)) return 'DAG 存在环'
  }
  return ''
}

function payloadNodes() {
  const orderOf = new Map(nodes.value.map((n, i) => [n.key, i + 1]))
  return nodes.value.map((node, i) => ({
    nodeOrder: i + 1,
    nodeName: node.nodeName.trim(),
    nodeType: node.nodeType,
    documentType: node.nodeType === 'CONTENT_GENERATION' ? node.documentType : '',
    standardDesc: node.standardDesc || '执行标准',
    deliverableSpec: {},
    qualityChecklist: [{ itemCode: 'OK', itemDesc: '交付合格', required: true }],
    ownerRole: node.ownerRole,
    slaHours: node.slaHours || 24,
    predecessors: node.predecessorKeys.map((k) => orderOf.get(k)).filter((n): n is number => !!n),
    parallelGroup: node.parallelGroup || '',
    needReview: node.needReview ? 1 : 0,
    reviewerRole: node.needReview ? node.reviewerRole : '',
  }))
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/sop/list', {
      params: { pageNo: 1, pageSize: 50, keyword: keyword.value || undefined },
    })
    rows.value = data.data.list
    total.value = data.data.total
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  editingVersion.value = 1
  saveError.value = ''
  form.value = { sopName: '', contentType: 'SHORT_VIDEO', sopLevel: 'STANDARD', marketingPlan: '' }
  nodes.value = defaultNodes()
  selectedKey.value = nodes.value[0].key
  editorOpen.value = true
}

function addNode(nodeType: string) {
  const prev = nodes.value[nodes.value.length - 1]
  const node = makeNode(
    {
      nodeType,
      predecessorKeys: prev ? [prev.key] : [],
    },
    nodes.value.length,
  )
  nodes.value.push(node)
  selectedKey.value = node.key
  saveError.value = ''
}

function removeNode(key: string) {
  if (nodes.value.length < 2) return
  nodes.value = nodes.value
    .filter((n) => n.key !== key)
    .map((n) => ({ ...n, predecessorKeys: n.predecessorKeys.filter((k) => k !== key) }))
  if (!nodes.value.some((n) => n.key === selectedKey.value)) {
    selectedKey.value = nodes.value[0]?.key || ''
  }
}

function togglePred(key: string) {
  const node = selected.value
  if (!node || key === node.key) return
  const set = new Set(node.predecessorKeys)
  if (set.has(key)) set.delete(key)
  else set.add(key)
  node.predecessorKeys = [...set]
  saveError.value = ''
}

function onDragStart(ev: PointerEvent, node: EditorNode) {
  selectedKey.value = node.key
  const startX = ev.clientX
  const startY = ev.clientY
  const origX = node.x
  const origY = node.y
  const move = (e: PointerEvent) => {
    node.x = Math.max(8, origX + e.clientX - startX)
    node.y = Math.max(8, origY + e.clientY - startY)
  }
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

async function saveSop() {
  saveError.value = ''
  if (!form.value.sopName.trim() || !form.value.contentType.trim()) {
    saveError.value = '请填写模板名称与内容类型'
    return
  }
  if (dagError.value) return
  saving.value = true
  try {
    const body = {
      sopName: form.value.sopName.trim(),
      contentType: form.value.contentType.trim(),
      sopLevel: form.value.sopLevel,
      marketingPlan: form.value.marketingPlan || undefined,
      nodes: payloadNodes(),
    }
    if (editingId.value) {
      await http.put(`/content/sop/${editingId.value}`, body)
    } else {
      await http.post('/content/sop', body)
    }
    editorOpen.value = false
    await loadList()
  } catch (e) {
    saveError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function openEdit(row: SopRow) {
  saveError.value = ''
  nodes.value = []
  editingId.value = row.id
  editingVersion.value = row.version || 1
  form.value = {
    sopName: row.sopName,
    contentType: row.contentType || 'SHORT_VIDEO',
    sopLevel: row.sopLevel || 'STANDARD',
    marketingPlan: row.marketingPlan || '',
  }
  editorOpen.value = true
  try {
    const { data } = await http.get(`/content/sop/${row.id}/nodes`)
    const list = (data.data || []) as NodeVo[]
    const mapped = list.map((n, i) =>
      makeNode(
        {
          key: `o${n.nodeOrder}`,
          nodeName: n.nodeName,
          nodeType: n.nodeType || 'NORMAL',
          documentType: n.documentType || '',
          standardDesc: n.standardDesc || '',
          ownerRole: n.ownerRole || 'R6',
          slaHours: n.slaHours || 24,
          parallelGroup: n.parallelGroup || '',
          needReview: n.needReview || 0,
          reviewerRole: n.reviewerRole || '',
        },
        i,
      ),
    )
    const keyByOrder = new Map(list.map((n, i) => [n.nodeOrder, mapped[i].key]))
    list.forEach((n, i) => {
      mapped[i].predecessorKeys = (n.predecessors || [])
        .map((order) => keyByOrder.get(order))
        .filter((k): k is string => !!k)
    })
    nodes.value = mapped.length ? mapped : defaultNodes()
    selectedKey.value = nodes.value[0].key
  } catch (e) {
    nodes.value = defaultNodes()
    selectedKey.value = nodes.value[0].key
    saveError.value = errorMessage(e)
  }
}

async function removeSop(row: SopRow) {
  if (!confirm(`逻辑删除 SOP「${row.sopName}」v${row.version}？进行中计划沿用已挂版本。`)) return
  try {
    await http.delete(`/content/sop/${row.id}`, { params: { confirmText: 'DELETE' } })
    await loadList()
  } catch (e) {
    alert(errorMessage(e))
  }
}

function predLabel(node: NodeVo) {
  const preds = node.predecessors || []
  if (!preds.length) return '无'
  return preds
    .map((order) => {
      const hit = detailNodes.value.find((n) => n.nodeOrder === order)
      return hit ? hit.nodeName : String(order)
    })
    .join('、')
}

async function openNodes(row: SopRow) {
  nodeTitle.value = `节点 · ${row.sopName}`
  nodesOpen.value = true
  nodesLoading.value = true
  try {
    const { data } = await http.get(`/content/sop/${row.id}/nodes`)
    detailNodes.value = data.data
  } catch (e) {
    detailNodes.value = []
    alert(errorMessage(e))
  } finally {
    nodesLoading.value = false
  }
}

loadList()
</script>

<style scoped>
.sop-dag {
  min-height: 360px;
  margin-top: 12px;
}
.sop-dag .dag-canvas {
  min-height: 360px;
}
.dag-pred {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12.5px;
  margin: 4px 0;
}
.acts-inline {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
