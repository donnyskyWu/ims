<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>直播风险告警</h1>
        <div class="sub">LIVE-003 · 30 分钟升级与钉钉/短信均为站内桩，不外发</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/live/sessions">返回场次</router-link>
      </div>
    </div>

    <p v-if="banner" class="hint" data-testid="live-alarm-banner">{{ banner }}</p>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'records' }" data-testid="live-alarm-tab-records" @click="tab = 'records'">
        告警记录
      </div>
      <div class="tab" :class="{ on: tab === 'rules' }" data-testid="live-alarm-tab-rules" @click="openRules">规则管理</div>
      <div class="tab" :class="{ on: tab === 'stats' }" data-testid="live-alarm-tab-stats" @click="openStats">统计看板</div>
    </div>

    <form v-if="tab === 'records'" class="qbar" @submit.prevent="loadRecords">
      <input v-model="filters.sessionCode" placeholder="场次 ID" style="width: 180px" data-testid="live-alarm-filter-session" />
      <select v-model="filters.alarmLevel" style="width: 120px">
        <option value="">全部级别</option>
        <option value="1">L1 提示</option>
        <option value="2">L2 警告</option>
        <option value="3">L3 严重</option>
      </select>
      <select v-model="filters.handleStatus" style="width: 120px">
        <option value="">全部处置</option>
        <option value="UNHANDLED">未处理</option>
        <option value="CONFIRMED">已确认</option>
        <option value="HANDLED">已处理</option>
        <option value="FALSE_ALARM">误报</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div v-if="tab === 'records'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>告警 ID</th>
              <th>场次 ID</th>
              <th>规则</th>
              <th>级别</th>
              <th>内容</th>
              <th>触达</th>
              <th>升级</th>
              <th>处置</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9"><div class="empty"><div class="et">{{ error || '暂无告警' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" data-testid="live-alarm-row">
              <td class="mono">{{ row.id }}</td>
              <td class="mono">{{ row.sessionCode }}</td>
              <td>{{ row.ruleName }}</td>
              <td>{{ levelText(row.alarmLevel) }}</td>
              <td>{{ row.alarmContent }}</td>
              <td data-testid="live-alarm-stub">{{ stubText(row.notifyChannels) }}</td>
              <td>
                <span v-if="row.escalated" data-testid="live-alarm-escalated" style="color: var(--orange)">已升级</span>
                <span v-else>—</span>
              </td>
              <td>{{ statusText(row.handleStatus) }}</td>
              <td>
                <button
                  v-if="row.handleStatus === 'UNHANDLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="live-alarm-handle"
                  @click="openHandle(row)"
                >
                  处置
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <div v-else-if="tab === 'rules'" class="tbl-block">
      <div class="acts" style="margin-bottom: 8px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-rule-create" @click="openRule()">新建规则</button>
        <span v-if="ruleHint" class="hint" data-testid="live-alarm-rule-hint">{{ ruleHint }}</span>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>规则名</th>
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
              <td colspan="7"><div class="empty"><div class="et">{{ ruleError || '暂无规则' }}</div></div></td>
            </tr>
            <tr v-for="rule in rules" :key="rule.id" data-testid="live-alarm-rule-row">
              <td>{{ rule.ruleName }}</td>
              <td>{{ rule.ruleType === 'THRESHOLD' ? '阈值' : '事件' }}</td>
              <td data-testid="live-alarm-rule-summary">{{ rule.ruleExprSummary }}</td>
              <td>{{ levelText(rule.level) }}</td>
              <td>{{ rule.notifySummary }}</td>
              <td>{{ rule.status === 'ENABLED' ? '启用' : '停用' }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" @click="openRule(rule)">编辑</button>
                <button class="btn btn-txt btn-sm" type="button" data-testid="live-alarm-rule-toggle" @click="toggleRule(rule)">
                  {{ rule.status === 'ENABLED' ? '停用' : '启用' }}
                </button>
                <button class="btn btn-txt btn-sm" type="button" data-testid="live-alarm-rule-delete" @click="openDelete(rule)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="tbl-block" data-testid="live-alarm-stats">
      <div class="g4" style="margin-bottom: 12px">
        <div class="card stat"><span class="l">L1</span><div class="n">{{ stats?.byLevel?.['1'] ?? 0 }}</div></div>
        <div class="card stat"><span class="l">L2</span><div class="n">{{ stats?.byLevel?.['2'] ?? 0 }}</div></div>
        <div class="card stat"><span class="l">L3</span><div class="n" data-testid="live-alarm-stats-severe">{{ stats?.byLevel?.['3'] ?? 0 }}</div></div>
        <div class="card stat"><span class="l">未处理</span><div class="n">{{ stats?.byHandleStatus?.UNHANDLED ?? 0 }}</div></div>
      </div>
      <table>
        <thead>
          <tr><th>日期</th><th>告警</th><th>严重</th></tr>
        </thead>
        <tbody>
          <tr v-for="point in stats?.trend || []" :key="point.date">
            <td class="mono">{{ point.date }}</td>
            <td class="num">{{ point.total }}</td>
            <td class="num">{{ point.severe }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <ProtoDrawer :open="handleOpen" title="告警处置" width="560px" @close="handleOpen = false">
      <p class="hint">{{ handling?.ruleName }} · {{ handling?.sessionCode }}</p>
      <p>{{ handling?.alarmContent }}</p>
      <div class="fld">
        <label>处置动作</label>
        <select v-model="handleForm.handleStatus" data-testid="live-alarm-handle-status">
          <option value="CONFIRMED">已确认</option>
          <option value="HANDLED">已处理</option>
          <option value="FALSE_ALARM">误报</option>
        </select>
      </div>
      <div class="fld">
        <label>说明</label>
        <input v-model="handleForm.handleRemark" maxlength="512" data-testid="live-alarm-handle-remark" />
      </div>
      <p v-if="handleError" class="hint bad">{{ handleError }}</p>
      <div class="acts" style="margin-top: 8px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-handle-submit" @click="submitHandle">提交处置</button>
      </div>
    </ProtoDrawer>

    <ProtoDrawer :open="ruleOpen" :title="editingRuleId ? '编辑规则' : '新建规则'" width="640px" @close="ruleOpen = false">
      <div class="fld"><label>规则名</label><input v-model="ruleForm.ruleName" maxlength="64" data-testid="live-alarm-rule-name" /></div>
      <div class="fld">
        <label>类型</label>
        <select v-model="ruleForm.ruleType" data-testid="live-alarm-rule-type">
          <option value="THRESHOLD">阈值</option>
          <option value="EVENT">事件</option>
        </select>
      </div>
      <div class="fld">
        <label>指标</label>
        <select v-model="ruleForm.metric" data-testid="live-alarm-rule-metric">
          <option value="viewer_drop">场观骤降</option>
          <option value="gmv_drop">GMV 异常波动</option>
          <option value="balance_low">话费余额</option>
          <option value="account_status">账号异常状态</option>
          <option value="banned_word">违禁词命中</option>
        </select>
      </div>
      <div class="fld">
        <label>操作符</label>
        <select v-model="ruleForm.operator">
          <option value="PCT_DROP">降幅超过</option>
          <option value="GT">&gt;</option>
          <option value="LT">&lt;</option>
          <option value="HIT">命中</option>
        </select>
      </div>
      <div class="fld">
        <label>阈值</label>
        <input v-model.number="ruleForm.threshold" type="number" min="0" data-testid="live-alarm-rule-threshold" />
      </div>
      <div class="fld">
        <label>窗口（分钟）</label>
        <input v-model.number="ruleForm.window" type="number" min="1" max="60" data-testid="live-alarm-rule-window" />
      </div>
      <div class="fld">
        <label>级别</label>
        <select v-model.number="ruleForm.level">
          <option :value="1">L1 提示</option>
          <option :value="2">L2 警告</option>
          <option :value="3">L3 严重</option>
        </select>
      </div>
      <div class="fld">
        <label>通知人用户 id</label>
        <input v-model.number="ruleForm.notifyUserId" type="number" data-testid="live-alarm-rule-notify" />
      </div>
      <p v-if="ruleError" class="hint bad" data-testid="live-alarm-rule-error">{{ ruleError }}</p>
      <div class="acts" style="margin-top: 8px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-rule-save" @click="saveRule">保存</button>
      </div>
    </ProtoDrawer>

    <ProtoDrawer :open="deleteOpen" title="删除规则" width="360px" @close="deleteOpen = false">
      <p class="hint">输入 DELETE 确认删除「{{ deleting?.ruleName }}」</p>
      <input v-model="deleteText" data-testid="live-alarm-delete-text" />
      <p v-if="ruleError" class="hint bad">{{ ruleError }}</p>
      <div class="acts" style="margin-top: 8px">
        <button class="btn btn-pri btn-sm" type="button" data-testid="live-alarm-delete-confirm" @click="confirmDelete">确认删除</button>
      </div>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

type AlarmRow = {
  id: number
  ruleName: string
  sessionCode: string
  alarmLevel: number
  alarmContent: string
  handleStatus: string
  escalated: boolean
  notifyChannels: string[]
}

type RuleRow = {
  id: number
  ruleName: string
  ruleType: 'THRESHOLD' | 'EVENT'
  ruleExpr: { metric: string; operator: string; threshold: number; window?: number }
  ruleExprSummary: string
  level: number
  notifyUsers: number[]
  notifySummary: string
  status: 'ENABLED' | 'DISABLED'
}

type Stats = {
  byLevel: Record<string, number>
  byHandleStatus: Record<string, number>
  trend: Array<{ date: string; total: number; severe: number }>
}

const tab = ref<'records' | 'rules' | 'stats'>('records')
const loading = ref(false)
const error = ref('')
const rows = ref<AlarmRow[]>([])
const total = ref(0)
const filters = reactive({ sessionCode: '', alarmLevel: '', handleStatus: '' })
const rules = ref<RuleRow[]>([])
const ruleHint = ref('')
const ruleError = ref('')
const stats = ref<Stats | null>(null)
const handleOpen = ref(false)
const handling = ref<AlarmRow | null>(null)
const handleError = ref('')
const handleForm = reactive({ handleStatus: 'HANDLED', handleRemark: '' })
const ruleOpen = ref(false)
const editingRuleId = ref<number | null>(null)
const ruleForm = reactive({
  ruleName: '',
  ruleType: 'THRESHOLD' as 'THRESHOLD' | 'EVENT',
  metric: 'viewer_drop',
  operator: 'PCT_DROP',
  threshold: 30,
  window: 5,
  level: 3,
  notifyUserId: 1,
  status: 'ENABLED' as 'ENABLED' | 'DISABLED',
})
const deleteOpen = ref(false)
const deleting = ref<RuleRow | null>(null)
const deleteText = ref('')

const banner = computed(() => {
  const severe = rows.value.some((row) => row.alarmLevel === 3 && row.handleStatus === 'UNHANDLED')
  if (!severe) return ''
  return '存在未处理的严重告警：1 分钟触达已记为钉钉桩与短信桩，未外发'
})

function levelText(level: number) {
  if (level === 3) return 'L3 严重'
  if (level === 2) return 'L2 警告'
  return 'L1 提示'
}

function statusText(status: string) {
  if (status === 'CONFIRMED') return '已确认'
  if (status === 'HANDLED') return '已处理'
  if (status === 'FALSE_ALARM') return '误报'
  return '未处理'
}

function stubText(channels: string[] | undefined) {
  const list = channels || []
  const parts: string[] = []
  if (list.includes('DINGTALK_STUB')) parts.push('钉钉桩')
  if (list.includes('SMS_STUB')) parts.push('短信桩')
  if (!parts.length) return '站内'
  return `${parts.join('·')}（未外发）`
}

async function loadRecords() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 50 }
    if (filters.sessionCode) params.sessionCode = filters.sessionCode
    if (filters.alarmLevel) params.alarmLevel = Number(filters.alarmLevel)
    if (filters.handleStatus) params.handleStatus = filters.handleStatus
    const res = await http.get('/live/alarm/records', { params })
    rows.value = res.data.data?.list || []
    total.value = res.data.data?.total || 0
  } catch (err) {
    error.value = errorMessage(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  ruleError.value = ''
  try {
    const res = await http.get('/live/alarm/rules', { params: { pageNo: 1, pageSize: 50 } })
    rules.value = res.data.data?.list || []
  } catch (err) {
    ruleError.value = errorMessage(err)
    rules.value = []
  }
}

async function openRules() {
  tab.value = 'rules'
  await loadRules()
}

async function openStats() {
  tab.value = 'stats'
  const res = await http.get('/live/alarm/stats')
  stats.value = res.data.data
}

function openHandle(row: AlarmRow) {
  handling.value = row
  handleForm.handleStatus = 'HANDLED'
  handleForm.handleRemark = '已核对场观回落，站内处置'
  handleError.value = ''
  handleOpen.value = true
}

async function submitHandle() {
  if (!handling.value) return
  handleError.value = ''
  try {
    await http.put(`/live/alarm/record/${handling.value.id}/handle`, {
      handleStatus: handleForm.handleStatus,
      handleRemark: handleForm.handleRemark,
    })
    handleOpen.value = false
    await loadRecords()
  } catch (err) {
    handleError.value = errorMessage(err)
  }
}

function openRule(rule?: RuleRow) {
  ruleError.value = ''
  ruleHint.value = ''
  if (rule) {
    editingRuleId.value = rule.id
    ruleForm.ruleName = rule.ruleName
    ruleForm.ruleType = rule.ruleType
    ruleForm.metric = rule.ruleExpr.metric
    ruleForm.operator = rule.ruleExpr.operator
    ruleForm.threshold = rule.ruleExpr.threshold
    ruleForm.window = rule.ruleExpr.window || 5
    ruleForm.level = rule.level
    ruleForm.notifyUserId = rule.notifyUsers[0] || 1
    ruleForm.status = rule.status
  } else {
    editingRuleId.value = null
    ruleForm.ruleName = '场观骤降'
    ruleForm.ruleType = 'THRESHOLD'
    ruleForm.metric = 'viewer_drop'
    ruleForm.operator = 'PCT_DROP'
    ruleForm.threshold = 30
    ruleForm.window = 5
    ruleForm.level = 3
    ruleForm.notifyUserId = 1
    ruleForm.status = 'ENABLED'
  }
  ruleOpen.value = true
}

function rulePayload() {
  return {
    ruleName: ruleForm.ruleName,
    ruleType: ruleForm.ruleType,
    ruleExpr: {
      metric: ruleForm.metric,
      operator: ruleForm.operator,
      threshold: ruleForm.threshold,
      window: ruleForm.window,
    },
    level: ruleForm.level,
    notifyUsers: [ruleForm.notifyUserId],
    status: ruleForm.status,
  }
}

async function saveRule() {
  ruleError.value = ''
  try {
    if (editingRuleId.value) {
      await http.put(`/live/alarm/rule/${editingRuleId.value}`, rulePayload())
    } else {
      await http.post('/live/alarm/rule', rulePayload())
    }
    ruleOpen.value = false
    ruleHint.value = '已保存，规则立即生效（ALM-R4）'
    await loadRules()
  } catch (err) {
    ruleError.value = errorMessage(err)
  }
}

async function toggleRule(rule: RuleRow) {
  ruleError.value = ''
  try {
    await http.put(`/live/alarm/rule/${rule.id}`, {
      ruleName: rule.ruleName,
      ruleType: rule.ruleType,
      ruleExpr: rule.ruleExpr,
      level: rule.level,
      notifyUsers: rule.notifyUsers,
      status: rule.status === 'ENABLED' ? 'DISABLED' : 'ENABLED',
    })
    ruleHint.value = '已保存，规则立即生效（ALM-R4）'
    await loadRules()
  } catch (err) {
    ruleError.value = errorMessage(err)
  }
}

function openDelete(rule: RuleRow) {
  deleting.value = rule
  deleteText.value = ''
  ruleError.value = ''
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!deleting.value) return
  ruleError.value = ''
  try {
    await http.delete(`/live/alarm/rule/${deleting.value.id}`, { params: { confirmText: deleteText.value } })
    deleteOpen.value = false
    ruleHint.value = '规则已删除'
    await loadRules()
  } catch (err) {
    ruleError.value = errorMessage(err)
  }
}

onMounted(loadRecords)
</script>
