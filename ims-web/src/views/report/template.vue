<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>上报模板</h1>
        <div class="sub">配置上报字段、勾稽规则和填报人</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="tpl-create-open" @click="openCreate">新建模板</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/submission')">填报单管理</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      模板字段配置后，上报人按模板逐项填报，提交后进入审核。
    </p>
    <p v-if="toast" class="hint" data-testid="tpl-toast">{{ toast }}</p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.templateName" placeholder="模板名称" style="width: 160px" />
      <select v-model="filters.periodType" style="width: 110px">
        <option value="">全部周期</option>
        <option value="DAILY">每日</option>
        <option value="WEEKLY">每周</option>
        <option value="MONTHLY">每月</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>模板编号</th>
              <th>模板名称</th>
              <th>字段数</th>
              <th>上报频率</th>
              <th>责任部门</th>
              <th>累计使用</th>
              <th>启停</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无模板' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono num" style="color: var(--blue)">
                <button class="linkish" type="button" @click="openEdit(row)">{{ row.templateNo }}</button>
              </td>
              <td style="font-weight: 500">
                <button class="linkish" type="button" @click="openEdit(row)">{{ row.templateName }}</button>
              </td>
              <td class="num">{{ row.fieldCount }} 字段</td>
              <td>
                <span class="tag" :style="periodStyle(row.periodType)">
                  <span class="dot"></span>{{ periodLabel(row.periodType, row.deadlineRule) }}
                </span>
              </td>
              <td>{{ row.deptName || '—' }}</td>
              <td class="num">{{ row.usageCount }} 次</td>
              <td>
                <span class="sw" :class="{ on: row.status === 'ENABLED' }"><i></i></span>
              </td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" data-testid="tpl-edit" @click="openEdit(row)">编辑</button>
                <button
                  v-if="row.status === 'DISABLED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  data-testid="tpl-enable"
                  @click="enableRow(row)"
                >
                  启用
                </button>
                <button v-else class="btn btn-sec btn-sm" type="button" data-testid="tpl-disable" @click="askDisable(row)">
                  停用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 480px; padding: 20px" data-testid="tpl-create-dialog">
        <h3 style="margin: 0 0 12px">新建上报模板</h3>
        <div class="fld">
          <label>模板名称 <span class="req">*</span></label>
          <input v-model="form.templateName" data-testid="tpl-name" :class="{ bad: fieldTips.templateName }" />
          <p v-if="fieldTips.templateName" class="field-err">{{ fieldTips.templateName }}</p>
        </div>
        <div class="fld">
          <label>上报频率 <span class="req">*</span></label>
          <select v-model="form.frequency" data-testid="tpl-frequency" :class="{ bad: fieldTips.frequency }">
            <option value="">请选择</option>
            <option v-for="item in FREQUENCIES" :key="item.label" :value="item.label">{{ item.label }}</option>
          </select>
          <p v-if="fieldTips.frequency" class="field-err">{{ fieldTips.frequency }}</p>
        </div>
        <div class="fld">
          <label>责任部门 <span class="req">*</span></label>
          <select v-model="form.deptName" data-testid="tpl-dept" :class="{ bad: fieldTips.deptName }">
            <option value="">请选择</option>
            <option v-for="dept in DEPTS" :key="dept" :value="dept">{{ dept }}</option>
          </select>
          <p v-if="fieldTips.deptName" class="field-err">{{ fieldTips.deptName }}</p>
        </div>
        <div class="fld">
          <label>业务线 <span class="req">*</span></label>
          <select v-model="form.businessLine" data-testid="tpl-line" :class="{ bad: fieldTips.businessLine }">
            <option value="">请选择</option>
            <option value="BUSINESS">业务</option>
            <option value="FINANCE">财务</option>
            <option value="ADMIN">行政</option>
          </select>
          <p v-if="fieldTips.businessLine" class="field-err">{{ fieldTips.businessLine }}</p>
        </div>
        <div class="fld">
          <label>初始字段数</label>
          <input v-model="form.fieldCount" type="number" min="0" data-testid="tpl-field-count" placeholder="0" />
        </div>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="tpl-create" @click="submitCreate">创建模板</button>
        </div>
        <p v-if="formError" class="hint" style="color: var(--red); margin-top: 8px">{{ formError }}</p>
      </div>
    </div>

    <div v-if="confirmRow" class="modal-mask" @click.self="confirmRow = null">
      <div class="modal card" style="max-width: 420px; padding: 20px" data-testid="tpl-disable-confirm">
        <h3 style="margin: 0 0 8px">停用模板</h3>
        <p>确认停用「{{ confirmRow.templateName }}」？停用后不能再用于新的填报。</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="confirmRow = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="tpl-disable-ok" @click="confirmDisable">确认停用</button>
        </div>
      </div>
    </div>

    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <div class="modal card edit-drawer" data-testid="tpl-edit-drawer">
        <h3 style="margin: 0 0 8px">编辑模板 · {{ editing?.templateName }}</h3>
        <p class="hint">保存后生成新版本，进行中的填报单仍沿用旧版。</p>
        <div class="tab-bar">
          <button type="button" class="tab-btn" :class="{ active: editTab === 'fields' }" data-testid="tpl-tab-fields" @click="editTab = 'fields'">字段定义</button>
          <button type="button" class="tab-btn" :class="{ active: editTab === 'rules' }" data-testid="tpl-tab-rules" @click="editTab = 'rules'">勾稽规则</button>
          <button type="button" class="tab-btn" :class="{ active: editTab === 'people' }" data-testid="tpl-tab-people" @click="editTab = 'people'">填报人</button>
        </div>

        <div v-if="editTab === 'fields'">
          <table class="mini">
            <thead>
              <tr>
                <th>字段键</th>
                <th>名称</th>
                <th>类型</th>
                <th>必填</th>
                <th>校验</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(field, index) in editFields" :key="index">
                <td><input v-model="field.fieldKey" placeholder="gmv" /></td>
                <td><input v-model="field.fieldLabel" placeholder="GMV" /></td>
                <td>
                  <select v-model="field.fieldType">
                    <option value="MONEY">金额</option>
                    <option value="INTEGER">整数</option>
                    <option value="NUMBER">数值</option>
                    <option value="TEXT">文本</option>
                    <option value="ENUM">枚举</option>
                    <option value="DATE">日期</option>
                  </select>
                </td>
                <td><input v-model="field.required" type="checkbox" /></td>
                <td>
                  <input
                    v-if="isNumberType(field.fieldType)"
                    v-model="field.minText"
                    placeholder="≥0"
                    style="width: 72px"
                  />
                  <input
                    v-else-if="field.fieldType === 'TEXT'"
                    v-model="field.maxLenText"
                    placeholder="≤200 字"
                    style="width: 88px"
                  />
                  <input v-model="field.validateExpr" placeholder="校验表达式" data-testid="tpl-validate-expr" />
                </td>
                <td class="nowrap">
                  <button class="btn btn-sec btn-sm" type="button" @click="moveField(index, -1)">↑</button>
                  <button class="btn btn-sec btn-sm" type="button" @click="moveField(index, 1)">↓</button>
                  <button class="btn btn-sec btn-sm" type="button" @click="editFields.splice(index, 1)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
          <button class="btn btn-sec btn-sm" type="button" data-testid="tpl-add-field" @click="addField">新增字段</button>
        </div>

        <div v-else-if="editTab === 'rules'">
          <p class="hint">只允许字段代码、SUM/AVG/COUNT/MAX/MIN 和四则运算。DELETE、DROP 等语句会被拒绝。</p>
          <div v-for="(rule, index) in editRules" :key="index" class="rule-row">
            <input v-model="rule.expression" placeholder="如 gmv == orders" data-testid="tpl-rule-expr" />
            <input v-model="rule.errorMsg" placeholder="错误提示，如明细合计不平" />
            <button class="btn btn-sec btn-sm" type="button" @click="editRules.splice(index, 1)">删除</button>
          </div>
          <button class="btn btn-sec btn-sm" type="button" data-testid="tpl-add-rule" @click="editRules.push({ expression: '', errorMsg: '勾稽校验失败' })">
            新增规则
          </button>
        </div>

        <div v-else>
          <p class="hint">被指定的人会在工作台看到填报待办；未指定的人不会出现。</p>
          <p v-if="usersError" class="hint" style="color: var(--red)">{{ usersError }}</p>
          <label v-for="user in users" :key="user.id" class="user-line">
            <input v-model="selectedUserIds" type="checkbox" :value="user.id" />
            {{ user.nickname || user.username }}（{{ user.username }}）
          </label>
          <p v-if="!users.length && !usersError" class="hint">暂无可选用户</p>
        </div>

        <p v-if="editError" class="hint" style="color: var(--red)" data-testid="tpl-edit-error">{{ editError }}</p>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showEdit = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="tpl-save" @click="saveEdit">保存模板</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'

type SchemaField = {
  fieldKey: string
  fieldLabel: string
  fieldType: string
  required?: boolean
  range?: { min?: number; max?: number; maxLength?: number }
  validateExpr?: string
  crossCheck?: { expression?: string; errorMsg?: string; targetFieldKey?: string; operator?: string }
}

type Row = {
  id: number
  templateNo: string
  templateName: string
  fieldCount: number
  periodType: string
  deadlineRule: string
  deptName: string
  usageCount: number
  status: string
  businessLine: string
  fieldsSchema: SchemaField[]
  assignees: Array<{ assignType?: string; targetIds?: number[] }>
}

type EditField = {
  fieldKey: string
  fieldLabel: string
  fieldType: string
  required: boolean
  minText: string
  maxLenText: string
  validateExpr: string
  legacyCheck?: SchemaField['crossCheck']
}

const FUNCS = new Set(['SUM', 'AVG', 'COUNT', 'MAX', 'MIN'])
const SQL_WORDS = /^(DELETE|DROP|UPDATE|INSERT|SELECT|ALTER|TRUNCATE|EXEC|UNION|FROM|WHERE|TABLE)$/i

const router = useRouter()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const toast = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ templateName: '', periodType: '', status: '' })
const FREQUENCIES = [
  { label: '每日 18:00 前', periodType: 'DAILY', deadlineRule: '18:00' },
  { label: '场次结束 2h 内', periodType: 'DAILY', deadlineRule: '场次结束 2h 内' },
  { label: '每周一 12:00 前', periodType: 'WEEKLY', deadlineRule: '周一 12:00' },
  { label: '每周五 18:00 前', periodType: 'WEEKLY', deadlineRule: '周五 18:00' },
  { label: '活动结束 24h 内', periodType: 'MONTHLY', deadlineRule: '活动结束 24h 内' },
]
const DEPTS = ['运营中心', '直播运营', '内容中心', '数据中心', '商务外协']

const form = reactive({
  templateName: '',
  frequency: '',
  deptName: '',
  businessLine: '',
  fieldCount: '',
})
const fieldTips = reactive({ templateName: '', frequency: '', deptName: '', businessLine: '' })
const confirmRow = ref<Row | null>(null)

const showEdit = ref(false)
const editing = ref<Row | null>(null)
const editTab = ref<'fields' | 'rules' | 'people'>('fields')
const editFields = ref<EditField[]>([])
const editRules = ref<Array<{ expression: string; errorMsg: string }>>([])
const editError = ref('')
const users = ref<Array<{ id: number; username: string; nickname: string }>>([])
const usersError = ref('')
const selectedUserIds = ref<number[]>([])

function go(path: string) {
  router.push(path)
}

function apiError(err: unknown): string {
  if (err && typeof err === 'object' && 'msg' in err) {
    const body = err as { code?: number; msg?: string }
    if (body.msg) return body.code ? `${body.msg}（${body.code}）` : body.msg
  }
  return errorMessage(err)
}

function periodLabel(period: string, rule: string) {
  const hit = FREQUENCIES.find((item) => item.periodType === period && item.deadlineRule === rule)
  if (hit) return hit.label
  const map: Record<string, string> = {
    DAILY: '每日',
    WEEKLY: '每周',
    MONTHLY: '每月',
  }
  return `${map[period] || period} ${rule || ''}`.trim()
}

function periodStyle(period: string) {
  if (period === 'DAILY') return { background: 'rgba(0,113,227,.12)', color: '#0071e3' }
  if (period === 'WEEKLY') return { background: 'rgba(90,200,250,.12)', color: '#0e7fb8' }
  return { background: 'rgba(255,149,0,.12)', color: '#c46a00' }
}

function isNumberType(fieldType: string) {
  return fieldType === 'NUMBER' || fieldType === 'INTEGER' || fieldType === 'MONEY'
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.templateName) params.templateName = filters.templateName
    if (filters.periodType) params.periodType = filters.periodType
    if (filters.status) params.status = filters.status
    const res = await http.get('/report/template/list', { params })
    rows.value = res.data.data.list || []
  } catch (err) {
    error.value = apiError(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.templateName = ''
  filters.periodType = ''
  filters.status = ''
  loadList()
}

function openCreate() {
  form.templateName = ''
  form.frequency = ''
  form.deptName = ''
  form.businessLine = ''
  form.fieldCount = ''
  fieldTips.templateName = ''
  fieldTips.frequency = ''
  fieldTips.deptName = ''
  fieldTips.businessLine = ''
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  fieldTips.templateName = form.templateName.trim() ? '' : '必填项，请填写'
  fieldTips.frequency = form.frequency ? '' : '必填项，请填写'
  fieldTips.deptName = form.deptName ? '' : '必填项，请填写'
  fieldTips.businessLine = form.businessLine ? '' : '必填项，请填写'
  if (fieldTips.templateName || fieldTips.frequency || fieldTips.deptName || fieldTips.businessLine) {
    formError.value = '必填项，请填写'
    return
  }
  const freq = FREQUENCIES.find((item) => item.label === form.frequency)
  if (!freq) {
    fieldTips.frequency = '必填项，请填写'
    return
  }
  const count = Math.max(0, Number(form.fieldCount) || 0)
  const fieldsSchema = Array.from({ length: count }, (_, index) => ({
    fieldKey: `field_${index + 1}`,
    fieldLabel: `字段${index + 1}`,
    fieldType: 'NUMBER',
    required: false,
  }))
  try {
    await http.post('/report/template', {
      templateName: form.templateName.trim(),
      periodType: freq.periodType,
      deadlineRule: freq.deadlineRule,
      deptName: form.deptName,
      businessLine: form.businessLine,
      status: 'ENABLED',
      fieldsSchema,
      assignees: [],
    })
    showForm.value = false
    toast.value = '模板已创建'
    await loadList()
  } catch (err) {
    formError.value = apiError(err)
  }
}

function askDisable(row: Row) {
  confirmRow.value = row
}

async function confirmDisable() {
  const row = confirmRow.value
  if (!row) return
  try {
    await http.delete(`/report/template/${row.id}`)
    confirmRow.value = null
    toast.value = '模板已停用'
    await loadList()
  } catch (err) {
    error.value = apiError(err)
    confirmRow.value = null
  }
}

async function enableRow(row: Row) {
  try {
    await http.put(`/report/template/${row.id}`, {
      templateName: row.templateName,
      periodType: row.periodType,
      deadlineRule: row.deadlineRule,
      deptName: row.deptName,
      businessLine: row.businessLine || 'BUSINESS',
      status: 'ENABLED',
      fieldsSchema: row.fieldsSchema || [],
      assignees: row.assignees || [],
    })
    toast.value = '已启用'
    await loadList()
  } catch (err) {
    error.value = apiError(err)
  }
}

function addField() {
  editFields.value.push({
    fieldKey: '',
    fieldLabel: '',
    fieldType: 'MONEY',
    required: false,
    minText: '',
    maxLenText: '',
    validateExpr: '',
  })
}

function moveField(index: number, delta: number) {
  const next = index + delta
  if (next < 0 || next >= editFields.value.length) return
  const list = editFields.value.slice()
  const [item] = list.splice(index, 1)
  list.splice(next, 0, item)
  editFields.value = list
}

async function loadUsers() {
  usersError.value = ''
  try {
    const res = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    users.value = res.data.data.list || []
  } catch (err) {
    usersError.value = apiError(err)
    users.value = []
  }
}

function openEdit(row: Row) {
  editing.value = row
  editTab.value = 'fields'
  editError.value = ''
  toast.value = ''
  const schema = row.fieldsSchema || []
  editFields.value = schema
    .filter((item) => item.fieldType !== 'CROSS_RULE')
    .map((item) => ({
      fieldKey: item.fieldKey,
      fieldLabel: item.fieldLabel,
      fieldType: item.fieldType || 'TEXT',
      required: !!item.required,
      minText: item.range?.min != null ? String(item.range.min) : '',
      maxLenText: item.range?.maxLength != null ? String(item.range.maxLength) : '',
      validateExpr: item.validateExpr || '',
      legacyCheck: item.crossCheck?.expression ? undefined : item.crossCheck,
    }))
  editRules.value = schema
    .filter((item) => item.crossCheck?.expression || item.fieldType === 'CROSS_RULE')
    .map((item) => ({
      expression: item.crossCheck?.expression || '',
      errorMsg: item.crossCheck?.errorMsg || '勾稽校验失败',
    }))
  const ids = (row.assignees || []).flatMap((item) => (item.assignType === 'USER' ? item.targetIds || [] : []))
  selectedUserIds.value = ids.map((id) => Number(id))
  showEdit.value = true
  loadUsers()
}

function localRuleError(keys: Set<string>): string {
  const ident = /[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*/g
  for (const rule of editRules.value) {
    const expr = rule.expression.trim()
    if (!expr) continue
    const names = expr.match(ident) || []
    for (const name of names) {
      if (FUNCS.has(name.toUpperCase())) continue
      if (SQL_WORDS.test(name)) return '非法表达式（1192）'
      if (!keys.has(name)) return '勾稽规则引用了不存在的字段（1121）'
    }
  }
  for (const field of editFields.value) {
    const expr = field.validateExpr.trim()
    if (!expr) continue
    const names = expr.match(ident) || []
    for (const name of names) {
      if (FUNCS.has(name.toUpperCase())) continue
      if (SQL_WORDS.test(name)) return '非法表达式（1192）'
    }
  }
  return ''
}

async function saveEdit() {
  editError.value = ''
  const row = editing.value
  if (!row) return
  const keys = new Set<string>()
  for (const field of editFields.value) {
    const key = field.fieldKey.trim()
    if (!key || !field.fieldLabel.trim()) {
      editError.value = '字段键和名称必填'
      editTab.value = 'fields'
      return
    }
    if (keys.has(key)) {
      editError.value = `字段键重复：${key}`
      return
    }
    keys.add(key)
  }
  const instant = localRuleError(keys)
  if (instant) {
    editError.value = instant
    editTab.value = instant.includes('1121') || instant.includes('1192') ? 'rules' : editTab.value
    return
  }
  const fieldsSchema = [
    ...editFields.value.map((field) => {
      const range: { min?: number; maxLength?: number } = {}
      if (isNumberType(field.fieldType) && field.minText.trim() !== '' && !Number.isNaN(Number(field.minText))) {
        range.min = Number(field.minText)
      }
      if (field.fieldType === 'TEXT' && field.maxLenText.trim() !== '' && !Number.isNaN(Number(field.maxLenText))) {
        range.maxLength = Number(field.maxLenText)
      }
      return {
        fieldKey: field.fieldKey.trim(),
        fieldLabel: field.fieldLabel.trim(),
        fieldType: field.fieldType,
        required: field.required,
        range: Object.keys(range).length ? range : undefined,
        validateExpr: field.validateExpr.trim() || undefined,
        crossCheck: field.legacyCheck,
      }
    }),
    ...editRules.value
      .filter((rule) => rule.expression.trim())
      .map((rule, index) => ({
        fieldKey: `rule_${index + 1}`,
        fieldLabel: rule.errorMsg.trim() || '勾稽规则',
        fieldType: 'CROSS_RULE',
        required: false,
        crossCheck: {
          expression: rule.expression.trim(),
          errorMsg: rule.errorMsg.trim() || '勾稽校验失败',
        },
      })),
  ]
  try {
    await http.put(`/report/template/${row.id}`, {
      templateName: row.templateName,
      periodType: row.periodType,
      deadlineRule: row.deadlineRule,
      deptName: row.deptName,
      businessLine: row.businessLine || 'BUSINESS',
      status: row.status || 'ENABLED',
      fieldsSchema,
      assignees: selectedUserIds.value.length
        ? [{ assignType: 'USER', targetIds: selectedUserIds.value }]
        : [],
    })
    showEdit.value = false
    toast.value = '模板已保存'
    await loadList()
  } catch (err) {
    editError.value = apiError(err)
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
.edit-drawer {
  width: min(880px, calc(100vw - 48px));
  max-height: 86vh;
  overflow: auto;
  padding: 20px;
}
.linkish {
  background: none;
  border: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
  padding: 0;
  text-align: left;
}
.tab-bar {
  display: flex;
  gap: 8px;
  margin: 12px 0;
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
.mini {
  width: 100%;
  margin-bottom: 8px;
}
.mini input,
.mini select {
  width: 100%;
  box-sizing: border-box;
}
.nowrap {
  white-space: nowrap;
}
.rule-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr auto;
  gap: 8px;
  margin-bottom: 8px;
}
.user-line {
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 6px 0;
  font-size: 13px;
}
.req {
  color: #c62828;
}
.field-err {
  margin: 4px 0 0;
  color: #c62828;
  font-size: 12px;
}
.bad {
  border-color: #c62828;
}
</style>
