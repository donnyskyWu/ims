<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>直播风险告警</h1>
        <div class="sub">LIVE-003 · 规则命中、处置与 30 分钟升级桩 · 钉钉/短信只记本地桩</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/live/sessions">返回场次</router-link>
      </div>
    </div>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'records' }" data-testid="live-alarm-tab-records" @click="switchTab('records')">告警记录</div>
      <div class="tab" :class="{ on: tab === 'rules' }" data-testid="live-alarm-tab-rules" @click="switchTab('rules')">规则管理</div>
      <div class="tab" :class="{ on: tab === 'stats' }" data-testid="live-alarm-tab-stats" @click="switchTab('stats')">统计看板</div>
    </div>

    <p class="hint" data-testid="live-alarm-banner">钉钉/短信保持本地桩，未外发</p>
    <p v-if="error" class="hint bad" data-testid="live-alarm-error">{{ error }}</p>

    <template v-if="tab === 'records'">
      <form class="qbar" @submit.prevent="loadRecords">
        <input v-model="filters.sessionCode" data-testid="live-alarm-session" placeholder="场次 ID" style="width: 200px" />
        <select v-model="filters.alarmLevel" style="width: 110px" data-testid="live-alarm-level">
          <option value="">全部级别</option>
          <option value="1">L1 提示</option>
          <option value="2">L2 警告</option>
          <option value="3">L3 严重</option>
        </select>
        <select v-model="filters.handleStatus" style="width: 120px" data-testid="live-alarm-status">
          <option value="">全部处置</option>
          <option value="UNHANDLED">未处理</option>
          <option value="CONFIRMED">已确认</option>
          <option value="HANDLED">已处理</option>
          <option value="FALSE_ALARM">误报</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="live-alarm-query">查询</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>告警</th>
                <th>场次</th>
                <th>规则</th>
                <th>级别</th>
                <th>内容</th>
                <th>处置</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!records.length">
                <td colspan="7">
                  <div class="empty" data-testid="live-alarm-empty">
                    <div class="et">{{ filters.sessionCode.trim() ? '该场次暂无风险告警' : '暂无告警' }}</div>
                  </div>
                </td>
              </tr>
              <tr v-for="row in records" v-else :key="row.id" data-testid="live-alarm-row">
                <td class="mono">{{ row.id }}</td>
                <td class="mono">{{ row.sessionCode }}</td>
                <td>{{ row.ruleName }}</td>
                <td>L{{ row.alarmLevel }}</td>
                <td>
                  {{ row.alarmContent }}
                  <span v-if="row.mergeCount > 1" data-testid="live-alarm-merge">×{{ row.mergeCount }}</span>
                  <span v-if="row.escalated" data-testid="live-alarm-escalated">已升级</span>
                  <span data-testid="live-alarm-stub">{{ stubText(row) }}</span>
                </td>
                <td data-testid="live-alarm-handle-state">{{ statusLabel(row.handleStatus) }}</td>
                <td>
                  <button
                    v-if="row.handleStatus === 'UNHANDLED' || row.handleStatus === 'CONFIRMED'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="live-alarm-handle"
                    @click="openHandle(row)"
                  >
                    处置
                  </button>
                  <button class="btn btn-txt btn-sm" type="button" data-testid="live-alarm-detail" @click="openDetail(row)">详情</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'rules'">
      <div class="acts" style="margin: 12px 0">
        <span data-testid="live-alarm-rule-create" @click="openRule()">
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-rule-open" @click.stop="openRule()">新建规则</button>
        </span>
      </div>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>规则</th>
                <th>类型</th>
                <th>摘要</th>
                <th>级别</th>
                <th>通知人</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!rules.length">
                <td colspan="7"><div class="empty"><div class="et">暂无规则</div></div></td>
              </tr>
              <tr v-for="row in rules" v-else :key="row.id" data-testid="live-alarm-rule-row">
                <td>{{ row.ruleName }}</td>
                <td>{{ row.ruleType === 'EVENT' ? '事件' : '阈值' }}</td>
                <td data-testid="live-alarm-rule-summary">{{ row.ruleExprSummary }}</td>
                <td>L{{ row.level }}</td>
                <td>{{ row.notifySummary }}</td>
                <td>{{ row.status === 'ENABLED' ? '启用' : '停用' }}</td>
                <td>
                  <button class="btn btn-txt btn-sm" type="button" @click="openRule(row)">编辑</button>
                  <button class="btn btn-txt btn-sm" type="button" data-testid="live-alarm-rule-toggle" @click="toggleRule(row)">
                    {{ row.status === 'ENABLED' ? '停用' : '启用' }}
                  </button>
                  <button class="btn btn-txt btn-sm" type="button" data-testid="live-alarm-rule-delete" @click="openDelete(row)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="hint" data-testid="live-alarm-rule-hint">ALM-R4 规则保存后下一次读取即新表达式</p>
    </template>

    <template v-else>
      <p v-if="statsEmpty" class="hint" data-testid="live-alarm-stats-empty">暂无风险命中</p>
      <div v-if="stats" class="g4" style="margin-top: 12px">
        <div class="card stat">
          <span class="l">L1 提示</span>
          <div class="n" data-testid="live-alarm-stats-l1">{{ stats.byLevel['1'] }}</div>
        </div>
        <div class="card stat">
          <span class="l">L2 警告</span>
          <div class="n" data-testid="live-alarm-stats-l2">{{ stats.byLevel['2'] }}</div>
        </div>
        <div class="card stat">
          <span class="l">L3 严重</span>
          <div class="n" data-testid="live-alarm-stats-l3"><span data-testid="live-alarm-stats-severe">{{ stats.byLevel['3'] }}</span></div>
        </div>
        <div class="card stat">
          <span class="l">已处理</span>
          <div class="n" data-testid="live-alarm-stats-handled">{{ stats.byHandleStatus.HANDLED }}</div>
          <div class="d">未处理 {{ stats.byHandleStatus.UNHANDLED }}</div>
        </div>
      </div>
      <div v-if="stats" class="tbl-block" style="margin-top: 12px">
        <p class="hint">近 7 日命中（只读）</p>
        <table>
          <thead>
            <tr><th>日期</th><th>合计</th><th>严重</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in stats.trend" :key="item.date" data-testid="live-alarm-trend-row">
              <td class="mono">{{ item.date }}</td>
              <td class="num">{{ item.total }}</td>
              <td class="num">{{ item.severe }}</td>
            </tr>
          </tbody>
        </table>
        <p class="hint" style="margin-top: 8px">规则命中 TOP</p>
        <table>
          <thead><tr><th>规则</th><th>命中次数（含合并）</th></tr></thead>
          <tbody>
            <tr v-if="!stats.byRule.length"><td colspan="2">暂无</td></tr>
            <tr v-for="item in stats.byRule" :key="item.ruleName">
              <td>{{ item.ruleName }}</td>
              <td class="num">{{ item.hitCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-if="ruleOpen" class="drawer-mask" @click.self="ruleOpen = false">
      <div class="drawer on" data-testid="live-alarm-rule-drawer" style="width: 640px">
        <div class="drawer-h">
          <b>{{ editingId ? '编辑规则' : '新建规则' }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="ruleOpen = false">关闭</button>
        </div>
        <p class="hint">保存后立即参与下一次命中扫描（ALM-R4）。通知只记站内。</p>
        <label class="fld"><span>规则名</span><input v-model="ruleForm.ruleName" data-testid="live-alarm-rule-name" maxlength="64" /></label>
        <label class="fld">
          <span>类型</span>
          <select v-model="ruleForm.ruleType" data-testid="live-alarm-rule-type">
            <option value="THRESHOLD">阈值</option>
            <option value="EVENT">事件</option>
          </select>
        </label>
        <label class="fld">
          <span>指标</span>
          <select v-model="ruleForm.metric" data-testid="live-alarm-rule-metric">
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="viewer_count">场观</option>
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="gmv">GMV</option>
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="peak_online">峰值在线</option>
            <option v-if="ruleForm.ruleType === 'EVENT'" value="blacklist">违禁词</option>
          </select>
        </label>
        <label class="fld">
          <span>操作符</span>
          <select v-model="ruleForm.operator" data-testid="live-alarm-rule-op">
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="LT">低于</option>
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="GT">高于</option>
            <option v-if="ruleForm.ruleType === 'THRESHOLD'" value="PCT_DROP">降幅</option>
            <option v-if="ruleForm.ruleType === 'EVENT'" value="HIT">命中</option>
          </select>
        </label>
        <label class="fld">
          <span>阈值</span>
          <input v-model="ruleForm.threshold" type="number" min="0" step="0.01" data-testid="live-alarm-rule-threshold" />
        </label>
        <label class="fld">
          <span>窗口（分钟，可空）</span>
          <input v-model="ruleForm.window" type="number" min="1" max="60" data-testid="live-alarm-rule-window" />
        </label>
        <label class="fld">
          <span>级别</span>
          <select v-model="ruleForm.level" data-testid="live-alarm-rule-level">
            <option value="1">L1 提示</option>
            <option value="2">L2 警告</option>
            <option value="3">L3 严重</option>
          </select>
        </label>
        <p v-if="ruleError" class="hint bad" data-testid="live-alarm-rule-error">{{ ruleError }}</p>
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-rule-save" @click="saveRule">保存</button>
        </div>
      </div>
    </div>

    <div v-if="handleOpen && active" class="drawer-mask" @click.self="handleOpen = false">
      <div class="drawer on" data-testid="live-alarm-handle-drawer" style="width: 560px">
        <div class="drawer-h">
          <b>处置告警</b>
          <button type="button" class="btn btn-sec btn-sm" @click="handleOpen = false">关闭</button>
        </div>
        <p class="hint">{{ active.sessionCode }} · {{ active.ruleName }} · {{ active.alarmContent }}</p>
        <label class="fld">
          <span>处置动作</span>
          <select v-model="handleForm.handleStatus" data-testid="live-alarm-handle-status">
            <option value="CONFIRMED">已确认</option>
            <option value="HANDLED">已处理</option>
            <option value="FALSE_ALARM">误报</option>
          </select>
        </label>
        <label class="fld">
          <span>说明</span>
          <input v-model="handleForm.handleRemark" maxlength="512" data-testid="live-alarm-handle-remark" />
        </label>
        <p v-if="handleError" class="hint bad">{{ handleError }}</p>
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-handle-submit" @click="submitHandle">提交处置</button>
        </div>
      </div>
    </div>

    <div v-if="detailOpen && active" class="drawer-mask" @click.self="detailOpen = false">
      <div class="drawer on" data-testid="live-alarm-detail-drawer" style="width: 560px">
        <div class="drawer-h">
          <b>告警详情</b>
          <button type="button" class="btn btn-sec btn-sm" @click="detailOpen = false">关闭</button>
        </div>
        <div data-testid="live-alarm-detail-body">
          <p>场次 {{ active.sessionCode }}</p>
          <p>规则 {{ active.ruleName }} · L{{ active.alarmLevel }}</p>
          <p>内容 {{ active.alarmContent }}<template v-if="active.mergeCount > 1"> ×{{ active.mergeCount }}</template></p>
          <p>发生 {{ active.occurAt || '—' }}</p>
          <p>处置 {{ statusLabel(active.handleStatus) }} · {{ active.handlerName || '—' }}</p>
          <p>说明 {{ active.handleRemark || '—' }}</p>
          <p class="hint">通知方式：站内记录。不外发钉钉或短信，也不升级推送。</p>
        </div>
      </div>
    </div>

    <div v-if="deleteOpen && deleting" class="drawer-mask" @click.self="deleteOpen = false">
      <div class="drawer on" style="width: 420px">
        <div class="drawer-h"><b>删除规则</b></div>
        <p class="hint">输入 DELETE 确认删除「{{ deleting.ruleName }}」</p>
        <input v-model="deleteText" data-testid="live-alarm-delete-text" />
        <div class="drawer-f">
          <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-delete-submit" @click="submitDelete">
            <span data-testid="live-alarm-delete-confirm">确认删除</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { errorMessage, http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type AlarmRow = {
  id: number
  ruleName: string
  sessionCode: string
  alarmLevel: number
  alarmContent: string
  occurAt: string
  handleStatus: string
  handlerName: string | null
  handleRemark: string
  mergeCount: number
  escalated?: boolean
  notifyChannels?: string[]
}

type RuleRow = {
  id: number
  ruleName: string
  ruleType: string
  ruleExpr: { metric?: string; operator?: string; threshold?: number; window?: number }
  ruleExprSummary: string
  level: number
  notifyUsers: number[]
  notifySummary: string
  status: string
}

type Stats = {
  byLevel: Record<string, number>
  byHandleStatus: Record<string, number>
  trend: Array<{ date: string; total: number; severe: number }>
  byRule: Array<{ ruleName: string; hitCount: number }>
}

const user = useUserStore()
const tab = ref<'records' | 'rules' | 'stats'>('rules')
const error = ref('')
const records = ref<AlarmRow[]>([])
const rules = ref<RuleRow[]>([])
const stats = ref<Stats | null>(null)
const statsEmpty = computed(() => {
  const levels = stats.value?.byLevel
  if (!levels) return false
  return Number(levels['1'] || 0) + Number(levels['2'] || 0) + Number(levels['3'] || 0) === 0
})
const filters = reactive({ sessionCode: '', alarmLevel: '', handleStatus: '' })

const ruleOpen = ref(false)
const editingId = ref<number | null>(null)
const ruleError = ref('')
const ruleForm = reactive({
  ruleName: '',
  ruleType: 'THRESHOLD',
  metric: 'viewer_count',
  operator: 'LT',
  threshold: '1000',
  window: '',
  level: '2',
  status: 'ENABLED',
  notifyUsers: [] as number[],
})

const handleOpen = ref(false)
const detailOpen = ref(false)
const active = ref<AlarmRow | null>(null)
const handleError = ref('')
const handleForm = reactive({ handleStatus: 'HANDLED', handleRemark: '' })

const deleteOpen = ref(false)
const deleting = ref<RuleRow | null>(null)
const deleteText = ref('')

function stubText(row: AlarmRow) {
  const channels = row.notifyChannels || []
  if (channels.includes('DINGTALK_STUB') || channels.includes('SMS_STUB')) {
    const parts = ['站内']
    if (channels.includes('DINGTALK_STUB')) parts.push('钉钉桩')
    if (channels.includes('SMS_STUB')) parts.push('短信桩')
    parts.push('未外发')
    return parts.join(' · ')
  }
  return '站内'
}

function statusLabel(value: string) {
  const map: Record<string, string> = {
    UNHANDLED: '未处理',
    CONFIRMED: '已确认',
    HANDLED: '已处理',
    FALSE_ALARM: '误报',
  }
  return map[value] || value
}

watch(
  () => ruleForm.ruleType,
  (value) => {
    if (value === 'EVENT') {
      ruleForm.metric = 'blacklist'
      ruleForm.operator = 'HIT'
      if (!ruleForm.threshold) ruleForm.threshold = '1'
    } else if (ruleForm.metric === 'blacklist') {
      ruleForm.metric = 'viewer_count'
      ruleForm.operator = 'LT'
    }
  },
)

function switchTab(name: 'records' | 'rules' | 'stats') {
  tab.value = name
  error.value = ''
  if (name === 'rules') loadRules()
  else if (name === 'stats') loadStats()
}

async function loadRecords() {
  error.value = ''
  const params: Record<string, string> = { pageNo: '1', pageSize: '20' }
  if (filters.sessionCode.trim()) params.sessionCode = filters.sessionCode.trim()
  if (filters.alarmLevel) params.alarmLevel = filters.alarmLevel
  if (filters.handleStatus) params.handleStatus = filters.handleStatus
  try {
    const res = await http.get('/live/alarm/records', { params })
    records.value = res.data.data.list || []
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function loadRules() {
  error.value = ''
  try {
    const res = await http.get('/live/alarm/rules', { params: { pageNo: 1, pageSize: 20 } })
    rules.value = res.data.data.list || []
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function loadStats() {
  error.value = ''
  try {
    const res = await http.get('/live/alarm/stats')
    stats.value = res.data.data
  } catch (err) {
    error.value = errorMessage(err)
  }
}

function notifyIds() {
  const current = Number(user.profile?.userId || 0)
  return current > 0 ? [current] : [1]
}

function openRule(row?: RuleRow) {
  ruleError.value = ''
  if (!row) {
    editingId.value = null
    ruleForm.ruleName = ''
    ruleForm.ruleType = 'THRESHOLD'
    ruleForm.metric = 'viewer_count'
    ruleForm.operator = 'LT'
    ruleForm.threshold = '1000'
    ruleForm.window = ''
    ruleForm.level = '2'
    ruleForm.status = 'ENABLED'
    ruleForm.notifyUsers = notifyIds()
  } else {
    editingId.value = row.id
    ruleForm.ruleName = row.ruleName
    ruleForm.ruleType = row.ruleType
    ruleForm.metric = row.ruleExpr.metric || 'viewer_count'
    ruleForm.operator = row.ruleExpr.operator || 'LT'
    ruleForm.threshold = String(row.ruleExpr.threshold ?? 0)
    ruleForm.window = row.ruleExpr.window ? String(row.ruleExpr.window) : ''
    ruleForm.level = String(row.level)
    ruleForm.status = row.status
    ruleForm.notifyUsers = row.notifyUsers?.length ? [...row.notifyUsers] : notifyIds()
  }
  ruleOpen.value = true
}

function rulePayload() {
  const expr: Record<string, unknown> = {
    metric: ruleForm.metric,
    operator: ruleForm.operator,
    threshold: Number(ruleForm.threshold),
  }
  if (String(ruleForm.window).trim()) expr.window = Number(ruleForm.window)
  return {
    ruleName: ruleForm.ruleName.trim(),
    ruleType: ruleForm.ruleType,
    ruleExpr: expr,
    level: Number(ruleForm.level),
    notifyUsers: ruleForm.notifyUsers.length ? ruleForm.notifyUsers : notifyIds(),
    status: ruleForm.status,
  }
}

async function saveRule() {
  ruleError.value = ''
  try {
    if (editingId.value) await http.put(`/live/alarm/rule/${editingId.value}`, rulePayload())
    else await http.post('/live/alarm/rule', rulePayload())
    ruleOpen.value = false
    await loadRules()
  } catch (err) {
    ruleError.value = errorMessage(err)
  }
}

async function toggleRule(row: RuleRow) {
  try {
    await http.put(`/live/alarm/rule/${row.id}`, {
      ruleName: row.ruleName,
      ruleType: row.ruleType,
      ruleExpr: row.ruleExpr,
      level: row.level,
      notifyUsers: row.notifyUsers?.length ? row.notifyUsers : notifyIds(),
      status: row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED',
    })
    await loadRules()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

function openDelete(row: RuleRow) {
  deleting.value = row
  deleteText.value = ''
  deleteOpen.value = true
}

async function submitDelete() {
  if (!deleting.value) return
  try {
    await http.delete(`/live/alarm/rule/${deleting.value.id}`, { params: { confirmText: deleteText.value } })
    deleteOpen.value = false
    await loadRules()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

function openHandle(row: AlarmRow) {
  active.value = row
  handleForm.handleStatus = 'HANDLED'
  handleForm.handleRemark = ''
  handleError.value = ''
  handleOpen.value = true
  detailOpen.value = false
}

function openDetail(row: AlarmRow) {
  active.value = row
  detailOpen.value = true
  handleOpen.value = false
}

async function submitHandle() {
  if (!active.value) return
  handleError.value = ''
  try {
    await http.put(`/live/alarm/record/${active.value.id}/handle`, {
      handleStatus: handleForm.handleStatus,
      handleRemark: handleForm.handleRemark,
    })
    handleOpen.value = false
    await loadRecords()
  } catch (err) {
    handleError.value = errorMessage(err)
  }
}

onMounted(loadRules)
</script>
