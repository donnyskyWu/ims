<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>实时预警</h1>
        <div class="sub">ALERT-002 · 记录筛选 · 推送回执（钉钉/短信为本地桩）</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/escalate">升级中心</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/stats">统计总览</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'live' }" @click="switchTab('live')">实时预警</div>
      <div class="tab" :class="{ on: tab === 'history' }" @click="switchTab('history')">处置记录</div>
      <div class="tab" :class="{ on: tab === 'dedup' }" @click="switchTab('dedup')">去重合并</div>
    </div>

    <div v-if="tab === 'live'" class="g2" style="margin: 12px 0">
      <div class="card stat" data-testid="alert-delivery-card">
        <span class="l">送达率</span>
        <div class="n" data-testid="alert-delivery-rate">{{ delivery ? `${delivery.deliveryRate}%` : '—' }}</div>
        <div class="d">
          已送达 {{ delivery?.totalDelivered ?? 0 }} / {{ delivery?.totalShould ?? 0 }} · 目标 &gt;{{ delivery?.target ?? 99 }}%
          · 钉钉/短信本地桩
        </div>
        <form class="qbar" style="margin-top: 8px" @submit.prevent="loadDelivery">
          <input v-model="deliveryFrom" data-testid="alert-delivery-from" type="date" />
          <input v-model="deliveryTo" data-testid="alert-delivery-to" type="date" />
          <button class="btn btn-pri btn-sm" type="submit" data-testid="alert-delivery-apply">刷新送达</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="alert-delivery-reset" @click="resetDelivery">
            清空
          </button>
        </form>
        <p v-if="deliveryError" class="hint" style="color: var(--red)" data-testid="alert-delivery-error">{{ deliveryError }}</p>
        <p v-if="delivery && delivery.totalShould === 0" class="hint" data-testid="alert-delivery-empty">
          当前范围内没有应送达预警，不记未达标
        </p>
        <p
          v-else-if="delivery && delivery.deliveryRate < (delivery.target || 99)"
          class="hint"
          style="color: var(--red)"
          data-testid="alert-delivery-short"
        >
          未达标（BR-111）
        </p>
        <div v-if="delivery?.failedAlerts?.length" data-testid="alert-delivery-failed">
          <div v-for="item in delivery.failedAlerts" :key="item.alertNo" class="hint">
            {{ item.alertNo }} · {{ channelName(item.failedChannel) }}失败 · 已自动补发 {{ item.retryCount }} 次（ALR-P-R2）
          </div>
        </div>
      </div>
      <div class="card" data-testid="alert-my-card">
        <div class="hd-row">
          <h3>我的预警</h3>
          <span class="csub">{{ myAlerts.length }} 条未响应</span>
        </div>
        <div v-if="!myAlerts.length" class="empty"><div class="et">暂无待响应预警</div></div>
        <div
          v-for="item in myAlerts"
          :key="item.alertNo"
          class="mg-i"
          style="cursor: pointer"
          data-testid="alert-my-item"
          @click="openDetail(item.alertNo)"
        >
          <div>
            <div class="mt">L{{ item.level }} {{ item.content }}</div>
            <div class="md">{{ item.alertNo }} · 未读</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab === 'history' && summary" class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">累计</span><div class="n">{{ summary.totalAlerts }}</div></div>
      <div class="card stat"><span class="l">已处置</span><div class="n">{{ summary.handledCount }}</div></div>
      <div class="card stat"><span class="l">待响应</span><div class="n">{{ summary.openCount }}</div></div>
      <div class="card stat">
        <span class="l">误报</span>
        <div class="n">{{ summary.falsePositiveCount }}</div>
        <div v-if="summary.falsePositiveCount >= 5" class="d" data-testid="alert-history-false-hint">
          连续误报 ≥5，建议复核阈值
        </div>
      </div>
    </div>

    <form v-if="tab !== 'dedup'" class="qbar" data-testid="alert-filter-bar" @submit.prevent="loadList">
      <input v-model="filters.ruleCode" data-testid="alert-filter-rule" placeholder="规则编码" style="width: 160px" />
      <select v-model="filters.level" data-testid="alert-filter-level" style="width: 110px">
        <option value="">全部级别</option>
        <option value="L1">L1</option>
        <option value="L2">L2</option>
        <option value="L3">L3</option>
      </select>
      <select v-model="filters.responseStatus" data-testid="alert-history-status" style="width: 120px">
        <option value="">全部处置</option>
        <option v-if="tab === 'live'" value="OPEN">待响应</option>
        <option value="CONFIRMED">已确认</option>
        <option value="RESOLVED">已解决</option>
        <option value="FALSE_ALARM">误报</option>
      </select>
      <select v-model="filters.pushStatus" data-testid="alert-filter-push" style="width: 120px">
        <option value="">全部推送</option>
        <option value="PENDING">待推送</option>
        <option value="DELIVERED">已送达</option>
        <option value="PARTIAL_FAILED">部分失败</option>
        <option value="FAILED">失败</option>
      </select>
      <input v-model="filters.dateFrom" data-testid="alert-filter-from" type="date" />
      <input v-model="filters.dateTo" data-testid="alert-filter-to" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="alert-filter-reset" @click="resetFilters">重置</button>
    </form>
    <p v-if="filterError" class="hint" style="color: var(--red)">{{ filterError }}</p>

    <div v-if="tab === 'dedup'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>策略编码</th>
              <th>名称</th>
              <th>窗口(分)</th>
              <th>合并键</th>
              <th>已合并</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!dedupRows.length">
              <td colspan="6"><div class="empty" data-testid="alert-dedup-empty"><div class="et">暂无去重策略</div></div></td>
            </tr>
            <tr v-for="row in dedupRows" v-else :key="row.id">
              <td class="mono">{{ row.policyCode }}</td>
              <td>{{ row.policyName }}</td>
              <td class="num">{{ row.windowMinutes }}</td>
              <td class="mono">{{ row.mergeKeyExpr }}</td>
              <td class="num">{{ row.mergedCount }}</td>
              <td>{{ row.enabled ? '启用' : '停用' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>预警编号</th>
              <th>规则</th>
              <th>级别</th>
              <th>内容</th>
              <th>推送回执</th>
              <th>状态</th>
              <th>时间</th>
              <th v-if="tab === 'live'">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="tab === 'live' ? 8 : 7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td :colspan="tab === 'live' ? 8 : 7">
                <div class="empty" data-testid="alert-list-empty">
                  <div class="et" data-testid="alert-tab-empty">{{ error || (tab === 'history' ? '暂无处置记录' : '暂无预警') }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.alertNo }}</td>
              <td>
                <div class="mono">{{ row.ruleCode || '—' }}</div>
                <div>{{ row.ruleName }}</div>
              </td>
              <td class="num">L{{ row.level }}</td>
              <td>{{ row.content }}</td>
              <td :data-testid="`alert-push-${row.alertNo}`" :title="channelTitle(row)">
                <div>{{ pushLabel(row.pushStatus) }}</div>
                <div class="d">{{ channelBrief(row) }}</div>
              </td>
              <td>{{ row.responseStatus }}</td>
              <td class="mono">{{ row.occurredAt?.slice(0, 16) || '—' }}</td>
              <td v-if="tab === 'live'">
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-detail-btn" @click="openDetail(row.alertNo)">
                  回执
                </button>
                <button
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="alert-receipt-btn"
                  @click="openReceipt(row.alertNo)"
                >
                  回执
                </button>
                <button
                  v-if="row.responseStatus === 'OPEN'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="alert-confirm-btn"
                  @click="respond(row.alertNo, 'CONFIRM')"
                >
                  确认
                </button>
                <button
                  v-if="row.responseStatus === 'OPEN' || row.responseStatus === 'CONFIRMED'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="alert-resolve-btn"
                  @click="respond(row.alertNo, row.responseStatus === 'OPEN' ? 'HANDLE' : 'RESOLVE')"
                >
                  处理
                </button>
                <button
                  v-if="row.responseStatus === 'OPEN' || row.responseStatus === 'CONFIRMED' || row.responseStatus === 'FALSE_ALARM'"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="alert-false-alarm-btn"
                  @click="openFalse(row.alertNo)"
                >
                  误报
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="toast" class="hint" style="margin-top: 10px">{{ toast }}</p>

    <ProtoDrawer :open="detailOpen" :title="detail ? `预警回执 · ${detail.alertNo}` : '预警回执'" width="640px" @close="closeDetail">
      <div v-if="detail" data-testid="alert-receipt-drawer">
        <p>{{ detail.content }}</p>
        <p class="hint" data-testid="alert-receipt-status">
          {{ detail.ruleCode }} {{ detail.ruleName }} · L{{ detail.level }} · {{ statusText(detail.responseStatus) }}
        </p>
        <p class="hint">钉钉、短信为本地回执桩，未实际外发。</p>
        <p v-if="detail.priorityNote" class="hint" data-testid="alert-receipt-priority">{{ detail.priorityNote }}</p>
        <div v-if="detail.receiptEmpty" class="empty" data-testid="alert-receipt-empty">
          <div class="et">暂无通道回执（待推送，钉钉/短信不外发）</div>
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>通道</th>
              <th>状态</th>
              <th>回执时间</th>
              <th>外发</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ch in detail.pushChannels" :key="ch.channel" data-testid="alert-receipt-row" :data-channel="ch.channel">
              <td>{{ ch.label || channelName(ch.channel) }}</td>
              <td>
                {{ ch.empty ? '未触发 ✗' : ch.success ? '✓' : '✗' }}
                <div v-if="ch.statusNote" class="hint" data-testid="alert-receipt-note">{{ ch.statusNote }}</div>
              </td>
              <td class="mono">{{ ch.receiptAt || '—' }}</td>
              <td>不外发</td>
            </tr>
          </tbody>
        </table>
        <p v-if="detail.retryNote || detail.retryCount" class="hint" style="color: var(--red)" data-testid="alert-receipt-retry">
          {{ detail.retryNote || '已自动补发 1 次（ALR-P-R2）' }}
        </p>
        <p v-if="detail.sourceJumpUrl" class="hint">
          <router-link data-testid="alert-receipt-source" :to="detail.sourceJumpUrl">查看来源</router-link>
        </p>
        <p v-else class="hint" data-testid="alert-receipt-source-empty">暂无来源单据</p>
        <button class="btn btn-sec btn-sm" type="button" data-testid="alert-receipt-close" @click="closeDetail">关闭</button>
      </div>
    </ProtoDrawer>
    <div v-if="falseTarget" class="modal-mask" @click.self="falseTarget = ''">
      <div class="card" style="width: 480px; padding: 20px" data-testid="alert-false-modal">
        <h3 style="margin: 0 0 8px">标记误报</h3>
        <p class="hint">误报反馈将用于规则阈值复核，连续误报 ≥5 次建议管理员复核阈值（ALR-S-R3）。</p>
        <label class="fld">误报原因（选填）</label>
        <input v-model="falseReason" class="fld-in" data-testid="alert-false-reason" />
        <label class="fld">处理说明（选填）</label>
        <input v-model="handleRemark" class="fld-in" data-testid="alert-false-remark" />
        <div style="margin-top: 12px; display: flex; gap: 8px">
          <button class="btn btn-pri btn-sm" type="button" data-testid="alert-false-submit" @click="submitFalse">
            确认误报
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="falseTarget = ''">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
type Channel = {
  channel: string
  label?: string
  success: boolean
  empty?: boolean
  receiptAt?: string
  statusNote?: string
}

type Row = {
  id: number
  alertNo: string
  ruleCode?: string
  ruleName: string
  level: number
  content: string
  pushStatus: string
  pushChannels?: Channel[]
  responseStatus: string
  occurredAt: string
}

type Detail = Row & {
  sourceJumpUrl?: string
  retryCount?: number
  receiptEmpty?: boolean
  priorityNote?: string
  retryNote?: string
}

type DedupRow = {
  id: number
  policyCode: string
  policyName: string
  windowMinutes: number
  mergeKeyExpr: string
  mergedCount: number
  enabled: boolean
}

type Delivery = {
  totalDelivered: number
  totalShould: number
  deliveryRate: number
  failedAlerts: { alertNo: string; failedChannel: string; retryCount: number }[]
  target: number
}

const route = useRoute()
const router = useRouter()
const tab = ref<'live' | 'history' | 'dedup'>('live')
const rows = ref<Row[]>([])
const dedupRows = ref<DedupRow[]>([])
const myAlerts = ref<Row[]>([])
const delivery = ref<Delivery | null>(null)
const detail = ref<Detail | null>(null)
const detailOpen = ref(false)
const loading = ref(false)
const error = ref('')
const filterError = ref('')
const summary = ref<{ totalAlerts: number; handledCount: number; openCount: number; falsePositiveCount: number } | null>(
  null
)
const filters = reactive({
  ruleCode: '',
  level: '',
  responseStatus: '',
  pushStatus: '',
  dateFrom: '',
  dateTo: '',
})
const toast = ref('')
const falseTarget = ref('')
const falseReason = ref('')
const handleRemark = ref('')

const deliveryFrom = ref('')
const deliveryTo = ref('')
const deliveryError = ref('')

const PUSH_LABELS: Record<string, string> = {
  PENDING: '待推送',
  DELIVERED: '已送达',
  PARTIAL_FAILED: '部分失败',
  FAILED: '失败',
}
const STATUS_TEXT: Record<string, string> = {
  OPEN: '未响应',
  CONFIRMED: '已确认',
  RESOLVED: '已处理',
  FALSE_ALARM: '误报',
}
const CHANNEL_NAMES: Record<string, string> = {
  WORKBENCH: '工作台',
  DINGTALK: '钉钉',
  SMS: '短信',
}

function pushLabel(status: string) {
  return PUSH_LABELS[status] || status || '—'
}

function statusText(status: string) {
  const label = STATUS_TEXT[status]
  return label ? `${label}（${status}）` : status || '—'
}

function channelName(channel: string) {
  return CHANNEL_NAMES[channel] || channel
}

function channelBrief(row: Row) {
  return (row.pushChannels || [])
    .map((ch) => {
      const name = channelName(ch.channel)
      if (ch.empty) return `${name}未触发`
      return `${name}${ch.success ? '✓' : '✗'}`
    })
    .join(' ')
}

function channelTitle(row: Row) {
  return (row.pushChannels || [])
    .map((ch) => {
      const mark = ch.empty ? '未触发' : ch.success ? '✓' : '✗'
      const note = ch.statusNote ? ` ${ch.statusNote}` : ''
      return `${channelName(ch.channel)} ${mark}${note} ${ch.receiptAt || ''}`.trim()
    })
    .join('\n')
}

function tabFromRoute() {
  const q = String(route.query.tab || '')
  if (q === 'history' || q === 'dedup') return q
  return 'live'
}

function switchTab(name: 'live' | 'history' | 'dedup') {
  tab.value = name
  router.replace({ path: '/ims/alert/live', query: name === 'live' ? {} : { tab: name } })
  if (name === 'dedup') loadDedup()
  else {
    if (name === 'history') {
      filters.responseStatus = ''
      loadSummary()
    }
    loadList()
  }
}

function resetFilters() {
  filters.ruleCode = ''
  filters.level = ''
  filters.responseStatus = ''
  filters.pushStatus = ''
  filters.dateFrom = ''
  filters.dateTo = ''
  filterError.value = ''
  if (route.query.level) {
    const nextQuery = tab.value === 'live' ? {} : { tab: tab.value }
    router.replace({ path: '/ims/alert/live', query: nextQuery })
  }
  loadList()
}

async function loadSummary() {
  const res = await http.get('/alert/history/summary')
  if (res.data.code === 0) summary.value = res.data.data
}

async function loadDelivery() {
  deliveryError.value = ''
  const params: Record<string, string> = {}
  if (deliveryFrom.value || deliveryTo.value) {
    if (!deliveryFrom.value || !deliveryTo.value) {
      deliveryError.value = '请同时填写送达率起止日期'
      return
    }
    params.dateRange = `${deliveryFrom.value},${deliveryTo.value}`
  }
  try {
    const stats = await http.get('/alert/check/delivery-stats', { params })
    delivery.value = stats.data.data
  } catch (err) {
    deliveryError.value = errorMessage(err)
  }
}

function resetDelivery() {
  deliveryFrom.value = ''
  deliveryTo.value = ''
  loadDelivery()
}

async function loadInbox() {
  const mine = await http.get('/alert/check/my-alerts')
  if (mine.data.code === 0) myAlerts.value = mine.data.data || []
  await loadDelivery()
}

async function loadDedup() {
  loading.value = true
  try {
    const res = await http.get('/alert/dedup/list', { params: { pageNo: 1, pageSize: 20 } })
    if (res.data.code === 0) dedupRows.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  filterError.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.ruleCode.trim()) params.ruleCode = filters.ruleCode.trim()
    if (filters.level) params.level = filters.level
    if (filters.responseStatus) params.responseStatus = filters.responseStatus
    if (filters.pushStatus) params.pushStatus = filters.pushStatus
    if (filters.dateFrom || filters.dateTo) {
      if (!filters.dateFrom || !filters.dateTo) {
        filterError.value = '请同时填写起止日期'
        rows.value = []
        return
      }
      params.dateRange = `${filters.dateFrom},${filters.dateTo}`
    }
    const res = await http.get('/alert/check/records', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    let list: Row[] = res.data.data?.list || []
    if (tab.value === 'history' && !filters.responseStatus) {
      list = list.filter((r) => r.responseStatus !== 'OPEN')
    }
    rows.value = list
    if (tab.value === 'live') {
      try {
        await loadInbox()
      } catch {
        /* 列表已返回；收件箱失败不改筛选结果 */
      }
    }
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function closeDetail() {
  detailOpen.value = false
  detail.value = null
}

async function openDetail(alertNo: string) {
  detail.value = null
  detailOpen.value = true
  toast.value = ''
  try {
    const res = await http.get(`/alert/check/${alertNo}`)
    if (res.data.code !== 0) {
      toast.value = res.data.msg || '回执加载失败'
      return
    }
    detail.value = res.data.data
  } catch (err) {
    toast.value = errorMessage(err)
  }
}

function closeReceipt() {
  closeDetail()
}

async function openReceipt(alertNo: string) {
  await openDetail(alertNo)
}

function openFalse(alertNo: string) {
  falseTarget.value = alertNo
  falseReason.value = ''
  handleRemark.value = ''
}

async function submitFalse() {
  const alertNo = falseTarget.value
  if (!alertNo) return
  falseTarget.value = ''
  await respond(alertNo, 'FALSE_ALARM', {
    falseAlarmReason: falseReason.value.trim(),
    handleRemark: handleRemark.value.trim(),
  })
}

async function respond(
  alertNo: string,
  action: string,
  extra?: { falseAlarmReason?: string; handleRemark?: string },
) {
  toast.value = ''
  try {
    const payload: Record<string, string> = { action }
    if (extra?.falseAlarmReason) payload.falseAlarmReason = extra.falseAlarmReason
    if (extra?.handleRemark) payload.handleRemark = extra.handleRemark
    const res = await http.put(`/alert/check/${alertNo}/respond`, payload)
    if (res.data.code !== 0) {
      toast.value = res.data.msg || '处置失败'
      return
    }
    const status = res.data.data?.responseStatus || ''
    const labels: Record<string, string> = {
      CONFIRMED: '已确认',
      RESOLVED: '已解决',
      FALSE_ALARM: '已标记误报',
    }
    toast.value = `处置成功：${labels[status] || status}（${alertNo}）`
    if (res.data.data?.escalationStopped) {
      toast.value += ' · 响应成功，后续升级已停止'
    }
    if (tab.value === 'history') await loadSummary()
    await loadList()
  } catch (error) {
    const body = error as { msg?: string }
    toast.value = body?.msg || errorMessage(error)
  }
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(() => {
  tab.value = tabFromRoute()
  const level = String(route.query.level || '')
  if (level === 'L1' || level === 'L2' || level === 'L3') filters.level = level
  if (tab.value === 'dedup') loadDedup()
  else {
    if (tab.value === 'history') loadSummary()
    loadList()
  }
})
</script>
