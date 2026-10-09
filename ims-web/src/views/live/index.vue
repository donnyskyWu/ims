<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>直播管理</h1>
        <div class="sub">场次中心：列表→详情 Tab（数据/风控/下播） · 10 LIVE</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openRegister">新建场次登记</button>
        <button class="btn btn-sec" type="button" data-testid="live-supplement-open" @click="openSupplement">历史补录</button>
        <button class="btn btn-sec" type="button" data-testid="live-ledger-export" :disabled="exporting" @click="exportLedger">导出</button>
      </div>
    </div>
    <p v-if="exportNote" class="hint" data-testid="live-export-note">{{ exportNote }}</p>
    <p v-if="exportError" class="hint bad" data-testid="live-export-error">{{ exportError }}</p>
    <p v-if="hint" class="hint" style="margin-bottom: 8px">{{ hint }}</p>
    <div class="tabs">
      <div class="tab" :class="{ on: view === 'sessions' }" data-testid="live-view-sessions" @click="view = 'sessions'">场次列表</div>
      <div class="tab" :class="{ on: view === 'pending' }" data-testid="live-view-pending" @click="openPending">待录入督办</div>
    </div>
    <form v-if="view === 'sessions'" class="qbar" @submit.prevent="loadList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 160px" />
      <select v-model="query.sessionStatus" style="width: 100px">
        <option value="">全部状态</option>
        <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetQuery">重置</button>
    </form>
    <div v-if="view === 'sessions'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>账号</th>
              <th>主题</th>
              <th>平台</th>
              <th>计划开播</th>
              <th>风险级别</th>
              <th>场次状态</th>
              <th>Football</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty">
                  <div class="et">{{ error || '暂无场次' }}</div>
                  <div class="es">登记后生成 19 位场次 ID；直播数据 Tab 只读 live_room。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.sessionCode">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">
                {{ row.sessionCode }}
                <span v-if="row.isSupplement" data-testid="live-supplement-tag">补录</span>
              </td>
              <td class="mono" style="font-size: 12px">{{ row.accountNo }}</td>
              <td>{{ row.topic }}</td>
              <td>{{ row.platform }}</td>
              <td class="num" style="font-size: 12px">{{ row.planStartTime }}</td>
              <td>{{ row.riskLevel || '—' }}</td>
              <td>{{ row.sessionStatus }}</td>
              <td>{{ syncLabel(row.footballSyncStatus) }}</td>
              <td><button class="btn btn-sec btn-sm" type="button" @click="openDetail(row)">详情</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
      </div>
    </div>
    <div v-else class="tbl-block" data-testid="live-pending-panel">
      <p v-if="pendingHint" class="hint bad" data-testid="live-overdue-hint">{{ pendingHint }}</p>
      <form class="qbar" @submit.prevent="loadPending">
        <label class="hint">
          <input v-model="overdueOnly" type="checkbox" data-testid="live-overdue-only" />
          仅看超过 24 小时
        </label>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit" data-testid="live-pending-query">查询</button>
      </form>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>场次 ID</th>
              <th>主题</th>
              <th>下播时间</th>
              <th>责任人</th>
              <th>超时小时</th>
              <th>督办</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!pendingRows.length">
              <td colspan="6"><div class="empty"><div class="et">暂无待录入场次</div></div></td>
            </tr>
            <tr v-for="row in pendingRows" v-else :key="row.sessionCode" data-testid="live-pending-row">
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">{{ row.sessionCode }}</td>
              <td>{{ row.topic }}</td>
              <td class="num" style="font-size: 12px">{{ row.endedAt || '—' }}</td>
              <td>{{ row.responsibleUserName || '—' }}</td>
              <td class="num" data-testid="live-pending-hours">{{ row.overdueHours }}</td>
              <td>
                <span v-if="row.overdue" data-testid="live-pending-overdue" style="color: var(--red)">超 24h</span>
                <span v-else>未超时</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ProtoDrawer :open="registerOpen" title="开播登记" width="720px" @close="registerOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>平台账号 id *</label>
          <input v-model.number="reg.accountId" type="number" />
        </div>
        <div class="fld">
          <label>实名人 id *</label>
          <input v-model.number="reg.realnamePersonId" type="number" />
        </div>
        <div class="fld">
          <label>手机设备 id *</label>
          <input v-model.number="reg.deviceId" type="number" />
        </div>
        <div class="fld">
          <label>Football room id（可选）</label>
          <input v-model="reg.footballRoomId" placeholder="live_room.id" />
        </div>
        <div class="fld">
          <label>主题 *</label>
          <input v-model="reg.topic" />
        </div>
        <div class="fld">
          <label>计划开播 *</label>
          <input v-model="reg.planStartTime" placeholder="2026-10-06T20:00:00+08:00" />
        </div>
      </div>
      <div v-if="registerError" class="hint bad" data-testid="live-register-error">{{ registerError }}</div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="registerOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="submitRegister">提交登记</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="supplementOpen" title="历史补录" width="720px" @close="supplementOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>平台账号 id *</label>
          <input v-model.number="sup.accountId" type="number" data-testid="live-supplement-account" />
        </div>
        <div class="fld">
          <label>实名人 id *</label>
          <input v-model.number="sup.realnamePersonId" type="number" data-testid="live-supplement-person" />
        </div>
        <div class="fld">
          <label>手机设备 id *</label>
          <input v-model.number="sup.deviceId" type="number" data-testid="live-supplement-device" />
        </div>
        <div class="fld">
          <label>主题 *</label>
          <input v-model="sup.topic" data-testid="live-supplement-topic" />
        </div>
        <div class="fld">
          <label>计划开播 *</label>
          <input v-model="sup.planStartTime" data-testid="live-supplement-plan" />
        </div>
        <div class="fld">
          <label>补录说明 *</label>
          <input v-model="sup.supplementReason" data-testid="live-supplement-reason" maxlength="256" />
        </div>
        <div class="fld">
          <label>GMV</label>
          <input v-model.number="sup.gmv" type="number" step="0.01" data-testid="live-supplement-gmv" />
        </div>
      </div>
      <div v-if="supplementError" class="hint bad" data-testid="live-supplement-error">{{ supplementError }}</div>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="supplementOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="live-supplement-submit" @click="submitSupplement">提交补录</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" :title="detailTitle" width="90%" @close="detailOpen = false">
      <div v-if="detail" class="tabs" data-testid="live-ledger-detail">
        <div v-for="t in tabs" :key="t" class="tab" :class="{ on: tab === t }" @click="switchTab(t)">{{ t }}</div>
      </div>
      <div v-if="detail && tab === '基本信息'" class="tbl-block" style="margin-top: 12px">
        <table class="ipg-info-grid">
          <tbody>
            <tr v-for="line in basicLines" :key="line.k"><td class="lbl">{{ line.k }}</td><td>{{ line.v }}</td></tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="detail && tab === '直播数据'" class="tbl-block" style="margin-top: 12px">
        <p class="hint">GMV / 峰值 / 涨粉等由下播录入承载；此处只读 live_room。</p>
        <div class="acts" style="margin: 8px 0">
          <button class="btn btn-pri btn-sm" type="button" :disabled="!detail.footballRoomId" @click="doSync">从 Football 同步</button>
        </div>
        <table v-if="metrics" class="ipg-info-grid">
          <tbody>
            <tr><td class="lbl">同步态</td><td>{{ syncLabel(metrics.syncStatus) }}</td></tr>
            <tr><td class="lbl">roomId</td><td>{{ metrics.footballRoomId || '—' }}</td></tr>
            <template v-if="metrics.footballRoomBasic">
              <tr><td class="lbl">直播名称</td><td>{{ metrics.footballRoomBasic.liveName }}</td></tr>
              <tr><td class="lbl">作者</td><td>{{ metrics.footballRoomBasic.authorNickname }}</td></tr>
              <tr><td class="lbl">观看人数</td><td>{{ metrics.footballRoomBasic.viewerCount }}</td></tr>
              <tr><td class="lbl">点赞</td><td>{{ metrics.footballRoomBasic.likeCount }}</td></tr>
              <tr><td class="lbl">预约</td><td>{{ metrics.footballRoomBasic.reservationCount }}</td></tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-else-if="detail && tab === '风控登记'" class="tbl-block" style="margin-top: 12px">
        <div class="acts" style="margin-bottom: 8px">
          <button class="btn btn-pri btn-sm" type="button" @click="doRisk">执行风控</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="live-start-btn" @click="doStart">确认开播</button>
        </div>
        <p v-if="actionError" class="hint bad" data-testid="live-action-error">{{ actionError }}</p>
        <p data-testid="live-session-status">风险分 {{ detail.riskScore ?? '—' }} · {{ detail.riskLevel || '—' }} · 状态 {{ detail.sessionStatus }}</p>
        <p v-if="riskConclusion" data-testid="live-risk-conclusion">{{ riskConclusion }}</p>
        <p v-if="detail.approverName" data-testid="live-approver">审批人 {{ detail.approverName }}</p>
        <div v-if="showYellowApprove" class="formrow one" style="margin-top: 8px">
          <div class="fld">
            <label>审批意见</label>
            <input v-model="approveComment" data-testid="live-approve-comment" maxlength="512" />
          </div>
          <div class="acts">
            <button class="btn btn-pri btn-sm" type="button" data-testid="live-approve-pass" @click="doApprove(true)">通过放行</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="live-approve-reject" @click="doApprove(false)">拒绝整改</button>
          </div>
        </div>
        <p v-if="detail.isSupplement" data-testid="live-supplement-reason-text">补录说明：{{ detail.supplementReason || '—' }}</p>
        <div v-if="showSupplementApprove" class="formrow one" style="margin-top: 8px">
          <div class="fld">
            <label>补录审批意见</label>
            <input v-model="supplementComment" data-testid="live-supplement-comment" maxlength="512" />
          </div>
          <div class="acts">
            <button class="btn btn-pri btn-sm" type="button" data-testid="live-supplement-pass" @click="doSupplementApprove(true)">通过补录</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="live-supplement-reject" @click="doSupplementApprove(false)">拒绝补录</button>
          </div>
        </div>
        <table v-if="detail.riskCheckResults?.length">
          <thead><tr><th>检查项</th><th>结果</th><th>权重分</th></tr></thead>
          <tbody>
            <tr v-for="c in detail.riskCheckResults" :key="c.id">
              <td>{{ c.checkItem }}</td><td>{{ c.checkResult }}</td><td>{{ c.scoreWeight }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="detail && tab === '下播与 GMV'" class="tbl-block" style="margin-top: 12px">
        <p v-if="financeView" class="hint" data-testid="live-report-finance-scope">财务字段：仅 GMV 与成本</p>
        <p v-if="report?.fieldScope === 'MASKED'" class="hint" data-testid="live-report-cost-masked">成本已脱敏</p>
        <div v-if="report" class="hint" data-testid="live-report-headline">
          录入状态 {{ report.entryStatus || '—' }} · GMV ¥{{ displayMoney(report.gmv) }}
          · 客单价 {{ displayMoney(report.avgOrderValue) }} · ROAS <span data-testid="live-report-roas">{{ displayMoney(report.roas) }}</span>
        </div>
        <div class="formrow one">
          <div v-if="showOpsFields" class="fld"><label>实际开始</label><input v-model="reportForm.actualStart" data-testid="live-report-start" :readonly="reportLocked && !correcting" /></div>
          <div v-if="showOpsFields" class="fld"><label>实际结束</label><input v-model="reportForm.actualEnd" data-testid="live-report-end" :readonly="reportLocked && !correcting" /></div>
          <div class="fld"><label>GMV</label><input v-model="reportForm.gmv" type="number" step="0.01" data-testid="live-report-gmv" :readonly="financeView || (reportLocked && !correcting)" :style="fieldMissing('gmv') ? 'border-color: var(--red)' : ''" /></div>
          <div v-if="showOpsFields" class="fld"><label>订单数</label><input v-model="reportForm.orderCount" type="number" data-testid="live-report-orders" :readonly="reportLocked && !correcting" /></div>
          <div v-if="showOpsFields" class="fld"><label>观看人数</label><input v-model="reportForm.viewerCount" type="number" data-testid="live-report-viewers" :readonly="reportLocked && !correcting" /></div>
          <div v-if="showOpsFields" class="fld"><label>峰值在线</label><input v-model="reportForm.peakOnline" type="number" data-testid="live-report-peak" :readonly="reportLocked && !correcting" /></div>
          <div v-if="showOpsFields" class="fld"><label>涨粉</label><input v-model="reportForm.newFans" type="number" data-testid="live-report-fans" :readonly="reportLocked && !correcting" /></div>
          <div class="fld"><label>退款</label><input v-model="reportForm.refundAmount" type="number" step="0.01" data-testid="live-report-refund" :readonly="financeView || (reportLocked && !correcting)" /></div>
          <div class="fld"><label>投放成本</label><input v-model="reportForm.adCost" data-testid="live-report-ad" :readonly="financeView || report?.fieldScope === 'MASKED' || (reportLocked && !correcting)" /></div>
          <div v-if="showCostEditor" class="fld">
            <label>成本明细</label>
            <select v-model="costDraft.costType" data-testid="live-cost-type">
              <option value="AD">投放</option>
              <option value="RECHARGE">冲话费</option>
              <option value="GIFT">打赏</option>
              <option value="SAMPLE">样品</option>
            </select>
            <input v-model="costDraft.amount" type="number" step="0.01" placeholder="金额" data-testid="live-cost-amount" />
          </div>
          <div v-if="correcting" class="fld">
            <label>更正原因 *</label>
            <input v-model="correctionReason" maxlength="512" data-testid="live-report-correction-reason" />
          </div>
        </div>
        <ul v-if="costLines.length" data-testid="live-cost-details">
          <li v-for="(item, index) in costLines" :key="index">{{ costLabel(item.costType) }} {{ displayMoney(item.amount) }}</li>
        </ul>
        <p v-if="reportError" class="hint bad" data-testid="live-report-error">{{ reportError }}</p>
        <p v-if="correctionTrace" class="hint" data-testid="live-correction-trace">
          更正单 {{ correctionTrace.correctionId }} · GMV {{ correctionTrace.before?.gmv }} → {{ correctionTrace.after?.gmv }}
        </p>
        <div v-if="!financeView" class="acts" style="margin-top: 8px">
          <button v-if="!reportLocked" class="btn btn-pri btn-sm" type="button" data-testid="live-report-submit" @click="submitReport">提交下播</button>
          <button
            v-if="report && report.entryStatus === 'SUBMITTED'"
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="live-report-confirm"
            @click="confirmReport"
          >
            核准下播
          </button>
          <button v-if="reportLocked && !correcting" class="btn btn-sec btn-sm" type="button" data-testid="live-report-direct-save" @click="directSave">保存修改</button>
          <button v-if="reportLocked && !correcting" class="btn btn-sec btn-sm" type="button" data-testid="live-report-correction-open" @click="openCorrection">更正</button>
          <button v-if="correcting" class="btn btn-pri btn-sm" type="button" data-testid="live-report-correction-submit" @click="submitCorrection">提交更正单</button>
        </div>
      </div>
      <div v-else-if="detail && tab === '关联'" class="tbl-block" style="margin-top: 12px">
        <p class="hint">告警摘要（契约 GET /live/alarm/records）</p>
        <table v-if="alarms.length">
          <thead><tr><th>规则</th><th>级别</th><th>内容</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="a in alarms" :key="a.id">
              <td>{{ a.ruleName }}</td><td>{{ a.alarmLevel }}</td><td>{{ a.alarmContent }}</td><td>{{ a.handleStatus }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty"><div class="et">暂无告警记录</div></div>
      </div>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { errorMessage, http } from '../../api/http'

async function apiGet(url: string, params?: Record<string, unknown>) {
  const res = await http.get(url, { params })
  return res.data.data
}

async function apiPost(url: string, body?: unknown, config?: { headers?: Record<string, string> }) {
  const res = await http.post(url, body ?? {}, config)
  return res.data.data
}

async function apiPut(url: string, body?: unknown) {
  const res = await http.put(url, body ?? {})
  return res.data.data
}

const route = useRoute()
const loading = ref(false)
const error = ref('')
const hint = ref('')
const exporting = ref(false)
const exportNote = ref('')
const exportError = ref('')
const rows = ref<any[]>([])
const total = ref(0)
const view = ref<'sessions' | 'pending'>('sessions')
const pendingRows = ref<any[]>([])
const pendingHint = ref('')
const overdueOnly = ref(false)
const reportError = ref('')
const reportMissing = ref<string[]>([])
const correcting = ref(false)
const correctionReason = ref('')
const correctionTrace = ref<any>(null)
const query = reactive({ sessionCode: '', sessionStatus: '' })
const statusOptions = [
  { value: 'PENDING_RISK_CHECK', label: '待风控' },
  { value: 'APPROVED', label: '已放行' },
  { value: 'LIVE', label: '直播中' },
  { value: 'ENDED', label: '已下播' },
  { value: 'CANCELLED', label: '已取消' },
]

const registerOpen = ref(false)
const registerError = ref('')
const actionError = ref('')
const approveComment = ref('')
const supplementOpen = ref(false)
const supplementError = ref('')
const supplementComment = ref('')
const sup = reactive({
  accountId: 0,
  realnamePersonId: 0,
  deviceId: 0,
  topic: '历史场次补录',
  planStartTime: '2020-01-15T20:00:00+08:00',
  supplementReason: '',
  gmv: 100,
})
const reg = reactive({
  accountId: 0,
  realnamePersonId: 0,
  deviceId: 0,
  footballRoomId: '',
  topic: 'IMS 直播专场',
  planStartTime: '2026-10-06T20:00:00+08:00',
})
let clientToken = ''

const detailOpen = ref(false)
const detail = ref<any>(null)
const metrics = ref<any>(null)
const report = ref<any>(null)
const alarms = ref<any[]>([])
const tab = ref('基本信息')
const tabs = ['基本信息', '直播数据', '风控登记', '下播与 GMV', '关联']
const reportForm = reactive({
  actualStart: '2026-10-06T20:00:00+08:00',
  actualEnd: '2026-10-06T22:00:00+08:00',
  gmv: '1000',
  orderCount: '10',
  viewerCount: '500',
  peakOnline: '80',
  newFans: '20',
  refundAmount: '0',
  adCost: '100',
})
const costLines = ref<{ costType: string; amount: unknown; remark?: string }[]>([])
const costDraft = reactive({ costType: 'GIFT', amount: '' })

const reportLocked = computed(() => !!report.value && report.value.entryStatus !== 'DRAFT')
const financeView = computed(() => report.value?.fieldScope === 'FINANCE')
const showOpsFields = computed(() => !financeView.value)
const showCostEditor = computed(() => !financeView.value && (!reportLocked.value || correcting.value))

function displayMoney(value: unknown) {
  if (value === '***') return '***'
  if (value === '' || value === null || value === undefined) return '—'
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toFixed(2) : '—'
}

function costLabel(kind: string) {
  const map: Record<string, string> = { AD: '投放', RECHARGE: '冲话费', GIFT: '打赏', SAMPLE: '样品' }
  return map[kind] || kind || '成本'
}

function resetReportForm() {
  reportForm.actualStart = '2026-10-06T20:00:00+08:00'
  reportForm.actualEnd = '2026-10-06T22:00:00+08:00'
  reportForm.gmv = '1000'
  reportForm.orderCount = '10'
  reportForm.viewerCount = '500'
  reportForm.peakOnline = '80'
  reportForm.newFans = '20'
  reportForm.refundAmount = '0'
  reportForm.adCost = '100'
}

function applyReport(data: Record<string, unknown> | null) {
  if (!data) {
    resetReportForm()
    costLines.value = []
    costDraft.amount = ''
    return
  }
  reportForm.actualStart = String(data.actualStart || '')
  reportForm.actualEnd = String(data.actualEnd || '')
  reportForm.gmv = String(data.gmv ?? '')
  reportForm.orderCount = String(data.orderCount ?? '')
  reportForm.viewerCount = String(data.viewerCount ?? '')
  reportForm.peakOnline = String(data.peakOnline ?? '')
  reportForm.newFans = String(data.newFans ?? '')
  reportForm.refundAmount = String(data.refundAmount ?? '')
  reportForm.adCost = data.adCost === '***' ? '***' : String(data.adCost ?? '')
  const details = data.costDetails
  costLines.value = Array.isArray(details)
    ? details.map((item) => ({
        costType: String((item as { costType?: string }).costType || ''),
        amount: (item as { amount?: unknown }).amount,
        remark: String((item as { remark?: string }).remark || ''),
      }))
    : []
  costDraft.amount = ''
}

function nullableNumber(value: unknown) {
  if (value === '' || value === null || value === undefined) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function reportPayload() {
  const payload: Record<string, unknown> = {
    actualStart: reportForm.actualStart.trim() || null,
    actualEnd: reportForm.actualEnd.trim() || null,
    gmv: nullableNumber(reportForm.gmv),
    refundAmount: nullableNumber(reportForm.refundAmount),
    orderCount: nullableNumber(reportForm.orderCount),
    viewerCount: nullableNumber(reportForm.viewerCount),
    peakOnline: nullableNumber(reportForm.peakOnline),
    newFans: nullableNumber(reportForm.newFans),
    adCost: reportForm.adCost === '***' ? null : nullableNumber(reportForm.adCost),
  }
  const details = costLines.value
    .filter((item) => item.amount !== '***')
    .map((item) => ({
      costType: item.costType,
      amount: nullableNumber(item.amount),
      remark: item.remark || undefined,
    }))
  if (String(costDraft.amount).trim() !== '') {
    details.push({ costType: costDraft.costType, amount: nullableNumber(costDraft.amount), remark: undefined })
  }
  if (details.length) payload.costDetails = details
  return payload
}

function fieldMissing(key: string) {
  return reportMissing.value.includes(key)
}

const detailTitle = computed(() => (detail.value ? `场次 ${detail.value.sessionCode}` : '场次详情'))

function syncLabel(v: string | undefined) {
  const map: Record<string, string> = {
    UNLINKED: '未关联',
    PENDING: '待同步',
    SYNCED: '已同步',
    FAILED: '同步失败',
  }
  return map[v || ''] || v || '—'
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (query.sessionCode) params.sessionCode = query.sessionCode
    if (query.sessionStatus) params.sessionStatus = query.sessionStatus
    const res = await apiGet('/live/sessions/list', params)
    rows.value = res.list || []
    total.value = res.total || 0
  } catch (e: unknown) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.sessionCode = ''
  query.sessionStatus = ''
  loadList()
}

function unwrapError(error: unknown) {
  if (error && typeof error === 'object' && 'response' in error) {
    const data = (error as { response?: { data?: unknown } }).response?.data
    if (data && typeof data === 'object') return data
  }
  return error
}

function bizError(error: unknown) {
  const body = unwrapError(error) as { code?: number; msg?: string }
  if (body && typeof body === 'object' && typeof body.code === 'number' && body.code !== 0) {
    return `${body.code} ${body.msg || ''}`.trim()
  }
  return errorMessage(error)
}

async function exportLedger() {
  exporting.value = true
  exportNote.value = ''
  exportError.value = ''
  try {
    const params: Record<string, string> = {}
    if (query.sessionCode) params.sessionCode = query.sessionCode
    if (query.sessionStatus) params.sessionStatus = query.sessionStatus
    const res = await http.get('/live/ledger/export', { params })
    const data = res.data.data || {}
    exportNote.value = data.message || '导出任务已提交'
    const downloadUrl = String(data.downloadUrl || '')
    if (!downloadUrl) return
    const token = localStorage.getItem('ims_access')
    const fileRes = await fetch(downloadUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!fileRes.ok) {
      let body: unknown = {}
      try {
        body = await fileRes.json()
      } catch {
        body = {}
      }
      throw body
    }
    const blob = await fileRes.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = String(data.fileName || 'live_ledger.xlsx')
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(a.href)
  } catch (e: unknown) {
    exportNote.value = ''
    exportError.value = bizError(e)
  } finally {
    exporting.value = false
  }
}

function openRegister() {
  clientToken = crypto.randomUUID()
  registerError.value = ''
  registerOpen.value = true
}

async function submitRegister() {
  hint.value = ''
  registerError.value = ''
  try {
    const body = {
      accountId: reg.accountId,
      realnamePersonId: reg.realnamePersonId,
      responsibleUserId: 1,
      deviceAssetIds: [reg.deviceId],
      platform: 'DOUYIN',
      topic: reg.topic,
      planStartTime: reg.planStartTime,
      planEndTime: '',
      footballRoomId: reg.footballRoomId || undefined,
    }
    const data = await apiPost('/live/register', body, { headers: { clientToken } })
    registerOpen.value = false
    hint.value = `已登记 ${data.sessionCode}`
    await loadList()
    openDetail(data)
    tab.value = '风控登记'
  } catch (e: unknown) {
    registerError.value = bizError(e)
    hint.value = registerError.value
  }
}

const basicLines = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    { k: '场次 ID', v: d.sessionCode },
    { k: '账号', v: d.accountNo },
    { k: '实名人', v: d.realnameName },
    { k: '责任人', v: d.responsibleUserName },
    { k: '主题', v: d.topic },
    { k: '状态', v: d.sessionStatus },
    { k: '补录', v: d.isSupplement ? d.supplementReason || '待审批' : '否' },
    { k: 'Football room', v: d.footballRoomId || '—' },
  ]
})

const riskConclusion = computed(() => {
  const level = detail.value?.riskLevel as string | undefined
  if (level === 'GREEN') return '绿色自动放行'
  if (level === 'YELLOW') return '黄色待审批'
  if (level === 'RED') return '红色禁止开播'
  return ''
})

const showYellowApprove = computed(
  () => detail.value?.riskLevel === 'YELLOW' && detail.value?.sessionStatus === 'PENDING_RISK_CHECK',
)

const showSupplementApprove = computed(
  () => !!detail.value?.isSupplement && !detail.value?.approverUserId,
)

async function openDetail(row: any) {
  detailOpen.value = true
  tab.value = '基本信息'
  reportError.value = ''
  reportMissing.value = []
  correcting.value = false
  correctionReason.value = ''
  correctionTrace.value = null
  const code = row.sessionCode
  detail.value = await apiGet(`/live/sessions/${code}`)
  metrics.value = detail.value.metricsSnapshot || (await apiGet(`/live/sessions/${code}/metrics`))
  report.value = detail.value.report || (await apiGet(`/live/report/${code}`))
  applyReport(report.value)
  const alarmRes = await apiGet('/live/alarm/records', { sessionCode: code, pageNo: 1, pageSize: 10 })
  alarms.value = alarmRes.list || []
}

async function openPending() {
  view.value = 'pending'
  await loadPending()
}

async function loadPending() {
  pendingHint.value = ''
  try {
    const res = await http.get('/live/report/pending', {
      params: {
        pageNo: 1,
        pageSize: 20,
        overdueOnly: overdueOnly.value ? true : undefined,
      },
    })
    pendingRows.value = res.data.data?.list || []
  } catch (error: unknown) {
    const body = error as { code?: number; msg?: string; data?: { list?: unknown[] } }
    if (body?.code === 1048) {
      pendingRows.value = body.data?.list || []
      pendingHint.value = `1048 ${body.msg || '24小时录入超时督办'}`
      return
    }
    pendingRows.value = []
    pendingHint.value = bizError(error)
  }
}

async function switchTab(name: string) {
  tab.value = name
  if (!detail.value) return
  const code = detail.value.sessionCode
  if (name === '直播数据') {
    metrics.value = await apiGet(`/live/sessions/${code}/metrics`)
  }
  if (name === '下播与 GMV' && !report.value) {
    report.value = await apiGet(`/live/report/${code}`)
  }
  if (name === '关联') {
    const alarmRes = await apiGet('/live/alarm/records', { sessionCode: code, pageNo: 1, pageSize: 10 })
    alarms.value = alarmRes.list || []
  }
}

async function doSync() {
  if (!detail.value) return
  metrics.value = await apiPost(`/live/sessions/${detail.value.sessionCode}/football-sync`, {})
  hint.value = '已同步 live_room'
}

async function refreshDetail() {
  if (!detail.value) return
  detail.value = await apiGet(`/live/sessions/${detail.value.sessionCode}`)
}

async function doRisk() {
  if (!detail.value) return
  actionError.value = ''
  try {
    await apiPost(`/live/register/${detail.value.sessionCode}/risk-check`, {})
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
}

async function doStart() {
  if (!detail.value) return
  actionError.value = ''
  try {
    await apiPut(`/live/register/${detail.value.sessionCode}/start`, {})
    hint.value = '已确认开播'
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
}

async function doApprove(pass: boolean) {
  if (!detail.value) return
  actionError.value = ''
  if (pass && !approveComment.value.trim()) {
    actionError.value = '审批意见必填'
    return
  }
  try {
    await apiPut(`/live/register/${detail.value.sessionCode}/approve`, {
      approve: pass,
      comment: approveComment.value.trim(),
    })
    hint.value = pass ? '黄级已放行' : '已拒绝，请整改'
    approveComment.value = ''
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
}

function openSupplement() {
  supplementError.value = ''
  sup.supplementReason = ''
  supplementOpen.value = true
}

async function submitSupplement() {
  supplementError.value = ''
  try {
    const data = await apiPost('/live/ledger/supplement', {
      sessionCreate: {
        accountId: sup.accountId,
        realnamePersonId: sup.realnamePersonId,
        responsibleUserId: 1,
        deviceAssetIds: [sup.deviceId],
        platform: 'DOUYIN',
        topic: sup.topic,
        planStartTime: sup.planStartTime,
        planEndTime: '',
      },
      sessionReport: {
        actualStart: sup.planStartTime,
        actualEnd: '2020-01-15T22:00:00+08:00',
        durationMinutes: 120,
        gmv: sup.gmv,
        refundAmount: 0,
        orderCount: 1,
        viewerCount: 10,
        peakOnline: 5,
        newFans: 1,
        adCost: 0,
      },
      supplementReason: sup.supplementReason,
    })
    supplementOpen.value = false
    hint.value = `补录已提交 ${data.sessionCode}`
    await loadList()
    openDetail(data)
    tab.value = '风控登记'
  } catch (e: unknown) {
    supplementError.value = bizError(e)
    hint.value = supplementError.value
  }
}

async function doSupplementApprove(pass: boolean) {
  if (!detail.value) return
  actionError.value = ''
  if (pass && !supplementComment.value.trim()) {
    actionError.value = '审批意见必填'
    return
  }
  try {
    await apiPut(`/live/ledger/supplement/${detail.value.id}/approve`, {
      approve: pass,
      comment: supplementComment.value.trim(),
    })
    hint.value = pass ? '补录已审批入库' : '补录已退回'
    supplementComment.value = ''
  } catch (e: unknown) {
    actionError.value = bizError(e)
    hint.value = actionError.value
  }
  await refreshDetail()
  await loadList()
}

async function submitReport() {
  if (!detail.value) return
  reportError.value = ''
  reportMissing.value = []
  try {
    report.value = await apiPost(`/live/report/${detail.value.sessionCode}`, reportPayload())
    applyReport(report.value)
    correcting.value = false
    hint.value = '下播数据已提交'
    await refreshDetail()
    await loadList()
  } catch (e: unknown) {
    const body = e as { data?: { missing?: string[] } }
    reportMissing.value = body.data?.missing || []
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

async function directSave() {
  if (!detail.value) return
  reportError.value = ''
  try {
    await apiPut(`/live/report/${detail.value.sessionCode}`, reportPayload())
    hint.value = '草稿已保存'
  } catch (e: unknown) {
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

function openCorrection() {
  correcting.value = true
  correctionReason.value = ''
  reportError.value = ''
}

async function submitCorrection() {
  if (!detail.value) return
  reportError.value = ''
  try {
    const data = await apiPost(`/live/report/${detail.value.sessionCode}/correction`, {
      ...reportPayload(),
      correctionReason: correctionReason.value.trim(),
    })
    correctionTrace.value = data
    correcting.value = false
    report.value = await apiGet(`/live/report/${detail.value.sessionCode}`)
    applyReport(report.value)
    hint.value = `更正单 ${data.correctionId} 已留痕`
  } catch (e: unknown) {
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

async function confirmReport() {
  if (!detail.value) return
  reportError.value = ''
  try {
    await apiPut(`/live/report/${detail.value.sessionCode}/confirm`, {})
    report.value = await apiGet(`/live/report/${detail.value.sessionCode}`)
    applyReport(report.value)
    hint.value = '下播数据已核准'
    await loadList()
  } catch (e: unknown) {
    reportError.value = bizError(e)
    hint.value = reportError.value
  }
}

onMounted(async () => {
  const code = typeof route.query.sessionCode === 'string' ? route.query.sessionCode.trim() : ''
  if (code) query.sessionCode = code
  await loadList()
  if (code) await openDetail({ sessionCode: code })
})
</script>
