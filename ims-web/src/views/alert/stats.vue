<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预警统计</h1>
        <div class="sub">ALERT-004 · 健康度 · 规则排行 · 合并记录 · 通道本地桩</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/escalate">升级中心</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <form class="qbar" data-testid="alert-stats-filter" @submit.prevent="load">
      <input v-model="start" data-testid="alert-stats-start" type="date" />
      <input v-model="end" data-testid="alert-stats-end" type="date" />
      <input
        v-model="ruleCode"
        data-testid="alert-stats-rule"
        placeholder="合并记录规则编码"
        style="width: 180px"
      />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
      <button class="btn btn-sec btn-sm" type="button" @click="clearRange">全部</button>
    </form>

    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

    <div v-if="overview && overview.totalAlertCount === 0" class="card" style="margin-top: 12px" data-testid="alert-stats-range-empty">
      <div class="empty"><div class="et">当前筛选范围内暂无预警</div></div>
    </div>

    <div v-if="overview" class="g4" style="margin-top: 12px">
      <div class="card stat">
        <span class="l">预警总量</span>
        <div class="n" data-testid="alert-stats-total">{{ overview.totalAlertCount }}</div>
        <div class="d">当前筛选范围内</div>
      </div>
      <div class="card stat">
        <span class="l">响应时长</span>
        <div class="n" data-testid="alert-stats-avg-minutes">{{ overview.avgResponseMinutes }}</div>
        <div class="d">分钟 · 已响应记录从发生到最近处置</div>
      </div>
      <div class="card stat">
        <span class="l">响应率</span>
        <div
          class="n"
          data-testid="alert-stats-response-rate"
          :data-neutral="overview.totalAlertCount === 0 ? '1' : '0'"
          :style="{ color: rateColor(overview.responseRate, 90) }"
        >
          {{ overview.responseRate }}%
        </div>
        <div class="d">已响应 {{ overview.respondedCount }} / {{ overview.totalAlertCount }} · BR-112 &gt;90%</div>
      </div>
      <div class="card stat">
        <span class="l">解决率</span>
        <div class="n" data-testid="alert-stats-resolution-rate">{{ overview.resolutionRate }}%</div>
        <div class="d" data-testid="alert-stats-resolved-count">
          已解决 {{ overview.resolvedCount }} / {{ overview.totalAlertCount }}
        </div>
      </div>
    </div>

    <div v-if="overview" class="g4">
      <div class="card stat">
        <span class="l">送达率</span>
        <div
          class="n"
          data-testid="alert-stats-delivery-rate"
          :data-neutral="overview.totalAlertCount === 0 ? '1' : '0'"
          :style="{ color: rateColor(overview.deliveryRate, 99) }"
        >
          {{ overview.deliveryRate }}%
        </div>
        <div class="d">只计工作台落库</div>
      </div>
      <div class="card stat">
        <span class="l">误报率</span>
        <div class="n" data-testid="alert-stats-false-rate" :style="{ color: falseRateColor }">
          {{ overview.falseAlarmRate }}%
        </div>
        <div class="d" data-testid="alert-stats-false-hint">{{ falseHint }}</div>
      </div>
      <div class="card stat">
        <span class="l">升级率</span>
        <div class="n" data-testid="alert-stats-escalate-rate">{{ overview.escalateRate }}%</div>
        <div class="d">越过起始级仍未在时限内响应</div>
      </div>
      <div class="card stat">
        <span class="l">级别分布</span>
        <div class="n" style="font-size: 16px; margin-top: 10px">
          <span data-testid="alert-stats-l1">L1 {{ overview.byLevel.L1 }}</span>
          ·
          <span data-testid="alert-stats-l2">L2 {{ overview.byLevel.L2 }}</span>
          ·
          <span data-testid="alert-stats-l3">L3 {{ overview.byLevel.L3 }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="overview && overview.totalAlertCount === 0"
      class="card"
      style="margin-top: 12px"
      data-testid="alert-stats-empty"
    >
      <div class="empty"><div class="et">当前筛选范围内暂无预警</div></div>
    </div>

    <div v-if="overview" class="card" style="margin-top: 12px; padding: 16px" data-testid="alert-channel-receipts">
      <div class="hd-row"><h3 style="margin: 0">通道回执</h3></div>
      <p class="hint">钉钉、短信为本地桩，不实际外发。短信只在兜底记账后才有回执。</p>
      <div v-if="overview.totalAlertCount === 0" class="empty" data-testid="alert-channel-empty">
        <div class="et">当前范围内暂无通道回执</div>
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>通道</th>
            <th>回执</th>
            <th>外发</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ch in overview.channelReceipts"
            :key="ch.channel"
            :data-testid="`alert-channel-${ch.channel}`"
            :data-empty="ch.empty ? '1' : '0'"
          >
            <td>{{ ch.label }}</td>
            <td>{{ ch.empty ? `暂无回执 · ${ch.note}` : `${ch.receiptCount} 条 · ${ch.note}` }}</td>
            <td>不外发</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top: 16px; padding: 16px" data-testid="alert-weekly">
      <div class="pg-h" style="margin-bottom: 8px">
        <div>
          <h2 style="margin: 0; font-size: 16px">预警周报</h2>
          <div class="sub">GET /alert/stats/weekly-report · 在线查看，周一汇总口径</div>
        </div>
        <select v-model="weekStart" data-testid="alert-weekly-week" @change="loadWeekly">
          <option v-for="week in weeks" :key="week" :value="week">{{ week }} 起</option>
        </select>
      </div>
      <p class="hint">周报由定时任务汇总后供管理层在线查看。钉钉/短信外发保持本地桩，本页不实际推送。</p>
      <p v-if="weeklyError" class="hint" style="color: var(--red)">{{ weeklyError }}</p>
      <div v-if="weekly && weekly.totalAlerts === 0" class="empty" data-testid="alert-weekly-empty">
        <div class="et">本周期周报尚未生成（每日汇总，周一推送管理层）</div>
      </div>
      <template v-else-if="weekly">
        <div class="g4" style="margin-top: 12px">
          <div class="card stat">
            <span class="l">本周总量</span>
            <div class="n" data-testid="alert-weekly-total">{{ weekly.totalAlerts }}</div>
            <div class="d" data-testid="alert-weekly-range">{{ weekly.weekRange[0] }} ~ {{ weekly.weekRange[1] }}</div>
          </div>
          <div class="card stat">
            <span class="l">响应率</span>
            <div class="n" data-testid="alert-weekly-response" :style="{ color: rateColor(weekly.responseRate, 90) }">
              {{ weekly.responseRate }}%
            </div>
            <div class="d">BR-112 &gt;90%</div>
          </div>
          <div class="card stat">
            <span class="l">送达率</span>
            <div class="n" data-testid="alert-weekly-delivery">{{ weekly.deliveryRate }}%</div>
            <div class="d">工作台记录 · 不含外发</div>
          </div>
        </div>
        <div class="tbl-wrap" style="margin-top: 8px">
          <table>
            <thead>
              <tr>
                <th>Top 规则</th>
                <th>预警数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!weekly.topRules.length">
                <td colspan="2"><div class="empty"><div class="et">无规则命中</div></div></td>
              </tr>
              <tr v-for="row in weekly.topRules" v-else :key="row.ruleCode" data-testid="alert-weekly-top">
                <td class="mono">{{ row.ruleCode }}</td>
                <td class="num">{{ row.alertCount }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3 style="font-size: 14px; margin: 14px 0 8px">升级预警</h3>
        <p v-if="!weekly.escalatedAlerts.length" class="hint" data-testid="alert-weekly-escalated-empty">本周暂无已升级预警</p>
        <div v-else class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>级别</th>
                <th>当前升级级别</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in weekly.escalatedAlerts" :key="row.alertNo" data-testid="alert-weekly-escalated">
                <td>
                  <router-link class="mono" :to="`/ims/alert/escalate?alertNo=${row.alertNo}`">{{ row.alertNo }}</router-link>
                </td>
                <td>{{ row.level }}</td>
                <td class="num">{{ row.currentLevel }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3 style="font-size: 14px; margin: 14px 0 8px">优化建议</h3>
        <ul data-testid="alert-weekly-suggestions">
          <li v-for="line in weekly.suggestions" :key="line">{{ line }}</li>
        </ul>
      </template>
    </div>

    <div
      v-if="overview && overview.totalAlertCount === 0"
      class="card"
      style="margin-top: 12px"
      data-testid="alert-stats-weekly-empty"
    >
      <div class="hd-row"><h3>周报</h3></div>
      <div class="empty"><div class="et">本周期周报尚未生成（每日汇总，周一推送管理层）</div></div>
    </div>
    <div v-if="overview" class="card" style="margin-top: 12px; padding: 16px" data-testid="alert-channel-stub">
      <div class="hd-row"><h3 style="margin: 0">推送通道</h3></div>
      <p class="hint">钉钉、短信为本地桩，不实际外发。送达率只统计工作台已落库。</p>
      <table>
        <thead>
          <tr>
            <th>通道</th>
            <th>形态</th>
            <th>外发</th>
            <th>计入送达</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ch in overview.channelStubs" :key="ch.channel" :data-testid="`alert-channel-${ch.channel}`">
            <td>{{ ch.label }}</td>
            <td>{{ ch.mode === 'STUB' ? '本地桩' : '本地记录' }}</td>
            <td>{{ ch.outbound ? '外发' : '不外发' }}</td>
            <td>{{ ch.countsTowardDelivery ? '是' : '否' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top: 12px; padding: 16px" data-testid="alert-stats-rank">
      <div class="hd-row"><h3 style="margin: 0">规则命中排行</h3></div>
      <p v-if="rankError" class="hint" style="color: var(--red)">{{ rankError }}</p>
      <div v-if="!ranks.length" class="empty" data-testid="alert-stats-rank-empty">
        <div class="et">当前筛选范围内没有规则命中</div>
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>排名</th>
            <th>规则</th>
            <th>预警数</th>
            <th>合并节省</th>
            <th>响应率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in ranks" :key="row.ruleCode" :data-testid="`alert-rank-${row.ruleCode}`">
            <td class="num">{{ row.rank }}</td>
            <td>
              <div class="mono">{{ row.ruleCode }}</div>
              <div>{{ row.ruleName }}</div>
            </td>
            <td class="num">{{ row.alertCount }}</td>
            <td class="num" :title="`该规则通过去重合并节省 ${row.mergedSavingsCount} 次重复推送`">
              {{ row.mergedSavingsCount }}
            </td>
            <td class="num" :style="{ color: row.responseRate < 90 ? 'var(--orange, #d97706)' : undefined }">
              {{ row.responseRate }}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" style="margin-top: 12px; padding: 16px" data-testid="alert-stats-merge">
      <div class="hd-row"><h3 style="margin: 0">合并记录</h3></div>
      <p class="hint">同规则、同对象，自第一条起 30 分钟内归并。这里只展示，不补发、不外发。</p>
      <p v-if="mergeError" class="hint" style="color: var(--red)">{{ mergeError }}</p>
      <div v-if="!merges.length" class="empty" data-testid="alert-stats-merge-empty">
        <div class="et">{{ mergeEmptyText }}</div>
      </div>
      <table v-else>
        <thead>
          <tr>
            <th>主预警</th>
            <th>规则</th>
            <th>被合并</th>
            <th>合并次数</th>
            <th>窗口</th>
            <th>主预警时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in merges" :key="row.id" data-testid="alert-merge-row">
            <td class="mono">{{ row.masterAlertNo }}</td>
            <td class="mono">{{ row.ruleCode }}</td>
            <td>{{ row.mergedAlertNos.length }} 条</td>
            <td class="num">{{ row.mergedCount }}</td>
            <td class="num">{{ row.mergeWindowMinutes }} 分钟</td>
            <td class="mono">{{ row.masterOccurredAt?.slice(0, 16) || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http } from '../../api/http'

type ChannelStub = {
  channel: string
  label: string
  mode: string
  outbound: boolean
  countsTowardDelivery: boolean
}

type Overview = {
  totalAlertCount: number
  byLevel: { L1: number; L2: number; L3: number }
  responseRate: number
  resolutionRate: number
  deliveryRate: number
  falseAlarmRate: number
  escalateRate: number
  avgResponseMinutes: number
  respondedCount: number
  resolvedCount: number
  channelStubs: ChannelStub[]
  channelReceipts: ChannelReceipt[]
}

type ChannelReceipt = {
  channel: string
  label: string
  receiptCount: number
  empty: boolean
  note: string
  outbound: boolean
}

type RankRow = {
  rank: number
  ruleCode: string
  ruleName: string
  alertCount: number
  mergedSavingsCount: number
  responseRate: number
}

type MergeRow = {
  id: number
  ruleCode: string
  masterAlertNo: string
  mergedAlertNos: string[]
  mergedCount: number
  mergeWindowMinutes: number
  masterOccurredAt: string
}

type Weekly = {
  weekRange: [string, string]
  totalAlerts: number
  topRules: Array<{ ruleCode: string; alertCount: number }>
  responseRate: number
  deliveryRate: number
  escalatedAlerts: Array<{ alertNo: string; level: string; currentLevel: number }>
  suggestions: string[]
}

const overview = ref<Overview | null>(null)
const weekly = ref<Weekly | null>(null)
const ranks = ref<RankRow[]>([])
const merges = ref<MergeRow[]>([])
const error = ref('')
const weeklyError = ref('')
const rankError = ref('')
const mergeError = ref('')
const start = ref('')
const end = ref('')
const weekStart = ref('')
const weeks = ref<string[]>([])
const ruleCode = ref('')

const falseHint = computed(() => {
  if (!overview.value || overview.value.totalAlertCount === 0) return '当前范围内没有误报样本'
  if (overview.value.falseAlarmRate > 5) return '超过 5%，建议复核阈值（ALR-S-R3）'
  return '未超过 5% 复核线'
})

const falseRateColor = computed(() => {
  if (!overview.value || overview.value.totalAlertCount === 0) return 'inherit'
  return overview.value.falseAlarmRate > 5 ? 'var(--orange, #d97706)' : undefined
})

const mergeEmptyText = computed(() =>
  ruleCode.value.trim() ? '该规则在当前筛选下没有合并记录' : '当前筛选下没有合并记录',
)

function bjToday() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function mondayOnOrBefore(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  const utc = new Date(Date.UTC(y, m - 1, d))
  const weekday = utc.getUTCDay()
  const delta = weekday === 0 ? -6 : 1 - weekday
  utc.setUTCDate(utc.getUTCDate() + delta)
  return utc.toISOString().slice(0, 10)
}

function recentMondays() {
  const thisMonday = mondayOnOrBefore(bjToday())
  const [y, m, d] = thisMonday.split('-').map(Number)
  const base = new Date(Date.UTC(y, m - 1, d))
  const out: string[] = []
  for (let i = 0; i < 8; i += 1) {
    const dt = new Date(base)
    dt.setUTCDate(base.getUTCDate() - i * 7)
    out.push(dt.toISOString().slice(0, 10))
  }
  return out
}

function rateColor(value: number, target: number) {
  if (!overview.value || overview.value.totalAlertCount === 0) return 'inherit'
  return value >= target ? 'var(--green, #15803d)' : 'var(--orange, #d97706)'
}

function dateParams(): Record<string, string> | null {
  if (start.value && end.value) return { dateRange: `${start.value},${end.value}` }
  if (start.value || end.value) {
    error.value = '请同时填写起止日期'
    return null
  }
  return {}
}

function clearRange() {
  start.value = ''
  end.value = ''
  ruleCode.value = ''
  load()
}

async function load() {
  error.value = ''
  rankError.value = ''
  mergeError.value = ''
  const params = dateParams()
  if (!params) return
  try {
    const [overviewRes, rankRes, mergeRes] = await Promise.all([
      http.get('/alert/stats/overview', { params }),
      http.get('/alert/stats/rule-rank', { params: { ...params, topN: 10 } }),
      http.get('/alert/stats/merge-logs', {
        params: { ...params, ruleCode: ruleCode.value.trim(), pageNo: 1, pageSize: 10 },
      }),
    ])
    if (overviewRes.data.code !== 0) {
      error.value = overviewRes.data.msg || '加载失败'
      overview.value = null
    } else {
      overview.value = overviewRes.data.data
    }
    if (rankRes.data.code !== 0) {
      rankError.value = rankRes.data.msg || '排行加载失败'
      ranks.value = []
    } else {
      ranks.value = rankRes.data.data || []
    }
    if (mergeRes.data.code !== 0) {
      mergeError.value = mergeRes.data.msg || '合并记录加载失败'
      merges.value = []
    } else {
      merges.value = mergeRes.data.data?.list || []
    }
  } catch (err) {
    const body = err as { msg?: string }
    error.value = body?.msg || '加载失败'
    overview.value = null
    ranks.value = []
    merges.value = []
  }
}

async function loadWeekly() {
  weeklyError.value = ''
  try {
    const res = await http.get('/alert/stats/weekly-report', { params: { weekStart: weekStart.value } })
    weekly.value = res.data.data
  } catch (err) {
    weekly.value = null
    weeklyError.value = (err as { msg?: string })?.msg || '周报加载失败'
  }
}

onMounted(() => {
  weeks.value = recentMondays()
  weekStart.value = weeks.value[0] || ''
  load()
  loadWeekly()
})
</script>
