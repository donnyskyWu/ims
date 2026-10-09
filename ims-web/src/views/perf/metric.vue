<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>指标配置</h1>
        <div class="sub">PERF-001 · /admin-api/ims/perf/metric · 岗位指标集权重合计须为 100%</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="metric-create-open" @click="openCreate">
          创建指标
        </button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 12px">
      竞品分析提交率（COMPETE_SUBMIT_RATE）在 V2 锁定禁用。岗位指标集保存时服务端校验权重合计。
    </p>
    <div
      data-testid="metric-coverage"
      :data-level="coverageLevel"
      style="margin-bottom: 12px; padding: 12px 14px; border-radius: 10px"
      :style="coverageStyle"
    >
      <div style="font-weight: 600">自动取数覆盖率</div>
      <div data-testid="metric-coverage-rate" style="font-size: 22px; margin-top: 4px">{{ coverageRateText }}</div>
      <div data-testid="metric-coverage-count" class="hint">
        自动 {{ coverage.autoMetricCount }} / 启用 {{ coverage.enabledMetricCount }}
      </div>
      <div data-testid="metric-coverage-flag">{{ coverageFlag }}</div>
      <button
        v-if="coverage.manualMetrics.length"
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="metric-coverage-manual"
        style="margin-top: 8px"
        @click="showManual = !showManual"
      >
        未自动取数清单
      </button>
      <ul v-if="showManual" data-testid="metric-coverage-manual-list" style="margin: 8px 0 0; padding-left: 18px">
        <li v-for="item in coverage.manualMetrics" :key="item.metricCode">
          {{ item.metricCode }} {{ item.metricName }}
        </li>
      </ul>
      <p v-if="coverageError" data-testid="metric-coverage-error" class="hint" style="color: var(--red)">
        {{ coverageError }}
      </p>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.metricName" placeholder="指标名称" style="width: 160px" />
      <select v-model="filters.dataSource" style="width: 120px">
        <option value="">全部来源</option>
        <option value="AUTO">系统自动</option>
        <option value="MANUAL">手工录入</option>
        <option value="EXAM">考试成绩</option>
      </select>
      <select v-model="filters.status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">禁用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>指标名称</th>
              <th>取数来源</th>
              <th>取数映射</th>
              <th>权重</th>
              <th>得分规则</th>
              <th>状态</th>
              <th>版本</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9"><div class="empty"><div class="et">{{ error || '暂无指标' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue)">{{ row.metricCode }}</td>
              <td style="font-weight: 500">{{ row.metricName }}</td>
              <td>
                <span class="tag" :style="sourceStyle(row.dataSource)">
                  <span class="dot"></span>{{ sourceLabel(row.dataSource) }}
                </span>
              </td>
              <td>{{ mappingText(row) }}</td>
              <td class="num">{{ row.metricCode === COMPETE_CODE ? '—' : `${formatWeight(row.weight)}%` }}</td>
              <td>{{ ruleText(row) }}</td>
              <td>
                <span class="tag" :title="row.metricCode === COMPETE_CODE ? row.enableNote || '' : ''">
                  <span class="dot"></span>{{ row.metricCode === COMPETE_CODE ? '🔒' : '' }}{{ statusLabel(row.status) }}
                </span>
              </td>
              <td class="num">v{{ row.version }}</td>
              <td>
                <button
                  v-if="row.metricCode === COMPETE_CODE"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="compete-view"
                  @click="openCompete(row)"
                >
                  查看
                </button>
                <template v-else>
                  <button class="btn btn-sec btn-sm" type="button" data-testid="metric-fetch" @click="openFetch(row)">
                    试取数
                  </button>
                  <button
                    v-if="row.status === 'ENABLED'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    @click="disableRow(row)"
                  >
                    禁用
                  </button>
                  <span v-else class="csub">已禁用</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > 0" class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <button class="btn btn-sec btn-sm" type="button" data-testid="metric-bind-open" @click="openBind">
          岗位指标集绑定
        </button>
      </div>
    </div>

    <ProtoDrawer :open="createOpen" title="创建指标" width="720px" @close="createOpen = false">
      <div class="fld">
        <label>指标编码</label>
        <input v-model="form.metricCode" data-testid="metric-code" placeholder="TRAIN_FINISH_RATE" />
      </div>
      <div class="fld">
        <label>指标名称</label>
        <input v-model="form.metricName" data-testid="metric-name" />
      </div>
      <div class="fld">
        <label>取数来源</label>
        <select v-model="form.dataSource" data-testid="metric-source">
          <option value="MANUAL">手工录入</option>
          <option value="AUTO">系统自动</option>
          <option value="EXAM">考试成绩</option>
        </select>
      </div>
      <div class="fld">
        <label>全局权重（%）</label>
        <input v-model="form.weight" data-testid="metric-weight" type="number" min="0" max="100" step="0.01" />
      </div>
      <template v-if="form.dataSource === 'AUTO'">
        <div class="fld">
          <label>取数模块</label>
          <select v-model="form.module" data-testid="metric-module">
            <option value="TRAIN">TRAIN</option>
            <option value="MEET">MEET</option>
            <option value="REPORT">REPORT</option>
            <option value="LIVE">LIVE</option>
            <option value="FIN">FIN</option>
            <option value="FLOW">FLOW</option>
          </select>
        </div>
        <div class="fld">
          <label>指标表达式</label>
          <input v-model="form.metricExpression" data-testid="metric-expression" placeholder="finish_rate" />
        </div>
      </template>
      <div class="fld">
        <label>得分规则</label>
        <select v-model="form.ruleType" data-testid="metric-rule-type">
          <option value="SEGMENT">分段</option>
          <option value="LINEAR">线性</option>
        </select>
      </div>
      <template v-if="form.ruleType === 'SEGMENT'">
        <div v-for="(seg, index) in form.segments" :key="index" class="rowline" style="gap: 8px; margin-bottom: 8px">
          <input
            v-model="seg.minValue"
            :data-testid="`segment-${index}-min`"
            type="number"
            step="0.01"
            placeholder="下限"
            style="width: 90px"
          />
          <input
            v-model="seg.maxValue"
            :data-testid="`segment-${index}-max`"
            type="number"
            step="0.01"
            placeholder="上限，空=∞"
            style="width: 120px"
          />
          <input
            v-model="seg.score"
            :data-testid="`segment-${index}-score`"
            type="number"
            step="0.01"
            placeholder="得分"
            style="width: 90px"
          />
        </div>
      </template>
      <template v-else>
        <div class="rowline" style="gap: 8px">
          <input v-model="form.minMetric" data-testid="linear-min-metric" type="number" step="0.01" placeholder="指标下限" />
          <input v-model="form.maxMetric" data-testid="linear-max-metric" type="number" step="0.01" placeholder="指标上限" />
          <input v-model="form.minScore" data-testid="linear-min-score" type="number" step="0.01" placeholder="分数下限" />
          <input v-model="form.maxScore" data-testid="linear-max-score" type="number" step="0.01" placeholder="分数上限" />
        </div>
      </template>
      <p v-if="formError" data-testid="metric-form-error" class="hint" style="color: var(--red); margin-top: 8px">
        {{ formError }}
      </p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="metric-save" @click="submitCreate">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="bindOpen" title="岗位指标集绑定" width="640px" @close="bindOpen = false">
      <div class="fld">
        <label>岗位</label>
        <select v-model="bindPosition" data-testid="bind-position">
          <option value="R5">直播运营 R5</option>
          <option value="R6">内容运营 R6</option>
          <option value="R2">行政管理 R2</option>
          <option value="R4">运营总监 R4</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>绑定</th>
              <th>指标</th>
              <th>全局权重</th>
              <th>覆盖权重</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in bindItems" :key="item.id">
              <td>
                <input
                  v-model="item.checked"
                  type="checkbox"
                  :data-testid="`bind-check-${item.metricCode}`"
                />
              </td>
              <td>{{ item.metricName }}<div class="csub mono">{{ item.metricCode }}</div></td>
              <td class="num">{{ formatWeight(item.weight) }}%</td>
              <td>
                <input
                  v-model="item.override"
                  :data-testid="`bind-weight-${item.metricCode}`"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  placeholder="留空用全局"
                  style="width: 120px"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        data-testid="metric-weight-total"
        class="hint"
        :style="{ color: weightOk ? 'inherit' : 'var(--red)', marginTop: '10px' }"
      >
        Σ 权重 = {{ formatWeight(bindTotal) }}%
      </p>
      <p v-if="bindError" data-testid="metric-bind-error" class="hint" style="color: var(--red)">{{ bindError }}</p>
      <p v-if="bindOk" data-testid="metric-bind-ok" class="hint">{{ bindOk }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="bindOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="metric-bind-save" @click="submitBind">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="fetchOpen" title="试取数" width="480px" @close="fetchOpen = false">
      <p v-if="fetchTarget" class="hint">{{ fetchTarget.metricCode }} · {{ fetchTarget.metricName }}</p>
      <div class="fld">
        <label>试取周期</label>
        <input v-model="fetchPeriod" data-testid="metric-fetch-period" type="month" />
      </div>
      <p class="hint">发布前建议试一次。本地只验证取数通道，不访问外部系统。</p>
      <p v-if="fetchResult" data-testid="metric-fetch-result">{{ fetchResult }}</p>
      <p v-if="fetchError" data-testid="metric-fetch-error" class="hint" style="color: var(--red)">{{ fetchError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="fetchOpen = false">关闭</button>
        <button class="btn btn-pri" type="button" data-testid="metric-fetch-run" @click="runFetch">试取</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="competeOpen" title="查看指标" width="640px" @close="competeOpen = false">
      <div v-if="compete" class="formrow one">
        <div class="fld"><label>指标编码</label><div class="mono">{{ compete.metricCode }}</div></div>
        <div class="fld"><label>指标名称</label><div>{{ compete.metricName }}</div></div>
        <div class="fld"><label>状态</label><div>🔒 {{ statusLabel(compete.status) }}</div></div>
        <div class="fld"><label>锁定说明</label><div data-testid="compete-note">{{ compete.enableNote }}</div></div>
      </div>
      <p v-if="competeError" data-testid="compete-lock-error" class="hint" style="color: var(--red)">{{ competeError }}</p>
      <template #foot>
        <button class="btn btn-sec" type="button" @click="competeOpen = false">关闭</button>
        <button class="btn btn-pri" type="button" data-testid="compete-enable" @click="tryEnableCompete">启用</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const COMPETE_CODE = 'COMPETE_SUBMIT_RATE'

type ScoreRule = { ruleType?: string; segments?: unknown[]; linear?: Record<string, number> }
type SourceConfig = { module: string; metricExpression: string; periodType: string }
type MetricRow = {
  id: number
  metricCode: string
  metricName: string
  dataSource: string
  weight: number
  scoreRule: ScoreRule
  status: string
  version: number
  enableNote?: string
  sourceConfig?: SourceConfig
}
type SegmentForm = { minValue: string; maxValue: string; score: string }
type BindItem = { id: number; metricCode: string; metricName: string; weight: number; checked: boolean; override: string }

const rows = ref<MetricRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const filters = reactive({ metricName: '', dataSource: '', status: '' })

const createOpen = ref(false)
const formError = ref('')
const form = reactive({
  metricCode: '',
  metricName: '',
  dataSource: 'MANUAL',
  weight: '10',
  module: 'TRAIN',
  metricExpression: '',
  ruleType: 'SEGMENT',
  segments: [
    { minValue: '0', maxValue: '50', score: '40' },
    { minValue: '50', maxValue: '100', score: '80' },
  ] as SegmentForm[],
  minMetric: '0',
  maxMetric: '100',
  minScore: '0',
  maxScore: '100',
})

const bindOpen = ref(false)
const bindPosition = ref('R5')
const bindItems = ref<BindItem[]>([])
const bindError = ref('')
const bindOk = ref('')

const competeOpen = ref(false)
const compete = ref<MetricRow | null>(null)
const competeError = ref('')

type ManualMetric = { metricCode: string; metricName: string }
const coverage = reactive({
  enabledMetricCount: 0,
  autoMetricCount: 0,
  autoCoverageRate: 0,
  manualMetrics: [] as ManualMetric[],
})
const coverageError = ref('')
const showManual = ref(false)
const fetchOpen = ref(false)
const fetchTarget = ref<MetricRow | null>(null)
const fetchPeriod = ref(previousMonth())
const fetchResult = ref('')
const fetchError = ref('')

const coverageLevel = computed(() => {
  if (!coverage.enabledMetricCount) return 'empty'
  return coverage.autoCoverageRate > 80 ? 'ok' : 'warn'
})
const coverageStyle = computed(() => {
  if (coverageLevel.value === 'ok') return { background: 'rgba(52,199,89,.12)', border: '1px solid rgba(52,199,89,.35)' }
  if (coverageLevel.value === 'warn') return { background: 'rgba(255,149,0,.12)', border: '1px solid rgba(255,149,0,.4)' }
  return { background: 'rgba(0,0,0,.03)', border: '1px solid rgba(0,0,0,.08)' }
})
const coverageRateText = computed(() => `${Number(coverage.autoCoverageRate || 0).toFixed(2)}%`)
const coverageFlag = computed(() => {
  if (!coverage.enabledMetricCount) return '暂无启用指标'
  if (coverage.autoCoverageRate > 80) return '达标（BR-105 >80%）'
  return '未达标'
})

function previousMonth() {
  const now = new Date()
  const cursor = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  return `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`
}

const bindTotal = computed(() => {
  let sum = 0
  for (const item of bindItems.value) {
    if (!item.checked) continue
    const raw = asText(item.override) === '' ? item.weight : Number(item.override)
    if (Number.isFinite(raw)) sum += raw
  }
  return Math.round(sum * 100) / 100
})
const weightOk = computed(() => Math.abs(bindTotal.value - 100) < 0.001)

function formatWeight(value: number) {
  const rounded = Math.round(Number(value) * 100) / 100
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2)
}

function sourceLabel(source: string) {
  if (source === 'AUTO') return '系统自动'
  if (source === 'EXAM') return '考试成绩'
  return '手工录入'
}

function sourceStyle(source: string) {
  if (source === 'AUTO') return { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
  if (source === 'EXAM') return { background: 'rgba(175,82,218,.12)', color: '#8944ab' }
  return { background: 'rgba(255,149,0,.12)', color: '#c46a00' }
}

function statusLabel(status: string) {
  return status === 'ENABLED' ? '启用' : '禁用'
}

function mappingText(row: MetricRow) {
  if (row.dataSource !== 'AUTO' || !row.sourceConfig) return '—'
  return `${row.sourceConfig.module} · ${row.sourceConfig.metricExpression} · 月`
}

function ruleText(row: MetricRow) {
  if (row.scoreRule?.ruleType === 'LINEAR') return '线性'
  const count = row.scoreRule?.segments?.length || 0
  return count ? `分段 ${count} 段` : '分段'
}

function rejectText(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    return `${body.code ?? ''} ${body.msg || ''}`.trim()
  }
  return errorMessage(err)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 100 }
    if (filters.metricName) params.metricName = filters.metricName
    if (filters.dataSource) params.dataSource = filters.dataSource
    if (filters.status) params.status = filters.status
    const res = await http.get('/perf/metric/list', { params })
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (err) {
    error.value = rejectText(err)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.metricName = ''
  filters.dataSource = ''
  filters.status = ''
  loadList()
}

function openCreate() {
  form.metricCode = ''
  form.metricName = ''
  form.dataSource = 'MANUAL'
  form.weight = '10'
  form.module = 'TRAIN'
  form.metricExpression = ''
  form.ruleType = 'SEGMENT'
  form.segments = [
    { minValue: '0', maxValue: '50', score: '40' },
    { minValue: '50', maxValue: '100', score: '80' },
  ]
  form.minMetric = '0'
  form.maxMetric = '100'
  form.minScore = '0'
  form.maxScore = '100'
  formError.value = ''
  createOpen.value = true
}

function scoreRulePayload() {
  if (form.ruleType === 'LINEAR') {
    return {
      ruleType: 'LINEAR',
      linear: {
        minMetric: Number(form.minMetric),
        maxMetric: Number(form.maxMetric),
        minScore: Number(form.minScore),
        maxScore: Number(form.maxScore),
      },
    }
  }
  return {
    ruleType: 'SEGMENT',
    segments: form.segments.map((seg) => ({
      minValue: Number(seg.minValue),
      maxValue: asText(seg.maxValue) === '' ? null : Number(seg.maxValue),
      score: Number(seg.score),
    })),
  }
}

function asText(value: unknown) {
  return String(value ?? '').trim()
}

async function submitCreate() {
  formError.value = ''
  const payload: Record<string, unknown> = {
    metricCode: asText(form.metricCode),
    metricName: asText(form.metricName),
    dataSource: form.dataSource,
    weight: Number(form.weight),
    scoreRule: scoreRulePayload(),
    status: 'ENABLED',
  }
  if (form.dataSource === 'AUTO') {
    payload.sourceConfig = {
      module: form.module,
      metricExpression: asText(form.metricExpression),
      periodType: 'MONTHLY',
    }
  }
  try {
    await http.post('/perf/metric', payload)
    createOpen.value = false
    await loadList()
    await loadCoverage()
  } catch (err) {
    formError.value = rejectText(err)
  }
}

async function disableRow(row: MetricRow) {
  if (!window.confirm('禁用后该指标不参与后续月度计算（PER-M-R1），确认？')) return
  try {
    await http.delete(`/perf/metric/${row.id}`)
    await loadList()
    await loadCoverage()
  } catch (err) {
    error.value = rejectText(err)
  }
}

function openBind() {
  bindPosition.value = 'R5'
  bindError.value = ''
  bindOk.value = ''
  bindItems.value = rows.value.map((row) => ({
    id: row.id,
    metricCode: row.metricCode,
    metricName: row.metricName,
    weight: row.weight,
    checked: false,
    override: '',
  }))
  bindOpen.value = true
}

async function submitBind() {
  bindError.value = ''
  bindOk.value = ''
  const metricBindings = bindItems.value
    .filter((item) => item.checked)
    .map((item) => {
      const binding: { metricId: number; weightOverride?: number } = { metricId: item.id }
      if (asText(item.override) !== '') binding.weightOverride = Number(item.override)
      return binding
    })
  try {
    const res = await http.post('/perf/metric/bind-position', {
      positionCode: bindPosition.value,
      metricBindings,
    })
    const data = res.data.data as { boundCount: number }
    bindOk.value = `已绑定 ${data.boundCount} 项指标`
  } catch (err) {
    bindError.value = rejectText(err)
  }
}

function openCompete(row: MetricRow) {
  compete.value = row
  competeError.value = ''
  competeOpen.value = true
}

async function tryEnableCompete() {
  if (!compete.value) return
  competeError.value = ''
  try {
    await http.put(`/perf/metric/${compete.value.id}`, {
      metricCode: compete.value.metricCode,
      metricName: compete.value.metricName,
      dataSource: compete.value.dataSource,
      weight: compete.value.weight,
      scoreRule: compete.value.scoreRule,
      status: 'ENABLED',
      sourceConfig: compete.value.sourceConfig,
    })
  } catch (err) {
    competeError.value = rejectText(err)
  }
}

async function loadCoverage() {
  coverageError.value = ''
  try {
    const res = await http.get('/perf/metric/auto-coverage')
    const data = res.data.data || {}
    coverage.enabledMetricCount = data.enabledMetricCount || 0
    coverage.autoMetricCount = data.autoMetricCount || 0
    coverage.autoCoverageRate = data.autoCoverageRate || 0
    coverage.manualMetrics = data.manualMetrics || []
  } catch (err) {
    coverageError.value = rejectText(err)
  }
}

function openFetch(row: MetricRow) {
  fetchTarget.value = row
  fetchPeriod.value = previousMonth()
  fetchResult.value = ''
  fetchError.value = ''
  fetchOpen.value = true
}

async function runFetch() {
  if (!fetchTarget.value) return
  fetchResult.value = ''
  fetchError.value = ''
  try {
    const res = await http.post('/perf/metric/test-fetch', {
      metricId: fetchTarget.value.id,
      testPeriod: fetchPeriod.value,
    })
    const data = res.data.data || {}
    const sample = data.sampleValue === undefined || data.sampleValue === null ? '' : `样本 ${data.sampleValue}`
    const reason = data.errorReason ? String(data.errorReason) : ''
    const state = data.fetchable ? '通道可用' : '未能取数'
    fetchResult.value = [state, sample, reason, `${data.elapsedMs ?? 0} ms`].filter(Boolean).join(' · ')
  } catch (err) {
    fetchError.value = rejectText(err)
  }
}

onMounted(async () => {
  await loadList()
  await loadCoverage()
})
</script>
