<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>全链路数据看板</h1>
        <div class="sub">DC-003 · /ims/dc/dashboard · 经营总览 / 链路健康度 / 维度下钻</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/dc/trace">返回穿透查询</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <label class="fld" style="width: auto">
        周期
        <input v-model="period" data-testid="dc-dash-period" type="month" @change="load" />
      </label>
      <span data-testid="dc-dash-as-of" class="hint">数据截至 {{ overview?.dataAsOf || '—' }}</span>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dc-dash-refresh">刷新</button>
    </form>

    <p v-if="error" class="hint" data-testid="dc-dash-error" style="color: var(--red)">{{ error }}</p>
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
                    :to="{ path: '/ims/dc/trace', query: { entryType: 'SESSION', keyword: child.dimensionValue } }"
                  >
                    {{ child.dimensionValue }}
                  </router-link>
                </td>
                <td class="num">{{ money(child.gmv) }}</td>
                <td class="num" :style="neg(child.netProfit)">{{ money(child.netProfit) }}</td>
                <td class="num">{{ child.sessionCount }}</td>
                <td>场次明细</td>
              </tr>
            </template>
            <tr v-if="!rows.length">
              <td colspan="5">该周期暂无已核算场次</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
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
const open = reactive<Record<string, boolean>>({})

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

function toggle(value: string) {
  open[value] = !open[value]
}

async function loadDimension() {
  const res = await http.get('/dc/dashboard/dimension', {
    params: { statPeriod: period.value, dimensionType: dimensionType.value },
  })
  rows.value = res.data.data || []
  for (const key of Object.keys(open)) delete open[key]
}

async function load() {
  error.value = ''
  try {
    const [overviewRes, healthRes] = await Promise.all([
      http.get('/dc/dashboard/overview', { params: { statPeriod: period.value } }),
      http.get('/dc/dashboard/health', { params: { dateRange: monthBounds(period.value) } }),
    ])
    overview.value = overviewRes.data.data
    health.value = healthRes.data.data
    await loadDimension()
  } catch (err) {
    error.value = errorMessage(err)
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
</style>
