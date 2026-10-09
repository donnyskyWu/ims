<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>穿透查询</h1>
        <div class="sub">DC-001 · /ims/dc/trace · GET/POST /dc/trace/* · 12 DC</div>
      </div>
    </div>
    <div class="hint" style="margin-bottom: 10px" data-testid="dc-trace-meta">
      <span v-if="dataAsOf">数据截至 <b>{{ dataAsOf }}</b> · </span>
      <router-link
        data-testid="dc-trace-query-cost"
        to="/ims/dc/trace/perf"
        :style="queryCostMs > 3000 ? { color: 'var(--orange)', fontWeight: '600' } : undefined"
      >queryCostMs {{ queried ? queryCostMs : '—' }} ms</router-link>
      ·
      <span
        data-testid="dc-trace-timeout-hint"
        :data-degraded="timeoutDegraded ? '1' : '0'"
        :style="timeoutDegraded ? { color: 'var(--orange)', fontWeight: '600' } : undefined"
      >{{ timeoutHint }}</span>
    </div>
    <form class="qbar" @submit.prevent="onSubmit">
      <select v-model="entryType" style="width: 132px" data-testid="dc-trace-entry-type" @change="onEntryTypeChange">
        <option value="PERSON">实名人</option>
        <option value="ACCOUNT">账号</option>
        <option value="ASSET">资产</option>
        <option value="SESSION">场次</option>
        <option value="RESPONSIBLE">责任人</option>
        <option value="IP_GROUP">IP组</option>
      </select>
      <input
        v-model="keyword"
        placeholder="关键词"
        style="width: 160px"
        data-testid="dc-trace-keyword"
      />
      <input v-model="dateFrom" type="date" data-testid="dc-trace-date-from" />
      <input v-model="dateTo" type="date" data-testid="dc-trace-date-to" />
      <button class="btn btn-sec btn-sm" type="button" data-testid="dc-trace-search-entry" @click="searchEntry">
        搜入口
      </button>
      <span class="sp"></span>
      <select v-model="exportFormat" style="width: 88px" data-testid="dc-trace-export-format">
        <option value="XLSX">XLSX</option>
        <option value="PDF">PDF</option>
      </select>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="dc-trace-export"
        :disabled="!selectedEntry"
        @click="exportReport"
      >
        导出链路报告
      </button>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-trace-submit">穿透查询</button>
    </form>
    <p v-if="exportNote" class="hint" data-testid="dc-trace-export-note">{{ exportNote }}</p>
    <div v-if="entries.length" class="hint" style="margin: 8px 0">
      入口：
      <button
        v-for="e in entries"
        :key="e.entryType + ':' + e.entryId"
        type="button"
        class="btn btn-sec btn-sm"
        style="margin-right: 6px"
        data-testid="dc-trace-entry-pick"
        :data-entry-type="e.entryType"
        :data-entry-id="e.entryId"
        :title="e.hint || ''"
        @click="pickEntry(e)"
      >
        {{ e.entryLabel }}
      </button>
    </div>
    <p v-else-if="searched" class="hint" data-testid="dc-trace-entry-empty">未找到入口</p>
    <p v-if="selectedEntry" class="hint" data-testid="dc-trace-current-entry">
      当前入口：{{ entryTypeLabel(selectedEntry.entryType) }} · {{ selectedEntry.entryLabel }}
    </p>
    <div v-if="crumbs.length" class="hint" data-testid="dc-trace-breadcrumb" style="margin: 8px 0">
      <button
        v-for="(crumb, index) in crumbs"
        :key="index"
        type="button"
        class="btn btn-sec btn-sm"
        style="margin-right: 6px"
        data-testid="dc-trace-crumb"
        :data-crumb-index="index"
        @click="truncateCrumb(index)"
      >
        {{ crumb.label }}
      </button>
    </div>
    <div
      v-if="queried && viewMode === 'SPLIT'"
      class="hint"
      data-testid="dc-trace-relation-chips"
      style="margin: 8px 0"
    >
      关联下钻
      <button
        v-for="chip in relationChips"
        :key="chip.entryType + ':' + chip.entryId"
        type="button"
        class="btn btn-sec btn-sm"
        style="margin-left: 6px"
        data-testid="dc-trace-relation-chip"
        :data-entry-type="chip.entryType"
        :data-entry-id="chip.entryId"
        @click="drillEntry(chip)"
      >
        {{ chip.relation }} · {{ chip.entryLabel }}
      </button>
      <span v-if="!assetChips.length" data-testid="dc-trace-asset-empty" style="margin-left: 8px">暂无绑定资产</span>
      <span v-if="!ownerChips.length" data-testid="dc-trace-owner-empty" style="margin-left: 8px">暂无责任人</span>
      <span v-if="!ipChips.length" data-testid="dc-trace-ip-group-empty" style="margin-left: 8px">未关联 IP 组</span>
    </div>
    <div class="hint" style="margin: 8px 0">
      <button
        type="button"
        class="btn btn-sm"
        :class="viewMode === 'SPLIT' ? 'btn-pri' : 'btn-sec'"
        data-testid="dc-trace-mode-split"
        @click="viewMode = 'SPLIT'"
      >
        链路图/明细
      </button>
      <button
        type="button"
        class="btn btn-sm"
        :class="viewMode === 'AGGREGATE' ? 'btn-pri' : 'btn-sec'"
        data-testid="dc-trace-mode-aggregate"
        style="margin-left: 6px"
        @click="showAggregate"
      >
        聚合
      </button>
    </div>
    <div v-if="error" class="hint" style="color: var(--red)">{{ error }}</div>
    <div v-if="viewMode === 'AGGREGATE'" class="tbl-block" data-testid="dc-trace-aggregate" style="margin-top: 12px">
      <div class="hint" style="margin-bottom: 8px">
        汇总维度
        <select :value="aggregateBy" data-testid="dc-trace-aggregate-by" @change="onAggregateBy">
          <option value="PERSON">按人</option>
          <option value="ACCOUNT">按账号</option>
          <option value="TEAM">按团队</option>
          <option value="IP_GROUP">按IP组</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>维度</th>
              <th>场次数</th>
              <th>GMV</th>
              <th>总成本</th>
              <th>净利润</th>
              <th>涉及人数</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in aggregates"
              :key="row.dimensionValue"
              data-testid="dc-trace-aggregate-row"
              :data-dimension-value="row.dimensionValue"
            >
              <td>
                <button
                  v-if="aggregateBy !== 'TEAM'"
                  type="button"
                  class="btn btn-sec btn-sm"
                  data-testid="dc-trace-aggregate-drill"
                  :data-dimension-value="row.dimensionValue"
                  @click="drillAggregate(row)"
                >
                  {{ row.dimensionLabel }}
                </button>
                <template v-else>{{ row.dimensionLabel }}</template>
              </td>
              <td class="num">{{ row.sessionCount }}</td>
              <td class="num">{{ moneyOrDash(row.gmv) }}</td>
              <td class="num">{{ moneyOrDash(row.totalCost) }}</td>
              <td class="num">{{ moneyOrDash(row.netProfit) }}</td>
              <td class="num">{{ row.personCount }}</td>
            </tr>
            <tr v-if="!aggregates.length">
              <td colspan="6"><div class="empty"><div class="et">暂无汇总</div></div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="g2" style="margin-top: 12px">
      <div class="card" style="padding: 12px; min-height: 200px" data-testid="dc-trace-graph">
        <b style="font-size: 13px">关系图</b>
        <ul style="margin: 10px 0 0; padding-left: 18px; font-size: 12px">
          <li
            v-for="n in nodes"
            :key="n.nodeType + ':' + n.nodeId"
            :data-node-type="n.nodeType"
            :data-node-id="n.nodeId"
          >
            {{ n.nodeType }} ·
            <button
              v-if="n.nodeType === 'SESSION'"
              type="button"
              class="btn btn-sec btn-sm"
              @click="openSession(n.nodeId)"
            >
              {{ n.nodeLabel }}
            </button>
            <button
              v-else-if="n.nodeType === 'PERSON' || n.nodeType === 'ACCOUNT' || n.nodeType === 'ASSET'"
              type="button"
              class="btn btn-sec btn-sm"
              data-testid="dc-trace-node-drill"
              :data-node-type="n.nodeType"
              :data-node-id="n.nodeId"
              @click="drillNode(n)"
            >
              {{ n.nodeLabel }}
            </button>
            <span
              v-else-if="n.nodeType === 'COST'"
              data-testid="dc-trace-cost-node"
              :data-node-id="n.nodeId"
            >{{ n.nodeLabel }} {{ moneyOrDash(n.metrics?.totalCost) }}</span>
            <span
              v-else-if="n.nodeType === 'PROFIT'"
              data-testid="dc-trace-profit-node"
              :data-node-id="n.nodeId"
            >{{ n.nodeLabel }} {{ moneyOrDash(n.metrics?.netProfit) }}</span>
            <template v-else>{{ n.nodeLabel }}</template>
          </li>
        </ul>
        <p v-if="!nodes.length" class="csub" data-testid="dc-trace-graph-empty">
          {{ queried ? '该入口暂无关联场次' : '选择入口后查询' }}
        </p>
      </div>
      <div class="tbl-block" data-testid="dc-trace-detail-table">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>场次</th>
                <th>平台</th>
                <th>账号</th>
                <th>实名人</th>
                <th>关联资产</th>
                <th>GMV</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in details" :key="d.sessionCode">
                <td class="mono">
                  <button
                    type="button"
                    class="btn btn-sec btn-sm"
                    data-testid="dc-trace-session-open"
                    :data-session-code="d.sessionCode"
                    @click="openSession(d.sessionCode)"
                  >
                    {{ d.sessionCode }}
                  </button>
                </td>
                <td>{{ d.platform }}</td>
                <td>{{ d.accountNo }}</td>
                <td>{{ d.realnameName }}</td>
                <td>
                  <button
                    v-for="(assetId, index) in d.assetIds || []"
                    :key="assetId"
                    type="button"
                    class="btn btn-sec btn-sm"
                    style="margin-right: 4px"
                    data-testid="dc-trace-detail-asset"
                    :data-entry-id="assetId"
                    @click="drillAsset(d, index)"
                  >
                    {{ (d.assetLabels || [])[index] || `资产#${assetId}` }}
                  </button>
                  <span v-if="!(d.assetIds || []).length" data-testid="dc-trace-detail-asset-empty">—</span>
                </td>
                <td class="num">{{ moneyOrDash(d.gmv) }}</td>
              </tr>
              <tr v-if="!details.length">
                <td colspan="6"><div class="empty"><div class="et">暂无明细</div></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="drawerOpen" class="mask on" @click="drawerOpen = false"></div>
    <div
      v-if="drawerOpen && sessionDetail"
      class="drawer on"
      data-testid="dc-trace-session-drawer"
      style="width: 880px"
    >
      <div class="drawer-h">
        <b>场次明细 · {{ sessionDetail.sessionCode }}</b>
        <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
      </div>
      <div class="drawer-b">
        <p class="hint">
          {{ sessionDetail.sessionTitle }} · {{ sessionDetail.platform }} · 数据截至 {{ sessionDetail.dataAsOf }}
        </p>
        <div class="g2" style="margin: 12px 0">
          <div class="card stat">
            <span class="l">GMV</span>
            <div class="n">¥{{ fmt(sessionDetail.liveData?.gmv) }}</div>
          </div>
          <div class="card stat">
            <span class="l">净利润</span>
            <div class="n">{{ moneyOrDash(sessionDetail.profit?.netProfit) }}</div>
          </div>
        </div>
        <ul class="hint" style="line-height: 1.8; margin-bottom: 12px">
          <li>退款：¥{{ fmt(sessionDetail.liveData?.refund) }}</li>
          <li>UV：{{ sessionDetail.liveData?.uv ?? '—' }}</li>
          <li>时长：{{ sessionDetail.liveData?.durationMinutes ?? '—' }} 分钟</li>
          <li>毛利：{{ moneyOrDash(sessionDetail.profit?.grossProfit) }}</li>
          <li>经营利润：{{ moneyOrDash(sessionDetail.profit?.operatingProfit) }}</li>
          <li>净利率：{{ sessionDetail.profit?.netProfitRate == null ? '—' : sessionDetail.profit.netProfitRate + '%' }}</li>
          <li>计算版本：v{{ sessionDetail.profit?.calcVersion ?? 0 }}</li>
          <li>账号：{{ sessionDetail.account?.accountNo || '—' }}</li>
          <li
            v-for="p in sessionDetail.persons || []"
            :key="p.roleType + ':' + p.userId"
            data-testid="dc-trace-person-line"
          >
            {{ personRoleLabel(p.roleType) }}：{{ p.userName || '—' }}
            <button
              v-if="p.roleType === 'RESPONSIBLE' && p.userId"
              type="button"
              class="btn btn-sec btn-sm"
              data-testid="dc-trace-drawer-responsible"
              :data-entry-id="p.userId"
              @click="drillFromDrawer('RESPONSIBLE', String(p.userId), p.userName || `责任人#${p.userId}`)"
            >
              下钻责任人
            </button>
          </li>
          <li v-if="!(sessionDetail.assetIds || []).length" data-testid="dc-trace-drawer-asset-empty">
            关联资产：暂无绑定资产
          </li>
          <li v-for="(assetId, index) in sessionDetail.assetIds || []" :key="'asset-' + assetId">
            关联资产：
            <button
              type="button"
              class="btn btn-sec btn-sm"
              data-testid="dc-trace-drawer-asset"
              :data-entry-id="assetId"
              @click="drillFromDrawer('ASSET', String(assetId), (sessionDetail.assetLabels || [])[index] || `资产#${assetId}`)"
            >
              {{ (sessionDetail.assetLabels || [])[index] || `资产#${assetId}` }}
            </button>
          </li>
          <li v-if="sessionDetail.ipGroupId">
            IP组：
            <button
              type="button"
              class="btn btn-sec btn-sm"
              data-testid="dc-trace-drawer-ip-group"
              :data-entry-id="sessionDetail.ipGroupId"
              @click="drillFromDrawer('IP_GROUP', String(sessionDetail.ipGroupId), sessionDetail.ipGroupName || `IP组#${sessionDetail.ipGroupId}`)"
            >
              {{ sessionDetail.ipGroupName || `IP组#${sessionDetail.ipGroupId}` }}
            </button>
          </li>
          <li v-else data-testid="dc-trace-drawer-ip-empty">IP组：未关联 IP 组</li>
        </ul>
        <h3 style="font-size: 14px; margin-bottom: 6px">成本明细</h3>
        <table>
          <thead><tr><th>项目</th><th>金额</th></tr></thead>
          <tbody>
            <tr v-for="item in sessionDetail.costDetail || []" :key="item.costItem">
              <td>{{ item.costItemLabel || item.costItem }}</td>
              <td class="num">{{ item.amount == null ? '—' : '¥' + fmt(item.amount) }}</td>
            </tr>
            <tr v-if="!(sessionDetail.costDetail || []).length">
              <td colspan="2">暂无成本</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'

type Entry = { entryType: string; entryId: string; entryLabel: string; hint?: string }
type Node = {
  nodeType: string
  nodeId: string
  nodeLabel: string
  metrics?: { totalCost?: number | null; netProfit?: number | null; gmv?: number | null }
}
type Detail = {
  sessionCode: string
  platform: string
  accountNo: string
  realnameName: string
  assetIds?: number[]
  assetLabels?: string[]
  gmv?: number | null
  netProfit?: number | null
  responsibleUserId?: number
  responsibleUserName?: string
  ipGroupId?: number
  ipGroupName?: string
}
type RelationChip = { entryType: string; entryId: string; entryLabel: string; relation: string }
type AggregateRow = {
  dimensionValue: string
  dimensionLabel: string
  sessionCount: number
  gmv: number | null
  totalCost: number | null
  netProfit: number | null
  personCount: number
}
type Crumb = { label: string; entry: Entry }
type CostItem = { costItem: string; costItemLabel?: string; amount: number | null }
type SessionDetail = {
  sessionCode: string
  sessionTitle?: string
  platform?: string
  dataAsOf?: string
  liveData?: { gmv?: number; refund?: number; uv?: number | null; durationMinutes?: number | null }
  profit?: {
    grossProfit?: number | null
    operatingProfit?: number | null
    netProfit?: number | null
    netProfitRate?: number | null
    calcVersion?: number
  }
  costDetail?: CostItem[]
  account?: { accountNo?: string }
  persons?: Array<{ userId: number; userName: string; roleType: string }>
  assetIds?: number[]
  assetLabels?: string[]
  ipGroupId?: number
  ipGroupName?: string
}
type TracePayload = {
  queryCostMs?: number
  dataAsOf?: string
  nodes?: Node[]
  detailList?: { list?: Detail[] }
}
type ApiFail = { code?: number; msg?: string; data?: TracePayload }

const route = useRoute()
const keyword = ref('')
const entryType = ref('ACCOUNT')
const dateFrom = ref('')
const dateTo = ref('')
const exportFormat = ref<'XLSX' | 'PDF'>('XLSX')
const selectedEntry = ref<Entry | null>(null)
const entries = ref<Entry[]>([])
const searched = ref(false)
const nodes = ref<Node[]>([])
const details = ref<Detail[]>([])
const viewMode = ref<'SPLIT' | 'AGGREGATE'>('SPLIT')
const aggregateBy = ref<'PERSON' | 'ACCOUNT' | 'TEAM' | 'IP_GROUP'>('ACCOUNT')
const aggregates = ref<AggregateRow[]>([])
const crumbs = ref<Crumb[]>([])
const dataAsOf = ref('')
const queryCostMs = ref(0)
const queried = ref(false)
const timeoutDegraded = ref(false)
const error = ref('')
const exportNote = ref('')
const drawerOpen = ref(false)
const sessionDetail = ref<SessionDetail | null>(null)

const timeoutHint = computed(() =>
  timeoutDegraded.value ? '1181 穿透查询超时降级，请缩小日期范围' : '超时降级 1181',
)

const ENTRY_LABELS: Record<string, string> = {
  PERSON: '实名人',
  ACCOUNT: '账号',
  ASSET: '资产',
  SESSION: '场次',
  RESPONSIBLE: '责任人',
  IP_GROUP: 'IP组',
}

function entryTypeLabel(entryType: string) {
  return ENTRY_LABELS[entryType] || entryType
}

function personRoleLabel(role: string) {
  if (role === 'RESPONSIBLE') return '责任人'
  if (role === 'REALNAME') return '实名人'
  return role
}

function onEntryTypeChange() {
  selectedEntry.value = null
  entries.value = []
  searched.value = false
  crumbs.value = []
  aggregates.value = []
}

const assetChips = computed<RelationChip[]>(() => {
  const seen = new Set<string>()
  const chips: RelationChip[] = []
  for (const node of nodes.value) {
    if (node.nodeType !== 'ASSET' || !node.nodeId || node.nodeId === '0') continue
    if (seen.has(node.nodeId)) continue
    seen.add(node.nodeId)
    chips.push({
      entryType: 'ASSET',
      entryId: node.nodeId,
      entryLabel: node.nodeLabel,
      relation: '绑定资产',
    })
  }
  return chips
})

const ownerChips = computed<RelationChip[]>(() => {
  const seen = new Set<string>()
  const chips: RelationChip[] = []
  for (const row of details.value) {
    const id = String(row.responsibleUserId || '')
    if (!id || id === '0' || seen.has(id)) continue
    seen.add(id)
    chips.push({
      entryType: 'RESPONSIBLE',
      entryId: id,
      entryLabel: row.responsibleUserName || `责任人#${id}`,
      relation: '责任人',
    })
  }
  return chips
})

const ipChips = computed<RelationChip[]>(() => {
  const seen = new Set<string>()
  const chips: RelationChip[] = []
  for (const row of details.value) {
    const id = String(row.ipGroupId || '')
    if (!id || id === '0' || seen.has(id)) continue
    seen.add(id)
    chips.push({
      entryType: 'IP_GROUP',
      entryId: id,
      entryLabel: row.ipGroupName || `IP组#${id}`,
      relation: 'IP组',
    })
  }
  return chips
})

const relationChips = computed(() => [...assetChips.value, ...ownerChips.value, ...ipChips.value])

function relationName(nodeType: string) {
  if (nodeType === 'ACCOUNT') return '持有账号'
  if (nodeType === 'ASSET') return '绑定资产'
  if (nodeType === 'PERSON') return '实名人'
  if (nodeType === 'SESSION') return '参与场次'
  return nodeType
}

function rememberSource(entry: Entry) {
  crumbs.value = [{ label: `源头：${entry.entryLabel}`, entry }]
}

onMounted(() => {
  const preset = route.query.keyword
  if (typeof preset === 'string' && preset) keyword.value = preset
})

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function moneyOrDash(n: number | null | undefined) {
  return n == null ? '—' : '¥' + fmt(n)
}

function asApiFail(err: unknown): ApiFail | null {
  if (err && typeof err === 'object' && 'code' in err) return err as ApiFail
  return null
}

function dateRange(): string[] | undefined {
  if (dateFrom.value && dateTo.value) return [dateFrom.value, dateTo.value]
  return undefined
}

function applyResult(data: TracePayload | undefined, degraded: boolean) {
  nodes.value = degraded ? [] : data?.nodes || []
  details.value = degraded ? [] : data?.detailList?.list || []
  dataAsOf.value = data?.dataAsOf || ''
  queryCostMs.value = data?.queryCostMs ?? 0
  queried.value = true
  timeoutDegraded.value = degraded || queryCostMs.value > 3000
}

async function searchEntry() {
  error.value = ''
  searched.value = false
  selectedEntry.value = null
  crumbs.value = []
  try {
    const res = await http.get('/dc/trace/entry', {
      params: { keyword: keyword.value, entryType: entryType.value, limit: 8 },
    })
    entries.value = res.data.data || []
    searched.value = true
    if (entries.value.length === 1) pickEntry(entries.value[0])
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '网络错误'
  }
}

function drillEntry(chip: RelationChip) {
  const entry = { entryType: chip.entryType, entryId: chip.entryId, entryLabel: chip.entryLabel }
  entryType.value = chip.entryType
  selectedEntry.value = entry
  crumbs.value = [...crumbs.value, { label: `关联：${chip.relation} → ${chip.entryLabel}`, entry }]
  viewMode.value = 'SPLIT'
  drawerOpen.value = false
  runQuery()
}

function drillFromDrawer(entryType: string, entryId: string, entryLabel: string) {
  const relation = entryType === 'ASSET' ? '绑定资产' : entryType === 'IP_GROUP' ? 'IP组' : '责任人'
  drillEntry({ entryType, entryId, entryLabel, relation })
}

function drillAsset(row: Detail, index: number) {
  const assetId = (row.assetIds || [])[index]
  if (!assetId) return
  drillEntry({
    entryType: 'ASSET',
    entryId: String(assetId),
    entryLabel: (row.assetLabels || [])[index] || `资产#${assetId}`,
    relation: '绑定资产',
  })
}

function drillNode(n: Node) {
  drillEntry({
    entryType: n.nodeType,
    entryId: n.nodeId,
    entryLabel: n.nodeLabel,
    relation: relationName(n.nodeType),
  })
}

function truncateCrumb(index: number) {
  const crumb = crumbs.value[index]
  if (!crumb) return
  crumbs.value = crumbs.value.slice(0, index + 1)
  entryType.value = crumb.entry.entryType
  selectedEntry.value = crumb.entry
  viewMode.value = 'SPLIT'
  runQuery()
}

function pickEntry(e: Entry) {
  selectedEntry.value = e
  rememberSource(e)
  if (viewMode.value === 'AGGREGATE') loadAggregate()
  else runQuery()
}

function showAggregate() {
  viewMode.value = 'AGGREGATE'
  loadAggregate()
}

function onAggregateBy(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value === 'PERSON' || value === 'ACCOUNT' || value === 'TEAM' || value === 'IP_GROUP') {
    aggregateBy.value = value
  }
  loadAggregate()
}

function drillAggregate(row: AggregateRow) {
  if (aggregateBy.value === 'TEAM') return
  const entry = {
    entryType: aggregateBy.value,
    entryId: row.dimensionValue,
    entryLabel: row.dimensionLabel,
  }
  entryType.value = aggregateBy.value
  selectedEntry.value = entry
  rememberSource(entry)
  viewMode.value = 'SPLIT'
  runQuery()
}

async function loadAggregate() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  try {
    const res = await http.get('/dc/trace/aggregate', {
      params: {
        entryType: selectedEntry.value.entryType,
        entryId: selectedEntry.value.entryId,
        aggregateBy: aggregateBy.value,
        dateRange: dateFrom.value && dateTo.value ? `${dateFrom.value},${dateTo.value}` : undefined,
      },
    })
    aggregates.value = res.data.data || []
    timeoutDegraded.value = false
  } catch (err) {
    const fail = asApiFail(err)
    if (fail?.code === 1181) {
      aggregates.value = []
      timeoutDegraded.value = true
      return
    }
    error.value = fail?.msg || '聚合加载失败'
  }
}

async function onSubmit() {
  if (selectedEntry.value) {
    if (viewMode.value === 'AGGREGATE') await loadAggregate()
    else await runQuery()
    return
  }
  await searchEntry()
}

async function runQuery() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  exportNote.value = ''
  try {
    const res = await http.post('/dc/trace/query', {
      entryType: selectedEntry.value.entryType,
      entryId: selectedEntry.value.entryId,
      mode: 'DETAIL',
      pageNo: 1,
      pageSize: 10,
      dateRange: dateRange(),
    })
    applyResult(res.data.data, false)
  } catch (err) {
    const fail = asApiFail(err)
    if (fail?.code === 1181) {
      applyResult(fail.data, true)
      return
    }
    error.value = fail?.msg || '网络错误'
  }
}

async function openSession(sessionCode: string) {
  error.value = ''
  try {
    const res = await http.get(`/dc/trace/detail/${encodeURIComponent(sessionCode)}`, { timeout: 60_000 })
    sessionDetail.value = res.data.data
    drawerOpen.value = true
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '场次明细加载失败'
  }
}

async function exportReport() {
  if (!selectedEntry.value) {
    error.value = '请先选择穿透入口'
    return
  }
  error.value = ''
  exportNote.value = ''
  try {
    const res = await http.get('/dc/trace/export', {
      params: {
        entryType: selectedEntry.value.entryType,
        entryId: selectedEntry.value.entryId,
        format: exportFormat.value,
      },
    })
    const downloadUrl = res.data.data?.downloadUrl as string
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      error.value = `导出失败（${fileRes.status}）`
      return
    }
    const blob = await fileRes.blob()
    const ext = exportFormat.value === 'PDF' ? 'pdf' : 'xlsx'
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `dc_trace_report.${ext}`
    a.click()
    URL.revokeObjectURL(a.href)
    exportNote.value = `已导出 ${exportFormat.value}`
  } catch (err) {
    const fail = asApiFail(err)
    error.value = fail?.msg || '导出失败'
  }
}
</script>
