<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>利润反查</h1>
        <div class="sub">DC-002 · 利润列表 / 聚合下钻 / 异常清单 · GET /dc/profit-trace/*</div>
      </div>
    </div>

    <div v-if="dataAsOf" class="hint" style="margin-bottom: 10px">
      DC-002 · perm <code>ims:fin:profit-trace:query</code> · 数据截至 {{ dataAsOf }}
    </div>

    <div class="tabs" style="margin-bottom: 8px">
      <button type="button" class="tab" :class="{ on: tab === 'list' }" data-testid="fin-trace-tab-list" @click="tab = 'list'">
        利润列表
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'aggregate' }"
        data-testid="fin-trace-tab-aggregate"
        @click="openAggregate"
      >
        聚合下钻
      </button>
      <button
        type="button"
        class="tab"
        :class="{ on: tab === 'abnormal' }"
        data-testid="fin-trace-tab-abnormal"
        @click="openAbnormal"
      >
        异常清单
      </button>
    </div>

    <template v-if="tab === 'list'">
      <form class="qbar" @submit.prevent="loadList">
        <input v-model="query.sessionCode" data-testid="fin-trace-session" placeholder="场次 ID" style="width: 180px" />
        <input v-model="query.platform" placeholder="平台" style="width: 100px" />
        <select v-model="query.calcStatus" style="width: 120px">
          <option value="">全部状态</option>
          <option value="CALCULATED">已计算</option>
          <option value="RECALCULATED">已重算</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="button" @click="loadList">查询</button>
      </form>

      <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>

      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>场次 ID</th>
                <th>标题</th>
                <th>净利润</th>
                <th>毛利</th>
                <th>版本</th>
                <th>异常</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!rows.length">
                <td colspan="7"><div class="empty"><div class="et">暂无已核算利润（需先核准成本）</div></div></td>
              </tr>
              <tr v-for="row in rows" v-else :key="row.sessionCode">
                <td class="mono">{{ row.sessionCode }}</td>
                <td>{{ row.sessionTitle }}</td>
                <td class="num">¥{{ fmt(row.netProfit) }}</td>
                <td class="num">¥{{ fmt(row.grossProfit) }}</td>
                <td>V{{ row.calcVersion }}</td>
                <td>{{ row.isAbnormal ? '异常' : '—' }}</td>
                <td>
                  <button class="btn btn-sec btn-sm" type="button" @click="openTrace(String(row.sessionCode))">反查</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'aggregate'">
      <div class="qbar" data-testid="fin-trace-aggregate-by">
        <button
          v-for="item in aggregateOptions"
          :key="item.value"
          type="button"
          class="btn btn-sm"
          :class="aggregateBy === item.value ? 'btn-pri' : 'btn-sec'"
          :data-testid="'fin-trace-aggregate-' + item.value"
          @click="switchAggregate(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
      <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table data-testid="fin-trace-aggregate-table">
            <thead>
              <tr>
                <th>维度</th>
                <th>净利润</th>
                <th>毛利</th>
                <th>场次数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="aggregateLoading">
                <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!aggregateRows.length">
                <td colspan="5"><div class="empty"><div class="et">该维度暂无已核算利润</div></div></td>
              </tr>
              <template v-for="row in aggregateRows" v-else :key="row.dimensionValue">
                <tr :data-testid="'fin-trace-aggregate-row-' + row.dimensionValue">
                  <td>{{ row.dimensionLabel }}</td>
                  <td class="num">¥{{ fmt(row.netProfit) }}</td>
                  <td class="num">¥{{ fmt(row.grossProfit) }}</td>
                  <td class="num">{{ row.sessionCount }}</td>
                  <td>
                    <button class="btn btn-sec btn-sm" type="button" @click="toggleAggregate(String(row.dimensionValue))">
                      {{ expanded === row.dimensionValue ? '收起' : '展开' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="expanded === row.dimensionValue">
                  <td colspan="5">
                    <table>
                      <thead>
                        <tr>
                          <th>场次 ID</th>
                          <th>标题</th>
                          <th>净利润</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="child in row.children || []" :key="child.sessionCode">
                          <td class="mono">{{ child.sessionCode }}</td>
                          <td>{{ child.sessionTitle }}</td>
                          <td class="num">¥{{ fmt(child.netProfit) }}</td>
                          <td>
                            <button class="btn btn-sec btn-sm" type="button" @click="openTrace(String(child.sessionCode))">反查</button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else>
      <p class="hint" style="margin: 8px 0">联动利润核算 2σ：偏离同类均值的场次，直达金额最大的成本项。</p>
      <div v-if="error" class="hint" style="color: var(--red); margin: 8px 0">{{ error }}</div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table data-testid="fin-trace-abnormal-table">
            <thead>
              <tr>
                <th>场次 ID</th>
                <th>净利润</th>
                <th>同行均值率</th>
                <th>σ</th>
                <th>偏离</th>
                <th>异常成本项</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="abnormalLoading">
                <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
              </tr>
              <tr v-else-if="!abnormalRows.length">
                <td colspan="7"><div class="empty"><div class="et">暂无异常利润</div></div></td>
              </tr>
              <tr v-for="row in abnormalRows" v-else :key="row.sessionCode" :data-testid="'fin-trace-abnormal-row-' + row.sessionCode">
                <td class="mono">{{ row.sessionCode }}</td>
                <td class="num" style="color: var(--red)">¥{{ fmt(row.netProfit) }}</td>
                <td class="num">{{ row.peerAvgRate }}%</td>
                <td class="num">{{ row.sigma }}</td>
                <td class="num" :style="{ color: Math.abs(Number(row.deviationSigma)) >= 3 ? 'var(--red)' : '#d48806' }">
                  {{ row.deviationSigma }}σ
                </td>
                <td><span class="tag" style="color: var(--red)">{{ costLabel(String(row.abnormalCostItem || '')) }}</span></td>
                <td>
                  <button
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="fin-trace-abnormal-open"
                    @click="openTrace(String(row.sessionCode), String(row.abnormalCostItem || ''))"
                  >
                    直达反查
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-if="drawerOpen && chain" class="drawer-mask" @click.self="closeDrawer">
      <div class="drawer" data-testid="fin-profit-trace-chain-drawer" style="width: 680px">
        <div class="drawer-h">
          <b>反查链路 · {{ chain.sessionCode }}</b>
          <span class="hint">{{ queryCostMs }} ms</span>
          <button type="button" class="btn btn-sec btn-sm" @click="closeDrawer">关闭</button>
        </div>
        <p class="hint">BR-209：利润 → 场次 → 账号/资产/责任人/实名人 → 成本明细</p>
        <div class="g2" style="margin-bottom: 12px">
          <div class="card stat"><span class="l">净利润</span><div class="n">¥{{ fmt(chain.chain?.profit?.netProfit) }}</div></div>
          <div class="card stat"><span class="l">场次</span><div class="n" style="font-size: 14px">{{ chain.chain?.session?.sessionTitle }}</div></div>
        </div>
        <ul class="hint" style="line-height: 1.8; margin-bottom: 12px">
          <li>账号：{{ chain.chain?.account?.accountNo || '—' }}</li>
          <li>责任人：{{ chain.chain?.responsibleUser?.userName || '—' }}</li>
          <li>实名人：{{ chain.chain?.realnamePersons?.[0]?.userName || '—' }}</li>
          <li>资产：{{ (chain.chain?.assets || []).map((a: { assetCode: string }) => a.assetCode).join(', ') || '—' }}</li>
        </ul>
        <h3 style="font-size: 14px; margin-bottom: 6px">成本明细</h3>
        <table>
          <thead><tr><th>项目</th><th>金额</th></tr></thead>
          <tbody>
            <tr
              v-for="item in chain.chain?.costDetail || []"
              :key="item.costItem"
              :data-testid="'fin-trace-cost-' + item.costItem"
              :data-highlight="highlightCost === item.costItem ? '1' : '0'"
              :style="highlightCost === item.costItem ? 'background:#fdecea' : ''"
            >
              <td>{{ item.costItemLabel || item.costItem }}</td>
              <td class="num">{{ item.amount == null ? '—' : '¥' + fmt(item.amount) }}</td>
            </tr>
          </tbody>
        </table>
        <h3 style="font-size: 14px; margin: 12px 0 6px">分成明细</h3>
        <table>
          <thead><tr><th>对象</th><th>分成</th></tr></thead>
          <tbody>
            <tr v-for="(s, i) in chain.chain?.shareDetail || []" :key="i">
              <td>{{ s.targetRefName || s.shareTarget }}</td>
              <td class="num">{{ s.shareAmount == null ? '—' : '¥' + fmt(s.shareAmount) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'

const route = useRoute()

const loading = ref(false)
const error = ref('')
const rows = ref<Record<string, any>[]>([])
const dataAsOf = ref('')
const drawerOpen = ref(false)
const chain = ref<Record<string, any> | null>(null)
const queryCostMs = ref(0)
const highlightCost = ref('')
const tab = ref<'list' | 'aggregate' | 'abnormal'>('list')
const query = reactive({ sessionCode: '', platform: '', calcStatus: '' })

const aggregateOptions = [
  { value: 'PERSON', label: '按人' },
  { value: 'ACCOUNT', label: '按账号' },
  { value: 'TEAM', label: '按团队' },
  { value: 'IP_GROUP', label: '按IP组' },
  { value: 'MONTH', label: '按月份' },
]
const aggregateBy = ref('ACCOUNT')
const aggregateLoading = ref(false)
const aggregateRows = ref<Record<string, any>[]>([])
const expanded = ref('')
const abnormalLoading = ref(false)
const abnormalRows = ref<Record<string, any>[]>([])

const costLabels: Record<string, string> = {
  commission: '平台佣金',
  ad: '投流成本',
  recharge: '充值成本',
  fixed: '固定成本',
  sample: '样品成本',
  shareDaren: '达人分成',
  shareRealname: '实名人分成',
}

function fmt(n: unknown) {
  return Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function costLabel(key: string) {
  return costLabels[key] || key || '—'
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/dc/profit-trace/list', {
      params: {
        pageNo: 1,
        pageSize: 50,
        sessionCode: query.sessionCode || undefined,
        platform: query.platform || undefined,
        calcStatus: query.calcStatus || undefined,
      },
    })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
    dataAsOf.value = res.data.data?.dataAsOf || ''
  } finally {
    loading.value = false
  }
}

async function loadAggregate() {
  aggregateLoading.value = true
  error.value = ''
  try {
    const res = await http.get('/dc/profit-trace/aggregate', { params: { aggregateBy: aggregateBy.value } })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      aggregateRows.value = []
      return
    }
    aggregateRows.value = res.data.data || []
  } finally {
    aggregateLoading.value = false
  }
}

function openAggregate() {
  tab.value = 'aggregate'
  loadAggregate()
}

function switchAggregate(value: string) {
  aggregateBy.value = value
  expanded.value = ''
  loadAggregate()
}

function toggleAggregate(value: string) {
  expanded.value = expanded.value === value ? '' : value
}

async function loadAbnormal() {
  abnormalLoading.value = true
  error.value = ''
  try {
    const res = await http.get('/dc/profit-trace/abnormal', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '加载失败'
      abnormalRows.value = []
      return
    }
    abnormalRows.value = res.data.data?.list || []
    dataAsOf.value = res.data.data?.dataAsOf || dataAsOf.value
  } finally {
    abnormalLoading.value = false
  }
}

function openAbnormal() {
  tab.value = 'abnormal'
  loadAbnormal()
}

async function openTrace(sessionCode: string, costItem = '') {
  const res = await http.get(`/dc/profit-trace/${sessionCode}`)
  if (res.data?.code !== 0) {
    error.value = res.data?.msg || '反查失败'
    return
  }
  chain.value = res.data.data
  queryCostMs.value = res.data.data?.queryCostMs || 0
  highlightCost.value = costItem
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  highlightCost.value = ''
}

onMounted(() => {
  const code = route.query.sessionCode
  if (typeof code === 'string' && code.trim()) query.sessionCode = code.trim()
  loadList()
})
</script>
