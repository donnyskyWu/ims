<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>填报单管理</h1>
        <div class="sub">查看填报记录，并处理待审核单据</div>
      </div>
      <div class="acts">
        <button v-if="tab === 'list'" class="btn btn-pri btn-sm" type="button" data-testid="submit-open" @click="openSubmit">提交填报单</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/template')">上报模板</button>
      </div>
    </div>
    <p v-if="toast" class="hint" data-testid="submit-toast">{{ toast }}</p>
    <div class="tab-bar">
      <button type="button" class="tab-btn" :class="{ active: tab === 'list' }" @click="switchTab('list')">填报列表</button>
      <button type="button" class="tab-btn" :class="{ active: tab === 'audit' }" @click="switchTab('audit')">审核队列</button>
    </div>
    <p v-if="tab === 'list'" class="hint" style="margin-bottom: 8px">
      作者与平台账号须属于同一账号池。同一模板、日期、填报人、作者和账号不能重复提交。
    </p>
    <p v-else class="hint" style="margin-bottom: 8px">
      退回须填写原因。超过 24 小时未审核的单据会标红。
    </p>
    <form v-if="tab === 'list'" class="qbar" @submit.prevent="loadList">
      <input v-model="filters.submissionNo" placeholder="上报单号" style="width: 130px" />
      <select v-model.number="filters.authorId" style="width: 140px" data-testid="filter-author" @change="onFilterAuthor">
        <option :value="0">全部作者</option>
        <option v-for="author in filterAuthors" :key="author.id" :value="author.id">{{ author.authorName }}</option>
      </select>
      <select v-model.number="filters.accountId" style="width: 150px" data-testid="filter-account" :disabled="!filters.authorId">
        <option :value="0">{{ filters.authorId ? '全部账号' : '请先选择作者' }}</option>
        <option v-for="acc in filterAccounts" :key="acc.id" :value="acc.id">{{ acc.label || acc.accountName }}</option>
      </select>
      <select v-model="filters.submitStatus" style="width: 110px" data-testid="filter-status">
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
              <th>提交人</th>
              <th>作者</th>
              <th>平台账号</th>
              <th>提交时间</th>
              <th>数据量</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9"><div class="empty"><div class="et">{{ error || '暂无填报单' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue)">{{ row.submissionNo }}</td>
              <td>{{ row.templateName }}</td>
              <td>{{ row.submitterName }}</td>
              <td>{{ row.authorName || '—' }}</td>
              <td>{{ row.accountLabel || '—' }}</td>
              <td>{{ formatTime(row.submittedAt) }}</td>
              <td class="num">{{ row.dataVolume ?? 0 }}</td>
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
      <div class="card submit-modal" data-testid="submit-dialog">
        <h3 style="margin: 0 0 12px">提交填报单</h3>
        <label class="fld">选择模板 <span class="req">*</span></label>
        <select v-model.number="form.templateId" class="fld-in" data-testid="submit-template" @change="onTemplateChange">
          <option :value="0">请选择模板</option>
          <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.templateName }}</option>
        </select>
        <label class="fld">作者 <span class="req">*</span></label>
        <select
          v-model.number="form.authorId"
          class="fld-in"
          data-testid="submit-author"
          :disabled="!form.templateId"
          @change="onAuthorChange"
        >
          <option :value="0">请选择作者（AuthorSelect）</option>
          <option v-for="author in authors" :key="author.id" :value="author.id">{{ author.authorName }}</option>
        </select>
        <label class="fld">平台账号 <span class="req">*</span></label>
        <select v-model.number="form.accountId" class="fld-in" data-testid="submit-account" :disabled="!form.authorId">
          <option :value="0">{{ form.authorId ? '请选择平台账号' : '请先选择作者' }}</option>
          <option v-for="acc in accounts" :key="acc.id" :value="acc.id">{{ acc.label || acc.accountName }}</option>
        </select>
        <label class="fld">数据日期 <span class="req">*</span></label>
        <input v-model="form.period" type="date" class="fld-in" data-testid="submit-date" />
        <template v-for="field in activeFields" :key="field.fieldKey">
          <label class="fld">
            {{ field.fieldLabel || field.fieldKey }}
            <span v-if="field.required" class="req">*</span>
          </label>
          <select
            v-if="field.options?.length"
            v-model="fieldValues[field.fieldKey]"
            class="fld-in"
            :class="{ bad: fieldErrors[field.fieldKey] }"
            :data-testid="`submit-field-${field.fieldKey}`"
          >
            <option value="">请选择</option>
            <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
          </select>
          <input
            v-else
            v-model="fieldValues[field.fieldKey]"
            class="fld-in"
            :class="{ bad: fieldErrors[field.fieldKey] }"
            :type="inputType(field.fieldType)"
            :data-testid="`submit-field-${field.fieldKey}`"
          />
          <p v-if="fieldErrors[field.fieldKey]" class="field-err">{{ fieldErrors[field.fieldKey] }}</p>
        </template>
        <label class="fld">数据附件（按模板 CSV）</label>
        <input class="fld-in" type="file" accept=".csv,text/csv" data-testid="submit-file" @change="onAttachment" />
        <p v-if="attachmentName" class="hint">已选择 {{ attachmentName }}</p>
        <label class="fld">数据行数</label>
        <input v-model="form.rowCount" type="number" min="0" class="fld-in" data-testid="submit-rows" />
        <label class="fld">数据说明</label>
        <textarea v-model="form.remark" class="fld-in" rows="2" data-testid="submit-remark"></textarea>
        <p v-if="formError" class="hint" style="color: var(--red); margin-top: 8px" data-testid="submit-error">{{ formError }}</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="submit-send" @click="doSubmit(false)">提交并送审</button>
        </div>
      </div>
    </div>

    <div v-if="rejectRow" class="modal-mask" @click.self="rejectRow = null">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 8px">退回 · {{ rejectRow.submissionNo }}</h3>
        <label class="fld">退回原因（必填）</label>
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
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

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
  submittedAt: string
  dataVolume: number
  submitStatus: string
  dataContent: Record<string, unknown>
}

type QueueRow = Row & {
  businessLine: string
  waitingHours: number
  isTimeoutSla: boolean
}

const router = useRouter()
const route = useRoute()
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
const toast = ref('')
const detail = ref<Row | null>(null)
const filters = reactive({ submissionNo: '', authorId: 0, accountId: 0, submitStatus: '' })
const filterAuthors = ref<AuthorOpt[]>([])
const filterAccounts = ref<AccountOpt[]>([])
const filterTemplateId = ref(0)

type FieldDef = {
  fieldKey: string
  fieldLabel: string
  fieldType: string
  required?: boolean
  options?: string[]
}
type TemplateOpt = {
  id: number
  templateName: string
  fieldsSchema: FieldDef[]
}
type AuthorOpt = { id: number; authorName: string; ipGroupId: number }
type AccountOpt = { id: number; accountName: string; accountNo: string; label: string }

const templates = ref<TemplateOpt[]>([])
const authors = ref<AuthorOpt[]>([])
const accounts = ref<AccountOpt[]>([])
const activeFields = ref<FieldDef[]>([])
const fieldValues = reactive<Record<string, string>>({})
const fieldErrors = reactive<Record<string, string>>({})
const attachmentName = ref('')
const form = reactive({
  templateId: 0,
  period: '',
  authorId: 0,
  accountId: 0,
  rowCount: '',
  remark: '',
})

function go(path: string) {
  router.push(path)
}

function switchTab(next: 'list' | 'audit') {
  tab.value = next
  if (next === 'audit') loadQueue()
  else loadList()
}

function formatTime(value: string) {
  if (!value) return '—'
  return value.replace('T', ' ').replace('+08:00', '')
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
    if (filters.authorId) params.authorId = filters.authorId
    if (filters.accountId) params.accountId = filters.accountId
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
  } catch (err) {
    error.value = describeError(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.submissionNo = ''
  filters.authorId = 0
  filters.accountId = 0
  filters.submitStatus = ''
  filterAccounts.value = []
  loadList()
}

async function loadFilterAuthors() {
  try {
    const res = await http.get('/report/submit/context')
    const templates: TemplateOpt[] = res.data.data?.templates || []
    filterTemplateId.value = templates[0]?.id || 0
    if (!filterTemplateId.value) {
      filterAuthors.value = []
      return
    }
    const withAuthors = await http.get('/report/submit/context', { params: { templateId: filterTemplateId.value } })
    filterAuthors.value = withAuthors.data.data?.authors || []
  } catch {
    filterAuthors.value = []
  }
}

async function onFilterAuthor() {
  filters.accountId = 0
  filterAccounts.value = []
  if (!filters.authorId || !filterTemplateId.value) return
  try {
    const res = await http.get('/report/submit/context', {
      params: { templateId: filterTemplateId.value, authorId: filters.authorId },
    })
    filterAccounts.value = res.data.data?.accounts || []
  } catch (err) {
    error.value = describeError(err)
  }
}

function inputType(fieldType: string) {
  if (fieldType === 'DATE') return 'date'
  if (fieldType === 'NUMBER' || fieldType === 'INTEGER' || fieldType === 'MONEY') return 'number'
  return 'text'
}

function clearFieldState() {
  for (const key of Object.keys(fieldValues)) delete fieldValues[key]
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
}

function applyTemplateFields(templateId: number) {
  const tpl = templates.value.find((item) => item.id === templateId)
  activeFields.value = tpl?.fieldsSchema || []
  clearFieldState()
  for (const field of activeFields.value) fieldValues[field.fieldKey] = ''
}

function describeError(error: unknown): string {
  if (error && typeof error === 'object' && 'msg' in error) {
    const body = error as { code?: number; msg?: string }
    if (body.msg) return body.code ? `${body.msg}（${body.code}）` : body.msg
  }
  return errorMessage(error)
}

function applyFieldErrors(error: unknown) {
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
  if (!error || typeof error !== 'object' || !('data' in error)) return
  const data = (error as { data?: { errors?: { fieldKey?: string; errorMsg?: string }[] } }).data
  for (const item of data?.errors || []) {
    if (item.fieldKey) fieldErrors[item.fieldKey] = item.errorMsg || '校验未通过'
  }
}

async function loadContext(templateId?: number, authorId?: number) {
  const params: Record<string, number> = {}
  if (templateId) params.templateId = templateId
  if (authorId) params.authorId = authorId
  const res = await http.get('/report/submit/context', { params })
  const data = res.data.data || {}
  templates.value = data.templates || []
  authors.value = data.authors || []
  accounts.value = data.accounts || []
}

async function openSubmit() {
  form.templateId = 0
  form.period = new Date().toISOString().slice(0, 10)
  form.authorId = 0
  form.accountId = 0
  form.rowCount = ''
  form.remark = ''
  formError.value = ''
  attachmentName.value = ''
  authors.value = []
  accounts.value = []
  activeFields.value = []
  clearFieldState()
  showForm.value = true
  try {
    await loadContext()
  } catch (error) {
    formError.value = describeError(error)
  }
}

async function onTemplateChange() {
  form.authorId = 0
  form.accountId = 0
  authors.value = []
  accounts.value = []
  applyTemplateFields(form.templateId)
  if (!form.templateId) return
  try {
    await loadContext(form.templateId)
    applyTemplateFields(form.templateId)
  } catch (error) {
    formError.value = describeError(error)
  }
}

async function onAuthorChange() {
  form.accountId = 0
  accounts.value = []
  if (!form.templateId || !form.authorId) return
  try {
    await loadContext(form.templateId, form.authorId)
  } catch (error) {
    formError.value = describeError(error)
  }
}

function onAttachment(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  attachmentName.value = file?.name || ''
}

async function doSubmit(asDraft: boolean) {
  formError.value = ''
  for (const key of Object.keys(fieldErrors)) delete fieldErrors[key]
  const missing: string[] = []
  if (!form.authorId) missing.push('请选择作者（AuthorSelect）')
  if (!form.templateId) missing.push('请选择模板')
  if (!form.accountId) missing.push('请选择平台账号')
  if (!form.period) missing.push('请选择数据日期')
  let fieldMissing = false
  for (const field of activeFields.value) {
    if (field.required && !String(fieldValues[field.fieldKey] ?? '').trim()) {
      fieldErrors[field.fieldKey] = '必填项，请填写'
      fieldMissing = true
    }
  }
  if (missing.length || fieldMissing) {
    formError.value = missing.join('；') || '请填写必填字段'
    return
  }
  const dataContent: Record<string, string | number> = { _dataDate: form.period }
  for (const field of activeFields.value) {
    const raw = String(fieldValues[field.fieldKey] ?? '').trim()
    if (!raw) continue
    if (field.fieldType === 'NUMBER' || field.fieldType === 'INTEGER' || field.fieldType === 'MONEY') {
      dataContent[field.fieldKey] = Number(raw)
    } else {
      dataContent[field.fieldKey] = raw
    }
  }
  if (form.rowCount !== '') dataContent._rowCount = Number(form.rowCount)
  if (form.remark.trim()) dataContent._remark = form.remark.trim()
  try {
    const res = await http.post('/report/submit', {
      templateId: form.templateId,
      period: form.period,
      authorId: form.authorId,
      accountId: form.accountId,
      dataContent,
      attachments: attachmentName.value ? [{ fileName: attachmentName.value, fileKey: attachmentName.value }] : [],
      asDraft,
    })
    const no = res.data.data?.submissionNo || ''
    const status = statusLabel(res.data.data?.submitStatus || 'SUBMITTED')
    toast.value = `已提交 ${no}，状态${status}`
    showForm.value = false
    await loadList()
  } catch (error) {
    applyFieldErrors(error)
    formError.value = describeError(error)
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
  } catch (err) {
    queueError.value = describeError(err)
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
  } catch (err) {
    auditError.value = describeError(err)
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
    auditError.value = '退回原因必填'
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

async function openPreselected(templateId: number) {
  form.templateId = templateId
  form.period = new Date().toISOString().slice(0, 10)
  form.authorId = 0
  form.accountId = 0
  form.rowCount = ''
  form.remark = ''
  formError.value = ''
  attachmentName.value = ''
  showForm.value = true
  try {
    await loadContext()
    await onTemplateChange()
  } catch (error) {
    formError.value = describeError(error)
  }
}

onMounted(() => {
  loadList()
  loadFilterAuthors()
  const raw = route.query.templateId
  const templateId = Number(Array.isArray(raw) ? raw[0] : raw || 0)
  if (templateId) void openPreselected(templateId)
})
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
.submit-modal {
  width: 480px;
  max-height: 86vh;
  overflow: auto;
  padding: 20px;
}
.req {
  color: #c62828;
}
.fld-in.bad {
  border-color: #c62828;
}
.field-err {
  margin: 4px 0 0;
  color: #c62828;
  font-size: 12px;
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
