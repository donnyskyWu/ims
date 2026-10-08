<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>填报单管理</h1>
        <div class="sub">REPORT-002/003 · 审核队列 SLA 24h · 09 REPORT</div>
      </div>
      <div class="acts">
        <button v-if="tab === 'list'" class="btn btn-pri btn-sm" type="button" @click="openSubmit">提交填报单</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/template')">上报模板</button>
      </div>
    </div>
    <div class="tab-bar">
      <button type="button" class="tab-btn" :class="{ active: tab === 'list' }" @click="switchTab('list')">填报列表</button>
      <button type="button" class="tab-btn" :class="{ active: tab === 'audit' }" @click="switchTab('audit')">审核队列</button>
    </div>
    <p v-if="tab === 'list'" class="hint" style="margin-bottom: 8px">
      作者与账号须同属 IP 组账号池，否则后端返回 <strong>1127</strong>；去重键：模板+周期+填报人+作者+账号。
    </p>
    <p v-else class="hint" style="margin-bottom: 8px">
      REPORT-003：<code>GET /report/audit/queue</code> · 退回须填原因（<strong>1124</strong>）· SLA 超时行标红。
    </p>
    <form v-if="tab === 'list'" class="qbar" @submit.prevent="loadList">
      <input v-model="filters.submissionNo" placeholder="上报单号" style="width: 130px" />
      <input v-model="filters.period" placeholder="周期 2026-10-07" style="width: 130px" />
      <select v-model="filters.submitStatus" style="width: 110px">
        <option value="">全部状态</option>
        <option value="DRAFT">草稿</option>
        <option value="SUBMITTED">待审核</option>
        <option value="APPROVED">已通过</option>
        <option value="REJECTED">已退回</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <form v-else class="qbar" @submit.prevent="loadQueue">
      <select v-model="queueFilters.businessLine" style="width: 120px">
        <option value="">全部业务线</option>
        <option value="BUSINESS">业务线</option>
        <option value="FINANCE">财务线</option>
        <option value="ADMIN">行政线</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新队列</button>
    </form>
    <div v-if="tab === 'list'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>上报单号</th>
              <th>模板</th>
              <th>周期</th>
              <th>作者</th>
              <th>账号</th>
              <th>提交人</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无填报单' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue)">{{ row.submissionNo }}</td>
              <td>{{ row.templateName }}</td>
              <td>{{ row.period }}</td>
              <td>{{ row.authorName || row.authorId }}</td>
              <td>{{ row.accountLabel || row.accountId }}</td>
              <td>{{ row.submitterName }}</td>
              <td>
                <span class="tag" :style="statusStyle(row.submitStatus)">
                  <span class="dot"></span>{{ statusLabel(row.submitStatus) }}
                </span>
              </td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="showDetail(row)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>上报单号</th>
              <th>模板</th>
              <th>业务线</th>
              <th>周期</th>
              <th>提交人</th>
              <th>等待(h)</th>
              <th>SLA</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="queueLoading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!queueRows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ queueError || '暂无待审核' }}</div></div></td>
            </tr>
            <tr
              v-for="row in queueRows"
              v-else
              :key="row.id"
              :style="row.isTimeoutSla ? { background: 'rgba(255, 59, 48, 0.06)' } : undefined"
            >
              <td class="mono num" style="color: var(--blue)">{{ row.submissionNo }}</td>
              <td>{{ row.templateName }}</td>
              <td>{{ row.businessLine }}</td>
              <td>{{ row.period }}</td>
              <td>{{ row.submitterName }}</td>
              <td class="num">{{ row.waitingHours }}</td>
              <td>
                <span v-if="row.isTimeoutSla" class="tag" style="background: rgba(255, 59, 48, 0.12); color: #c62828">
                  <span class="dot"></span>超时
                </span>
                <span v-else class="tag" style="background: rgba(52, 199, 89, 0.12); color: #1e8e3e">
                  <span class="dot"></span>正常
                </span>
              </td>
              <td>
                <button class="btn btn-pri btn-sm" type="button" @click="doAudit(row, 'APPROVED')">通过</button>
                <button class="btn btn-sec btn-sm" type="button" @click="openReject(row)">退回</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">提交填报单</h3>
        <label class="fld">模板 ID</label>
        <input v-model.number="form.templateId" type="number" class="fld-in" />
        <label class="fld">周期</label>
        <input v-model="form.period" class="fld-in" placeholder="2026-10-07" />
        <label class="fld">作者 ID（AuthorSelect）</label>
        <input v-model.number="form.authorId" type="number" class="fld-in" />
        <label class="fld">账号 ID（AccountSelect · IP 组池）</label>
        <input v-model.number="form.accountId" type="number" class="fld-in" />
        <label class="fld">指标值</label>
        <input v-model.number="form.metricValue" type="number" class="fld-in" />
        <p v-if="formError" class="hint" style="color: var(--red); margin-top: 8px">{{ formError }}</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-sec btn-sm" type="button" @click="doSubmit(true)">存草稿</button>
          <button class="btn btn-pri btn-sm" type="button" @click="doSubmit(false)">正式提交</button>
        </div>
      </div>
    </div>

    <div v-if="rejectRow" class="modal-mask" @click.self="rejectRow = null">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 8px">退回 · {{ rejectRow.submissionNo }}</h3>
        <label class="fld">退回原因（必填 · 1124）</label>
        <textarea v-model="rejectReason" class="fld-in" rows="4" placeholder="如：数据来源不明、勾稽不平"></textarea>
        <p v-if="auditError" class="hint" style="color: var(--red); margin-top: 8px">{{ auditError }}</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="rejectRow = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="confirmReject">确认退回</button>
        </div>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="card" style="width: 480px; padding: 20px; max-height: 80vh; overflow: auto">
        <h3 style="margin: 0 0 8px">{{ detail.submissionNo }}</h3>
        <p class="hint">{{ detail.templateName }} · {{ detail.period }}</p>
        <pre class="mono" style="font-size: 12px; white-space: pre-wrap">{{ JSON.stringify(detail.dataContent, null, 2) }}</pre>
        <button class="btn btn-sec btn-sm" type="button" @click="detail = null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type Row = {
  id: number
  submissionNo: string
  templateName: string
  period: string
  authorId: number
  authorName: string
  accountId: number
  accountLabel: string
  submitterName: string
  submitStatus: string
  dataContent: Record<string, unknown>
}

type QueueRow = Row & {
  businessLine: string
  waitingHours: number
  isTimeoutSla: boolean
}

const router = useRouter()
const tab = ref<'list' | 'audit'>('list')
const rows = ref<Row[]>([])
const queueRows = ref<QueueRow[]>([])
const loading = ref(false)
const queueLoading = ref(false)
const error = ref('')
const queueError = ref('')
const auditError = ref('')
const rejectRow = ref<QueueRow | null>(null)
const rejectReason = ref('')
const queueFilters = reactive({ businessLine: '' })
const showForm = ref(false)
const formError = ref('')
const detail = ref<Row | null>(null)
const filters = reactive({ submissionNo: '', period: '', submitStatus: '' })
const form = reactive({
  templateId: 0,
  period: '',
  authorId: 0,
  accountId: 0,
  metricValue: 0,
})

function go(path: string) {
  router.push(path)
}

function switchTab(next: 'list' | 'audit') {
  tab.value = next
  if (next === 'audit') loadQueue()
  else loadList()
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    DRAFT: '草稿',
    SUBMITTED: '待审核',
    APPROVED: '已通过',
    REJECTED: '已退回',
  }
  return map[s] || s
}

function statusStyle(s: string) {
  if (s === 'SUBMITTED') return { background: 'rgba(255, 149, 0, 0.12)', color: '#c46a00' }
  if (s === 'APPROVED') return { background: 'rgba(52, 199, 89, 0.12)', color: '#1e8e3e' }
  if (s === 'REJECTED') return { background: 'rgba(255, 59, 48, 0.12)', color: '#c62828' }
  return { background: 'rgba(142, 142, 147, 0.12)', color: '#6d6d72' }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 30 }
    if (filters.period) params.period = filters.period
    if (filters.submitStatus) params.submitStatus = filters.submitStatus
    const res = await http.get('/report/submit/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    let list: Row[] = res.data.data.list || []
    if (filters.submissionNo.trim()) {
      const key = filters.submissionNo.trim()
      list = list.filter((r) => r.submissionNo.includes(key))
    }
    rows.value = list
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.submissionNo = ''
  filters.period = ''
  filters.submitStatus = ''
  loadList()
}

function openSubmit() {
  form.templateId = rows.value[0]?.id ? 0 : 0
  form.period = new Date().toISOString().slice(0, 10)
  form.authorId = 0
  form.accountId = 0
  form.metricValue = 0
  formError.value = ''
  showForm.value = true
}

async function doSubmit(asDraft: boolean) {
  formError.value = ''
  if (!form.templateId || !form.period || !form.authorId || !form.accountId) {
    formError.value = '模板、周期、作者、账号必填'
    return
  }
  try {
    const res = await http.post('/report/submit', {
      templateId: form.templateId,
      period: form.period,
      authorId: form.authorId,
      accountId: form.accountId,
      dataContent: { metric_value: form.metricValue },
      attachments: [],
      asDraft,
    })
    if (res.data.code !== 0) {
      formError.value = `[${res.data.code}] ${res.data.msg}`
      return
    }
    showForm.value = false
    await loadList()
  } catch {
    formError.value = '网络错误'
  }
}

async function loadQueue() {
  queueLoading.value = true
  queueError.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 30 }
    if (queueFilters.businessLine) params.businessLine = queueFilters.businessLine
    const res = await http.get('/report/audit/queue', { params })
    if (res.data.code !== 0) {
      queueError.value = res.data.msg || '加载失败'
      queueRows.value = []
      return
    }
    queueRows.value = res.data.data.list || []
  } catch {
    queueError.value = '网络错误'
    queueRows.value = []
  } finally {
    queueLoading.value = false
  }
}

async function doAudit(row: QueueRow, conclusion: 'APPROVED' | 'REJECTED', reason = '') {
  auditError.value = ''
  try {
    const res = await http.put(`/report/audit/${row.id}`, {
      conclusion,
      rejectReason: reason,
      rejectReasonTags: reason ? ['其他'] : [],
    })
    if (res.data.code !== 0) {
      auditError.value = `[${res.data.code}] ${res.data.msg}`
      if (conclusion === 'REJECTED') return false
      window.alert(auditError.value)
      return false
    }
    await loadQueue()
    return true
  } catch {
    auditError.value = '网络错误'
    return false
  }
}

function openReject(row: QueueRow) {
  rejectRow.value = row
  rejectReason.value = ''
  auditError.value = ''
}

async function confirmReject() {
  if (!rejectRow.value) return
  if (!rejectReason.value.trim()) {
    auditError.value = '退回原因必填（1124）'
    return
  }
  const ok = await doAudit(rejectRow.value, 'REJECTED', rejectReason.value.trim())
  if (ok) rejectRow.value = null
}

async function showDetail(row: Row) {
  try {
    const res = await http.get(`/report/submit/${row.submissionNo}`)
    if (res.data.code === 0) detail.value = res.data.data
  } catch {
    detail.value = row
  }
}

onMounted(loadList)
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.tab-btn {
  border: 1px solid var(--border, #e5e5ea);
  background: var(--bg2, #f5f5f7);
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.tab-btn.active {
  background: rgba(0, 113, 227, 0.12);
  border-color: rgba(0, 113, 227, 0.35);
  color: #0071e3;
  font-weight: 600;
}
</style>
