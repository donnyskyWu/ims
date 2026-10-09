<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预警统计</h1>
        <div class="sub">ALERT-004 · GET /alert/stats/overview · 响应时长 / 响应率 / 解决率</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/escalate">升级中心</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/rule">预警规则</router-link>
      </div>
    </div>

    <form class="qbar" @submit.prevent="load">
      <input v-model="start" data-testid="alert-stats-start" type="date" />
      <input v-model="end" data-testid="alert-stats-end" type="date" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
      <button class="btn btn-sec btn-sm" type="button" @click="clearRange">全部</button>
    </form>

    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>

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
        <div class="n" data-testid="alert-stats-response-rate" :style="{ color: rateColor(overview.responseRate, 90) }">
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
        <div class="n" data-testid="alert-stats-delivery-rate" :style="{ color: rateColor(overview.deliveryRate, 99) }">
          {{ overview.deliveryRate }}%
        </div>
        <div class="d">工作台已记录 · 不含钉钉/短信外发</div>
      </div>
      <div class="card stat">
        <span class="l">误报率</span>
        <div class="n" data-testid="alert-stats-false-rate" :style="{ color: overview.falseAlarmRate > 5 ? 'var(--orange, #d97706)' : undefined }">
          {{ overview.falseAlarmRate }}%
        </div>
        <div class="d">&gt;5% 提示复核阈值</div>
      </div>
      <div class="card stat">
        <span class="l">升级率</span>
        <div class="n" data-testid="alert-stats-escalate-rate">{{ overview.escalateRate }}%</div>
        <div class="d">越过起始级仍未在时限内响应</div>
      </div>
      <div class="card stat">
        <span class="l">级别分布</span>
        <div class="n" style="font-size: 16px; margin-top: 10px">
          <span data-testid="alert-stats-l1">
            <router-link data-testid="alert-stats-level-L1" :to="{ path: '/ims/alert/live', query: { level: 'L1' } }">
              L1 {{ overview.byLevel.L1 }}
            </router-link>
          </span>
          ·
          <span data-testid="alert-stats-l2">
            <router-link data-testid="alert-stats-level-L2" :to="{ path: '/ims/alert/live', query: { level: 'L2' } }">
              L2 {{ overview.byLevel.L2 }}
            </router-link>
          </span>
          ·
          <span data-testid="alert-stats-l3">
            <router-link data-testid="alert-stats-level-L3" :to="{ path: '/ims/alert/live', query: { level: 'L3' } }">
              L3 {{ overview.byLevel.L3 }}
            </router-link>
          </span>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

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
const error = ref('')
const weeklyError = ref('')
const start = ref('')
const end = ref('')
const weekStart = ref('')
const weeks = ref<string[]>([])

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
  return value >= target ? 'var(--green, #15803d)' : 'var(--orange, #d97706)'
}

function clearRange() {
  start.value = ''
  end.value = ''
  load()
}

async function load() {
  error.value = ''
  const params: Record<string, string> = {}
  if (start.value && end.value) params.dateRange = `${start.value},${end.value}`
  else if (start.value || end.value) {
    error.value = '请同时填写起止日期'
    return
  }
  try {
    const res = await http.get('/alert/stats/overview', { params })
    overview.value = res.data.data
  } catch (err) {
    const body = err as { msg?: string }
    error.value = body?.msg || '加载失败'
    overview.value = null
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
