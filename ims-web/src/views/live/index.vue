<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>直播管理</h1>
        <div class="sub">场次中心：列表→详情 Tab（数据/风控/下播） · 10 LIVE</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" @click="openRegister">新建场次登记</button>
        <button class="btn btn-sec" type="button" disabled>导出</button>
      </div>
    </div>
    <p v-if="hint" class="hint" style="margin-bottom: 8px">{{ hint }}</p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="query.sessionCode" placeholder="场次 ID" style="width: 160px" />
      <select v-model="query.sessionStatus" style="width: 100px">
        <option value="">全部状态</option>
        <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetQuery">重置</button>
    </form>
    <div class="tbl-block">
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
              <td class="mono num" style="color: var(--blue); cursor: pointer" @click="openDetail(row)">{{ row.sessionCode }}</td>
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
      <template #footer>
        <button class="btn btn-sec" type="button" @click="registerOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="submitRegister">提交登记</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" :title="detailTitle" width="90%" @close="detailOpen = false">
      <div v-if="detail" class="tabs">
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
          <button class="btn btn-sec btn-sm" type="button" @click="doStart">确认开播</button>
        </div>
        <p>风险分 {{ detail.riskScore ?? '—' }} · {{ detail.riskLevel || '—' }} · 状态 {{ detail.sessionStatus }}</p>
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
        <div v-if="report" class="hint">录入状态 {{ report.entryStatus }} · GMV ¥{{ report.gmv?.toFixed(2) }}</div>
        <div v-else class="formrow one">
          <div class="fld"><label>实际开始</label><input v-model="reportForm.actualStart" /></div>
          <div class="fld"><label>实际结束</label><input v-model="reportForm.actualEnd" /></div>
          <div class="fld"><label>GMV</label><input v-model.number="reportForm.gmv" type="number" step="0.01" /></div>
          <div class="fld"><label>订单数</label><input v-model.number="reportForm.orderCount" type="number" /></div>
          <div class="fld"><label>观看人数</label><input v-model.number="reportForm.viewerCount" type="number" /></div>
          <div class="fld"><label>峰值在线</label><input v-model.number="reportForm.peakOnline" type="number" /></div>
          <div class="fld"><label>涨粉</label><input v-model.number="reportForm.newFans" type="number" /></div>
          <div class="fld"><label>退款</label><input v-model.number="reportForm.refundAmount" type="number" step="0.01" /></div>
          <div class="fld"><label>投放成本</label><input v-model.number="reportForm.adCost" type="number" step="0.01" /></div>
        </div>
        <div class="acts" style="margin-top: 8px">
          <button v-if="!report || report.entryStatus === 'DRAFT'" class="btn btn-pri btn-sm" type="button" @click="submitReport">提交下播</button>
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

const loading = ref(false)
const error = ref('')
const hint = ref('')
const rows = ref<any[]>([])
const total = ref(0)
const query = reactive({ sessionCode: '', sessionStatus: '' })
const statusOptions = [
  { value: 'PENDING_RISK_CHECK', label: '待风控' },
  { value: 'APPROVED', label: '已放行' },
  { value: 'LIVE', label: '直播中' },
  { value: 'ENDED', label: '已下播' },
  { value: 'CANCELLED', label: '已取消' },
]

const registerOpen = ref(false)
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
  gmv: 1000,
  orderCount: 10,
  viewerCount: 500,
  peakOnline: 80,
  newFans: 20,
  refundAmount: 0,
  adCost: 100,
})

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

function openRegister() {
  clientToken = crypto.randomUUID()
  registerOpen.value = true
}

async function submitRegister() {
  hint.value = ''
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
    hint.value = errorMessage(e)
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
    { k: 'Football room', v: d.footballRoomId || '—' },
  ]
})

async function openDetail(row: any) {
  detailOpen.value = true
  tab.value = '基本信息'
  const code = row.sessionCode
  detail.value = await apiGet(`/live/sessions/${code}`)
  metrics.value = detail.value.metricsSnapshot || (await apiGet(`/live/sessions/${code}/metrics`))
  report.value = detail.value.report || (await apiGet(`/live/report/${code}`))
  const alarmRes = await apiGet('/live/alarm/records', { sessionCode: code, pageNo: 1, pageSize: 10 })
  alarms.value = alarmRes.list || []
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

async function doRisk() {
  if (!detail.value) return
  await apiPost(`/live/register/${detail.value.sessionCode}/risk-check`, {})
  detail.value = await apiGet(`/live/sessions/${detail.value.sessionCode}`)
}

async function doStart() {
  if (!detail.value) return
  await apiPut(`/live/register/${detail.value.sessionCode}/start`, {})
  detail.value = await apiGet(`/live/sessions/${detail.value.sessionCode}`)
  hint.value = '已确认开播'
}

async function submitReport() {
  if (!detail.value) return
  report.value = await apiPost(`/live/report/${detail.value.sessionCode}`, { ...reportForm })
  hint.value = '下播数据已提交'
}

onMounted(loadList)
</script>
