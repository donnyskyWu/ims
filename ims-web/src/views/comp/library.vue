<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品库</h1>
        <div class="sub">V3 COMP-003 · BR-202 审核入库 · /ims/comp/library · 18a COMP</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/comp/work')">竞品作品监测</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/comp/account')">竞品账号监测</button>
        <button
          class="btn btn-sec btn-sm"
          type="button"
          data-testid="comp-export-compare"
          :disabled="!basket.length"
          @click="exportCompare"
        >
          导出对比{{ basket.length ? `（${basket.length}）` : '' }}
        </button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="comp-add" @click="openCreate">新增竞品</button>
      </div>
    </div>
    <p v-if="note" class="hint" data-testid="comp-lib-note">{{ note }}</p>
    <p v-else class="hint" style="margin-bottom: 8px">
      提交后进入两级审核：R8 初审 → R4 终审。终审通过后「已入库」并自动订阅监控。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.compName" placeholder="竞品对象名称" style="width: 140px" />
      <select v-model="filters.platform" style="width: 120px">
        <option value="">全部平台</option>
        <option v-for="item in platforms" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div v-if="loading" class="empty" style="margin-top: 24px"><div class="et">加载中</div></div>
    <div v-else-if="error" class="empty" style="margin-top: 24px"><div class="et">{{ error }}</div></div>
    <div v-else-if="!cards.length" class="empty" style="margin-top: 24px"><div class="et">暂无竞品档案</div></div>
    <div v-else class="comp-grid">
      <button
        v-for="row in cards"
        :key="row.key"
        class="card hov comp-card"
        type="button"
        :data-testid="'comp-card-' + row.key"
        @click="openCard(row)"
      >
        <div class="rowline" style="margin-bottom: 10px">
          <span class="av" style="background: linear-gradient(135deg, #0071e3, #5ac8fa)">{{ row.avatarInitial }}</span>
          <div style="min-width: 0; flex: 1">
            <b style="font-size: 14px; display: block; line-height: 1.3">{{ row.compName }}</b>
            <span style="font-size: 11.5px; color: var(--text2)">{{ platformLabel(row.platform) }} · 竞品</span>
          </div>
          <span class="tag" :style="statusStyle(row.auditStatus)" data-testid="comp-audit-status">{{ row.auditStatusLabel }}</span>
        </div>
        <div class="kv" style="grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 0">
          <div>
            <div class="k">粉丝数</div>
            <div class="v" style="font-size: 14px">{{ row.stored ? formatFans(row.followerCount) : '—' }}</div>
          </div>
          <div>
            <div class="k">近30天作品</div>
            <div class="v" style="font-size: 14px">{{ row.stored ? row.works30d : '—' }}</div>
          </div>
          <div>
            <div class="k">互动率</div>
            <div class="v" style="font-size: 14px; color: var(--blue)">{{ row.stored ? row.engagementRate + '%' : '—' }}</div>
          </div>
        </div>
        <div class="rowline" style="margin-top: 12px; justify-content: space-between">
          <span style="font-size: 11.5px; color: var(--text2)">{{ row.foot }}</span>
          <span style="font-size: 11px; color: var(--text2)">{{ row.assetNo || row.analysisNo }}</span>
        </div>
      </button>
    </div>

    <ProtoDrawer :open="showCreate" title="新增竞品" width="720px" @close="showCreate = false">
      <p class="hint">仅可采集公开数据（BR-202）。提交后状态为「待初审」，由 R8 初审、R4 终审。</p>
      <div v-if="mergeHint" class="hint" data-testid="comp-merge-preview" style="background: rgba(255, 149, 0, 0.08)">
        {{ mergeHint }}
      </div>
      <form class="comp-form" @submit.prevent="submitCreate">
        <div class="fld">
          <label>竞品对象名称 <span class="req">*</span></label>
          <input v-model="createForm.compName" data-testid="comp-name" placeholder="如：TC竞品库A" @blur="previewMerge" />
          <div v-if="fieldErrors.compName" class="ferr">{{ fieldErrors.compName }}</div>
        </div>
        <div class="fld">
          <label>平台 <span class="req">*</span></label>
          <select v-model="createForm.platform" data-testid="comp-platform">
            <option value="">请选择</option>
            <option v-for="item in platforms" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <div v-if="fieldErrors.platform" class="ferr">{{ fieldErrors.platform }}</div>
        </div>
        <div class="fld">
          <label>主页链接</label>
          <input v-model="createForm.homepageUrl" data-testid="comp-homepage" placeholder="https://…（选填）" />
        </div>
        <div class="fld">
          <label>分析周期 <span class="req">*</span></label>
          <input v-model="createForm.periodMonth" data-testid="comp-period" type="month" />
          <div v-if="fieldErrors.periodMonth" class="ferr">{{ fieldErrors.periodMonth }}</div>
        </div>
        <div class="fld">
          <label>数据来源 <span class="req">*</span></label>
          <textarea v-model="createForm.dataSource" data-testid="comp-source" rows="2" placeholder="仅可采集公开数据，来源须可追溯" />
          <div v-if="fieldErrors.dataSource" class="ferr">{{ fieldErrors.dataSource }}</div>
        </div>
        <div class="dsec">维度字段</div>
        <div class="fld" v-for="dim in dimensions" :key="dim.key">
          <label>{{ dim.label }}</label>
          <input v-model="createForm.dimensionData[dim.key]" :data-testid="'comp-dim-' + dim.key" />
        </div>
        <div class="fld">
          <label>结论与可借鉴点 <span class="req">*</span></label>
          <textarea v-model="createForm.conclusion" data-testid="comp-conclusion" rows="3" />
          <div v-if="fieldErrors.conclusion" class="ferr">{{ fieldErrors.conclusion }}</div>
        </div>
        <div v-if="formError" class="ferr" data-testid="comp-form-error">{{ formError }}</div>
      </form>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="showCreate = false">取消</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="comp-submit" :disabled="creating" @click="submitCreate">
          提交审核
        </button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="!!active" :title="active ? '竞品 · ' + active.compName : '竞品'" width="720px" @close="active = null">
      <template v-if="active">
        <div class="rowline" style="margin-bottom: 12px">
          <b>{{ active.compName }}</b>
          <span class="tag" :style="statusStyle(active.auditStatus)">{{ active.auditStatusLabel }}</span>
          <span style="font-size: 12px; color: var(--text2)">{{ platformLabel(active.platform) }} · 竞品账号</span>
          <span v-if="active.monitorSubscribed" class="tag" data-testid="comp-monitor-chip">已订阅监控</span>
        </div>
        <div v-if="active.stored" class="kv" data-testid="comp-detail-base">
          <div><div class="k">粉丝数</div><div class="v">{{ formatFans(active.followerCount) }}</div></div>
          <div><div class="k">近30天作品数</div><div class="v">{{ active.works30d }}</div></div>
          <div><div class="k">更新频率</div><div class="v">{{ active.updateFrequency ?? '—' }} 条/天</div></div>
          <div><div class="k">互动率</div><div class="v">{{ active.engagementRate }}%</div></div>
        </div>
        <div v-if="active.stored" class="dsec">近30天互动量趋势</div>
        <div v-if="active.stored" class="trend" data-testid="comp-trend">
          <span v-for="point in active.interactionTrend || []" :key="point.date" class="trend-bar" :title="point.date">
            <i :style="{ height: Math.max(8, point.value * 8) + 'px' }"></i>
          </span>
          <em>{{ active.trendNote || '示意' }}</em>
        </div>
        <div v-if="active.stored" class="dsec">代表作品 Top3</div>
        <ul v-if="active.stored" class="timeline" data-testid="comp-top-works">
          <li v-if="!(active.topWorks || []).length">暂无代表作品</li>
          <li v-for="work in active.topWorks || []" :key="work.title">
            {{ work.title }} · 播放 {{ formatFans(work.playCount) }} · 点赞 {{ formatFans(work.likeCount) }}
          </li>
        </ul>
        <div v-if="active.rejectReason" class="hint" data-testid="comp-reject-reason" style="color: var(--red)">
          驳回原因：{{ active.rejectReason }}
        </div>
        <div class="kv">
          <div><div class="k">竞品对象名称</div><div class="v">{{ active.compName }}</div></div>
          <div><div class="k">分析周期</div><div class="v">{{ active.periodMonth || '—' }}</div></div>
          <div><div class="k">数据来源</div><div class="v">{{ active.dataSource || '—' }}</div></div>
          <div><div class="k">结论</div><div class="v">{{ active.conclusion || '—' }}</div></div>
          <div><div class="k">单号</div><div class="v">{{ active.analysisNo || active.assetNo }}</div></div>
        </div>
        <div v-if="active.auditRounds?.length" class="dsec">审核记录</div>
        <ul v-if="active.auditRounds?.length" class="timeline" data-testid="comp-timeline">
          <li v-for="item in active.auditRounds" :key="item.round">
            第 {{ item.round }} 轮 · {{ roundTitle(item) }} · {{ item.auditorName }} · {{ item.auditedAt }}
            <span v-if="item.rejectReason"> · {{ item.rejectReason }}</span>
          </li>
        </ul>
        <div v-if="showRejectBox" class="fld" style="margin-top: 12px">
          <label>驳回原因 <span class="req">*</span></label>
          <textarea v-model="rejectReason" data-testid="comp-reject-input" rows="3" placeholder="请填写退回原因" />
          <div v-if="rejectError" class="ferr">{{ rejectError }}</div>
        </div>
      </template>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="active = null">关闭</button>
        <button
          v-if="active?.stored"
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="comp-add-compare"
          @click="addCompare"
        >
          加入对比
        </button>
        <button
          v-if="canResubmit"
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="comp-resubmit"
          @click="resubmit"
        >
          重新提交
        </button>
        <template v-if="canAudit">
          <button class="btn btn-sec btn-sm" type="button" data-testid="comp-reject" @click="beginReject">驳回</button>
          <button
            v-if="showRejectBox"
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="comp-reject-confirm"
            @click="confirmReject"
          >
            确认驳回
          </button>
          <button
            v-if="auditLevel === 'FIRST'"
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="comp-first-pass"
            @click="passAudit('FIRST')"
          >
            初审通过
          </button>
          <button
            v-if="auditLevel === 'FINAL'"
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="comp-final-pass"
            @click="passAudit('FINAL')"
          >
            终审通过
          </button>
        </template>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const router = useRouter()
const platforms = [
  { value: 'DOUYIN', label: '抖音' },
  { value: 'KUAISHOU', label: '快手' },
  { value: 'WECHAT_OFFICIAL', label: '公众号' },
  { value: 'WECHAT_CHANNELS', label: '视频号' },
  { value: 'XIAOHONGSHU', label: '小红书' },
]
type DimensionKey = 'sales' | 'gmv' | 'priceBand' | 'contentStrategy' | 'adStrategy'
const dimensions: { key: DimensionKey; label: string }[] = [
  { key: 'sales', label: '销售' },
  { key: 'gmv', label: 'GMV' },
  { key: 'priceBand', label: '价格带' },
  { key: 'contentStrategy', label: '内容策略' },
  { key: 'adStrategy', label: '投放策略' },
]

type Round = {
  round: number
  auditLevel: string
  conclusion: string
  rejectReason?: string
  auditorName: string
  auditedAt: string
}
type Card = {
  key: string
  cardKind: 'asset' | 'analysis'
  compName: string
  platform: string
  avatarInitial: string
  followerCount: number
  works30d: number
  engagementRate: number
  auditStatus: string
  auditStatusLabel: string
  assetNo?: string
  analysisNo?: string
  stored: boolean
  foot: string
  rejectReason?: string
  periodMonth?: string
  dataSource?: string
  conclusion?: string
  auditRounds?: Round[]
  submitterUserId?: number
  homepageUrl?: string
  dimensionData?: Record<string, string>
  monitorSubscribed?: boolean
  updateFrequency?: number
  trendNote?: string
  interactionTrend?: { date: string; value: number }[]
  topWorks?: { title: string; playCount: number; likeCount: number }[]
}
type Actor = {
  userId: number
  canSubmit: boolean
  canFirstAudit: boolean
  canFinalAudit: boolean
}

const rows = ref<Card[]>([])
const analyses = ref<Card[]>([])
const loading = ref(false)
const error = ref('')
const note = ref('')
const showCreate = ref(false)
const creating = ref(false)
const mergeHint = ref('')
const formError = ref('')
const fieldErrors = reactive<Record<string, string>>({})
const filters = reactive({ compName: '', platform: '' })
const actor = ref<Actor>({ userId: 0, canSubmit: true, canFirstAudit: false, canFinalAudit: false })
const active = ref<Card | null>(null)
const basket = ref<{ assetNo: string; compName: string }[]>([])
const showRejectBox = ref(false)
const rejectReason = ref('')

function roundTitle(item: Round) {
  if (item.auditLevel === 'RESUBMIT' || item.conclusion === 'RESUBMITTED') return '重新提交'
  const level = item.auditLevel === 'FINAL' ? '终审（R4）' : '初审（R8）'
  const result = item.conclusion === 'REJECTED' ? '退回' : '通过'
  return `${level} · ${result}`
}
const rejectError = ref('')

const createForm = reactive({
  compName: '',
  platform: '',
  homepageUrl: '',
  periodMonth: currentMonth(),
  dataSource: '',
  conclusion: '',
  dimensionData: emptyDimensions(),
})

const cards = computed(() => {
  const pending = analyses.value.filter((item) => item.auditStatus !== 'STORED')
  const names = new Set(pending.map((item) => item.compName))
  return [...pending, ...rows.value.filter((item) => !names.has(item.compName))]
})

const auditLevel = computed(() => {
  if (!active.value) return ''
  if (active.value.auditStatus === 'PENDING_FIRST') return 'FIRST'
  if (active.value.auditStatus === 'PENDING_FINAL') return 'FINAL'
  return ''
})

const canAudit = computed(() => {
  if (!active.value || active.value.cardKind !== 'analysis') return false
  if (active.value.submitterUserId && actor.value.userId && active.value.submitterUserId === actor.value.userId) {
    return false
  }
  if (auditLevel.value === 'FIRST') return actor.value.canFirstAudit
  if (auditLevel.value === 'FINAL') return actor.value.canFinalAudit
  return false
})

const canResubmit = computed(() => {
  if (!active.value || active.value.auditStatus !== 'REJECTED') return false
  return !active.value.submitterUserId || active.value.submitterUserId === actor.value.userId
})

function currentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function emptyDimensions(): Record<DimensionKey, string> {
  return { sales: '', gmv: '', priceBand: '', contentStrategy: '', adStrategy: '' }
}

function platformLabel(code: string) {
  return platforms.find((item) => item.value === code)?.label || code || '—'
}

function go(path: string) {
  router.push(path)
}

function formatFans(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(n >= 1_000_000 ? 0 : 1)} 万`
  return String(n ?? 0)
}

function statusStyle(status: string) {
  if (status === 'STORED' || status === 'APPROVED' || status === 'TRACKING') {
    return 'background: rgba(52, 199, 89, 0.12); color: #1e8e3e'
  }
  if (status === 'REJECTED') return 'background: rgba(255, 59, 48, 0.12); color: #d70015'
  if (status === 'PENDING_FINAL') return 'background: rgba(255, 149, 0, 0.16); color: #c46a00'
  return 'background: rgba(0, 113, 227, 0.12); color: #0071e3'
}

function apiMessage(error: unknown, fallback: string) {
  if (error && typeof error === 'object' && 'msg' in error) {
    const msg = (error as { msg?: string }).msg
    if (msg) return msg
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function assetCard(row: Record<string, unknown>): Card {
  const status = String(row.auditStatus || 'STORED')
  return {
    key: String(row.assetNo || row.id),
    cardKind: 'asset',
    compName: String(row.compName || ''),
    platform: String(row.platform || ''),
    avatarInitial: String(row.avatarInitial || (row.compName || '?')).slice(0, 1),
    followerCount: Number(row.followerCount || 0),
    works30d: Number(row.works30d || 0),
    engagementRate: Number(row.engagementRate || 0),
    auditStatus: status,
    auditStatusLabel: String(row.auditStatusLabel || '已入库'),
    assetNo: String(row.assetNo || ''),
    stored: true,
    foot: row.monitorSubscribed ? '已订阅监控' : '代表作品已收录',
    homepageUrl: String(row.homepageUrl || ''),
    monitorSubscribed: Boolean(row.monitorSubscribed),
    updateFrequency: Number(row.updateFrequency || 0),
    trendNote: String(row.trendNote || ''),
    interactionTrend: (row.interactionTrend as { date: string; value: number }[]) || [],
    topWorks: (row.topWorks as { title: string; playCount: number; likeCount: number }[]) || [],
  }
}

function analysisCard(row: Record<string, unknown>): Card {
  const status = String(row.auditStatus || '')
  return {
    key: String(row.analysisNo || row.id),
    cardKind: 'analysis',
    compName: String(row.compName || ''),
    platform: String(row.platform || ''),
    avatarInitial: String(row.compName || '?').slice(0, 1),
    followerCount: 0,
    works30d: 0,
    engagementRate: 0,
    auditStatus: status,
    auditStatusLabel: String(row.auditStatusLabel || ''),
    analysisNo: String(row.analysisNo || ''),
    assetNo: String(row.assetNo || ''),
    stored: status === 'STORED',
    foot: String(row.auditStatusLabel || ''),
    rejectReason: String(row.rejectReason || ''),
    periodMonth: String(row.periodMonth || ''),
    dataSource: String(row.dataSource || ''),
    conclusion: String(row.conclusion || ''),
    auditRounds: (row.auditRounds as Round[]) || [],
    submitterUserId: Number(row.submitterUserId || 0),
    homepageUrl: String(row.homepageUrl || ''),
    dimensionData: (row.dimensionData as Record<string, string>) || {},
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 24 }
    if (filters.compName) params.compName = filters.compName
    if (filters.platform) params.platform = filters.platform
    const [assetRes, analysisRes] = await Promise.all([
      http.get('/comp/asset/list', { params }),
      http.get('/comp/analysis/list', { params: { pageNo: 1, pageSize: 50 } }),
    ])
    rows.value = (assetRes.data.data.list || []).map(assetCard)
    const data = analysisRes.data.data || {}
    analyses.value = (data.list || []).map(analysisCard)
    if (data.actor) actor.value = data.actor
  } catch (e: unknown) {
    error.value = apiMessage(e, '网络错误')
    rows.value = []
    analyses.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.compName = ''
  filters.platform = ''
  loadList()
}

function resetCreateForm() {
  createForm.compName = ''
  createForm.platform = ''
  createForm.homepageUrl = ''
  createForm.periodMonth = currentMonth()
  createForm.dataSource = ''
  createForm.conclusion = ''
  createForm.dimensionData = emptyDimensions()
  mergeHint.value = ''
  formError.value = ''
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
}

function openCreate() {
  resetCreateForm()
  showCreate.value = true
}

function validateCreate() {
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
  formError.value = ''
  if (!createForm.compName.trim()) fieldErrors.compName = '必填项，请填写'
  if (!createForm.platform) fieldErrors.platform = '必填项，请填写'
  if (!createForm.periodMonth) fieldErrors.periodMonth = '必填项，请填写'
  if (!createForm.dataSource.trim()) fieldErrors.dataSource = '1171 数据来源必填（仅可采集公开数据，BR-202）'
  if (!createForm.conclusion.trim()) fieldErrors.conclusion = '必填项，请填写'
  return Object.keys(fieldErrors).length === 0
}

async function previewMerge() {
  const name = createForm.compName.trim()
  if (!name) {
    mergeHint.value = ''
    return
  }
  try {
    const res = await http.get('/comp/audit/merge-preview', { params: { compName: name } })
    const data = res.data.data
    if (data?.matched) {
      mergeHint.value = `检测到既有档案 ${data.compNameStd}（${data.assetNo}，当前版本 v${data.latestVersion}，匹配方式 ${data.matchedBy}）。提交通过终审后将归并至该档案。`
    } else {
      mergeHint.value = ''
    }
  } catch {
    mergeHint.value = ''
  }
}

async function submitCreate() {
  if (!validateCreate()) return
  creating.value = true
  formError.value = ''
  try {
    const res = await http.post('/comp/analysis', {
      compName: createForm.compName.trim(),
      platform: createForm.platform,
      homepageUrl: createForm.homepageUrl.trim(),
      periodMonth: createForm.periodMonth,
      dataSource: createForm.dataSource.trim(),
      dimensionData: { ...createForm.dimensionData },
      conclusion: createForm.conclusion.trim(),
    })
    const data = res.data.data || {}
    const compName = String(data.compName || '')
    const analysisNo = String(data.analysisNo || '')
    const auditStatusLabel = String(data.auditStatusLabel || '待初审')
    resetCreateForm()
    showCreate.value = false
    note.value = `已提交审核：${compName}（${analysisNo}），状态「${auditStatusLabel}」`
    await loadList()
  } catch (e: unknown) {
    if (showCreate.value) formError.value = apiMessage(e, '提交失败')
    else note.value = note.value || apiMessage(e, '已提交，列表刷新失败')
  } finally {
    creating.value = false
  }
}

async function openCard(row: Card) {
  showRejectBox.value = false
  rejectReason.value = ''
  rejectError.value = ''
  if (row.cardKind === 'asset' && row.assetNo) {
    try {
      const res = await http.get(`/comp/asset/${row.assetNo}`)
      active.value = assetCard(res.data.data)
      return
    } catch (e: unknown) {
      note.value = apiMessage(e, '加载详情失败')
    }
  }
  if (row.cardKind === 'analysis' && row.analysisNo) {
    try {
      const res = await http.get(`/comp/analysis/${row.analysisNo}`)
      const data = res.data.data
      if (data.actor) actor.value = { ...actor.value, ...data.actor }
      active.value = analysisCard(data)
      return
    } catch (e: unknown) {
      note.value = apiMessage(e, '加载详情失败')
    }
  }
  active.value = row
}

function addCompare() {
  if (!active.value?.stored || !active.value.assetNo) {
    note.value = '未入库的竞品不能加入对比'
    return
  }
  if (basket.value.some((item) => item.assetNo === active.value?.assetNo)) {
    note.value = `已在对比篮中，当前 ${basket.value.length} 个`
    return
  }
  if (basket.value.length >= 5) {
    note.value = '对比篮最多 5 个'
    return
  }
  basket.value.push({ assetNo: active.value.assetNo, compName: active.value.compName })
  note.value = `已加入对比，当前对比篮 ${basket.value.length} 个`
}

function csvCell(value: unknown) {
  const text = value == null ? '' : String(value)
  return `"${text.replaceAll('"', '""')}"`
}

async function exportCompare() {
  if (!basket.value.length) return
  try {
    const res = await http.get('/comp/asset/compare', {
      params: { assetNos: basket.value.map((item) => item.assetNo).join(',') },
    })
    const data = res.data.data
    const names = (data.conclusions || []).map((item: { compNameStd: string }) => item.compNameStd)
    const lines = [['维度', ...names].map(csvCell).join(',')]
    for (const row of data.dimensionMatrix || []) {
      lines.push([row.dimensionKey, ...(row.values || [])].map(csvCell).join(','))
    }
    const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'comp_compare.csv'
    link.click()
    URL.revokeObjectURL(link.href)
    note.value = `已导出对比 ${data.assetNos.length} 个竞品`
  } catch (e: unknown) {
    note.value = apiMessage(e, '导出对比失败')
  }
}

async function passAudit(level: 'FIRST' | 'FINAL') {
  if (!active.value?.analysisNo) return
  try {
    const res = await http.put(`/comp/audit/${active.value.analysisNo}`, {
      auditLevel: level,
      conclusion: 'STORED',
    })
    const data = res.data.data
    note.value =
      data.nextAction === 'MERGE_STORED'
        ? `终审通过，已入库 ${data.mergeInfo?.assetNo || ''}，已订阅监控（次日生效）`
        : `初审通过，状态「${data.auditStatusLabel}」`
    active.value = null
    await loadList()
  } catch (e: unknown) {
    note.value = apiMessage(e, '审核失败')
  }
}

function beginReject() {
  showRejectBox.value = true
  rejectError.value = ''
}

async function confirmReject() {
  if (!active.value?.analysisNo || !auditLevel.value) return
  if (!rejectReason.value.trim()) {
    rejectError.value = '驳回原因必填'
    return
  }
  try {
    const res = await http.put(`/comp/audit/${active.value.analysisNo}`, {
      auditLevel: auditLevel.value,
      conclusion: 'REJECTED',
      rejectReason: rejectReason.value.trim(),
    })
    note.value = `已退回：${res.data.data.auditStatusLabel}。${rejectReason.value.trim()}`
    active.value = null
    await loadList()
  } catch (e: unknown) {
    rejectError.value = apiMessage(e, '驳回失败')
  }
}

async function resubmit() {
  if (!active.value?.analysisNo) return
  try {
    const res = await http.put(`/comp/analysis/${active.value.analysisNo}`, {
      compName: active.value.compName,
      platform: active.value.platform,
      homepageUrl: active.value.homepageUrl || '',
      periodMonth: active.value.periodMonth,
      dataSource: active.value.dataSource,
      dimensionData: active.value.dimensionData || {},
      conclusion: active.value.conclusion,
    })
    note.value = `已重新提交，状态「${res.data.data.auditStatusLabel}」`
    active.value = null
    await loadList()
  } catch (e: unknown) {
    note.value = apiMessage(e, '重新提交失败')
  }
}

onMounted(loadList)
</script>

<style scoped>
.comp-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 12px;
}
.comp-card {
  text-align: left;
  width: 100%;
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.comp-form .fld {
  margin-bottom: 10px;
}
.req {
  color: var(--red);
}
.timeline {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  line-height: 1.7;
}
.trend {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  min-height: 48px;
}
.trend-bar i {
  display: block;
  width: 10px;
  background: var(--blue);
  border-radius: 3px 3px 0 0;
}
.trend em {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text2);
  font-style: normal;
}
@media (max-width: 1200px) {
  .comp-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
