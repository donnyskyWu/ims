<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预警规则</h1>
        <div class="sub">ALERT-001 · 试跑 POST /alert/rule/{id}/trial · 13 ALERT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建规则</button>
        <button class="btn btn-sec btn-sm" type="button" data-testid="alert-hit-open" @click="openHits">命中统计</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/escalate">升级中心</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/stats">统计总览</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/alert/live">实时预警</router-link>
      </div>
    </div>
    <form class="qbar" data-testid="alert-rule-filter" @submit.prevent="loadList">
      <input v-model="filters.ruleName" data-testid="alert-rule-filter-name" placeholder="规则名称" style="width: 160px" />
      <select v-model="filters.level" data-testid="alert-rule-filter-level" style="width: 110px">
        <option value="">全部级别</option>
        <option value="L1">L1</option>
        <option value="L2">L2</option>
        <option value="L3">L3</option>
      </select>
      <select v-model="filters.enabled" data-testid="alert-rule-filter-enabled" style="width: 110px">
        <option value="">全部状态</option>
        <option value="true">已启用</option>
        <option value="false">未启用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="alert-rule-filter-reset" @click="resetFilters">
        重置
      </button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>所属模块</th>
              <th>触发条件</th>
              <th>级别</th>
              <th>升级链</th>
              <th>命中</th>
              <th>启停</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="alert-rule-empty"><div class="et">{{ ruleEmptyText }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.ruleCode }}</td>
              <td style="font-weight: 500">{{ row.ruleName }}</td>
              <td data-testid="alert-rule-module">{{ row.sourceModule || '—' }}</td>
              <td class="mono" data-testid="alert-rule-trigger">{{ row.thresholdExpr || '—' }}</td>
              <td>{{ levelLabel(row.level) }}</td>
              <td data-testid="alert-rule-chain-cell">{{ row.escalationChain || '30/60 分钟 · 严重从二级起跳' }}</td>
              <td class="num" data-testid="alert-rule-hit">{{ row.hitCount }}</td>
              <td>{{ row.enabled ? '启用' : '停用' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="toggle(row)">
                  {{ row.enabled ? '停用' : '启用' }}
                </button>
                <button class="btn btn-txt btn-sm" type="button" data-testid="alert-rule-edit" @click="openEdit(row)">
                  编辑
                </button>
                <button class="btn btn-txt btn-sm" type="button" :disabled="!row.enabled" @click="run(row.id)">
                  试跑
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="toast" class="hint" style="margin-top: 10px">{{ toast }}</p>

    <div v-if="showHits" class="modal-mask" @click.self="showHits = false">
      <div class="card hit-modal" data-testid="alert-hit-modal" style="padding: 20px">
        <h3 style="margin: 0 0 12px">命中统计</h3>
        <form class="qbar" @submit.prevent="loadHits">
          <input v-model="hitStart" data-testid="alert-hit-start" type="date" />
          <input v-model="hitEnd" data-testid="alert-hit-end" type="date" />
          <button class="btn btn-pri btn-sm" type="submit">查询</button>
          <button class="btn btn-sec btn-sm" type="button" data-testid="alert-hit-reset" @click="resetHits">重置</button>
          <span class="sp"></span>
          <button class="btn btn-sec btn-sm" type="button" @click="showHits = false">关闭</button>
        </form>
        <p v-if="hitError" data-testid="alert-hit-error" class="hint" style="color: var(--red)">{{ hitError }}</p>
        <div class="tbl-wrap" style="margin-top: 10px">
          <table>
            <thead>
              <tr>
                <th>规则</th>
                <th>预警数</th>
                <th>响应率</th>
                <th>误报数</th>
                <th>最近命中</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!hitRows.length">
                <td colspan="5"><div class="empty"><div class="et">{{ hitError || '该范围内暂无命中' }}</div></div></td>
              </tr>
              <tr v-for="row in hitRows" v-else :key="row.ruleCode" data-testid="alert-hit-row">
                <td>
                  <div class="mono">{{ row.ruleCode }}</div>
                  <div>{{ row.ruleName }}</div>
                </td>
                <td class="num" data-testid="alert-hit-count">{{ row.alertCount }}</td>
                <td class="num" :style="{ color: row.responseRate < 90 ? 'var(--orange, #d97706)' : undefined }">
                  {{ row.responseRate }}%
                </td>
                <td class="num">
                  {{ row.falseAlarmCount }}
                  <span
                    v-if="row.falseAlarmCount >= 5"
                    data-testid="alert-hit-false-mark"
                    title="连续误报 ≥5 次建议复核阈值（ALR-S-R3）"
                    style="color: var(--orange, #d97706); margin-left: 6px"
                  >
                    复核阈值
                  </span>
                </td>
                <td class="mono">{{ row.lastHitAt ? row.lastHitAt.slice(0, 16) : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="hint">响应率 &lt; 90% 为橙色（BR-112）。钉钉/短信不在本弹窗外发。</p>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 520px; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ editingId ? '编辑预警规则' : '注册预警规则' }}</h3>
        <label class="fld">规则编码</label>
        <input v-model="form.ruleCode" class="fld-in" placeholder="live.data.delay" :readonly="editingId !== null" />
        <p v-if="codeError" data-testid="alert-rule-code-error" class="hint" style="color: var(--red)">{{ codeError }}</p>
        <label class="fld">规则名称 <span class="req">*</span></label>
        <input v-model="form.ruleName" data-testid="alert-rule-name" class="fld-in" />
        <p v-if="nameError" data-testid="alert-rule-name-error" class="hint" style="color: var(--red)">{{ nameError }}</p>
        <label class="fld">预警级别 <span class="req">*</span></label>
        <select v-model.number="form.level" data-testid="alert-rule-level" class="fld-in">
          <option :value="1">L1 提示（黄）</option>
          <option :value="2">L2 警告（橙）</option>
          <option :value="3">L3 严重（红）</option>
        </select>
        <label class="fld">监控对象 <span class="req">*</span></label>
        <select v-model="form.sourceModule" data-testid="alert-rule-object" class="fld-in">
          <option value="">请选择</option>
          <option v-for="item in moduleOptions" :key="item" :value="item">{{ item }}</option>
        </select>
        <p v-if="moduleError" data-testid="alert-rule-object-error" class="hint" style="color: var(--red)">{{ moduleError }}</p>
        <label class="fld">通知方式</label>
        <select v-model="form.notifyMode" data-testid="alert-rule-notify" class="fld-in">
          <option value="IN_APP">站内</option>
          <option value="DINGTALK">钉钉</option>
          <option value="BOTH">站内+钉钉</option>
        </select>
        <label class="fld">规则说明</label>
        <textarea v-model="form.ruleDesc" data-testid="alert-rule-desc" class="fld-in" rows="2" />
        <p class="hint" data-testid="alert-rule-chain">
          升级链：30 分钟责任人 → 再 60 分钟部门负责人 → 三级运营总监 + 系统管理员。严重级从二级起跳。
        </p>
        <label class="fld">触发条件 <span class="req">*</span></label>
        <input v-model="form.thresholdExpr" data-testid="alert-rule-threshold" class="fld-in" placeholder="delayMinutes>30" />
        <p v-if="thresholdError" data-testid="alert-rule-threshold-error" class="hint" style="color: var(--red)">
          {{ thresholdError }}
        </p>
        <p v-if="editingId" class="hint" data-testid="alert-rule-threshold-where">
          阈值在
          <router-link to="/ims/collect/threshold">数据采集 → 阈值规则</router-link>
          配置，保存后即时生效。
        </p>
        <label class="fld">触发条件 DSL</label>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">
          <input v-model="form.dslSource" data-testid="alert-dsl-source" class="fld-in" placeholder="ims_fin_cost" />
          <input v-model="form.dslField" data-testid="alert-dsl-field" class="fld-in" placeholder="hours_since_approve" />
          <input v-model="form.dslOp" data-testid="alert-dsl-op" class="fld-in" placeholder="GT" />
          <input v-model="form.dslValue" data-testid="alert-dsl-value" class="fld-in" placeholder="48" />
        </div>
        <p class="hint">操作符 GT / GTE / LT / LTE / EQ / NEQ。留空则沿用阈值表达式。</p>
        <p data-testid="alert-dsl-preview" class="hint mono">{{ dslPreview }}</p>
        <p v-if="dslError" data-testid="alert-dsl-error" class="hint" style="color: var(--red)">{{ dslError }}</p>
        <label class="fld"><input v-model="form.enabled" type="checkbox" /> 创建后立即启用</label>
        <p v-if="formError" data-testid="alert-rule-form-error" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Row = {
  id: number
  ruleCode: string
  ruleName: string
  level: number
  thresholdExpr: string
  hitCount: number
  enabled: boolean
  sourceModule?: string
  notifyMode?: string
  ruleDesc?: string
  escalationChain?: string
}

const ALL_MODULES = ['账号管理', '证件档案', '工作流', '日报', '会议', '财务核算', '组织人效', '直播管理']

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const codeError = ref('')
const nameError = ref('')
const moduleError = ref('')
const thresholdError = ref('')
const dslError = ref('')
const financeOnly = ref(false)
const filters = reactive({ ruleName: '', level: '', enabled: '' })
const form = reactive({
  ruleCode: '',
  ruleName: '',
  level: 2,
  sourceModule: '直播管理',
  notifyMode: 'IN_APP',
  ruleDesc: '',
  thresholdExpr: '',
  dslSource: '',
  dslField: '',
  dslOp: '',
  dslValue: '',
  enabled: false,
})
const moduleOptions = computed(() => (financeOnly.value ? ['财务核算'] : ALL_MODULES))
const toast = ref('')
const showHits = ref(false)
const hitRows = ref<HitRow[]>([])
const hitError = ref('')
const hitStart = ref('')
const hitEnd = ref('')

type HitRow = {
  ruleCode: string
  ruleName: string
  alertCount: number
  responseRate: number
  falseAlarmCount: number
  lastHitAt: string
}

function bjDate(offsetDays = 0) {
  const now = new Date(Date.now() + offsetDays * 86400000)
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
}

const DSL_OPS = new Set(['GT', 'GTE', 'LT', 'LTE', 'EQ', 'NEQ'])
const IDENT_RE = /^[A-Za-z][A-Za-z0-9_]{0,63}$/
const EXPR_RE = /^[A-Za-z][A-Za-z0-9_]*\s*(>=|<=|==|!=|>|<)\s*-?\d+(\.\d+)?$/

const dslTouched = computed(
  () => !!(form.dslSource.trim() || form.dslField.trim() || form.dslOp.trim() || form.dslValue.trim()),
)

const ruleFilterOn = computed(
  () => !!(filters.ruleName.trim() || filters.level || filters.enabled),
)
const ruleEmptyText = computed(() =>
  error.value || (ruleFilterOn.value ? '当前筛选条件下暂无规则。当前筛选下暂无规则' : '暂无规则'),
)

const dslPreview = computed(() => {
  if (!dslTouched.value) return 'DSL 预览：未填写'
  return `DSL 预览：${JSON.stringify(buildTriggerConfig())}`
})

function buildTriggerConfig() {
  const raw = form.dslValue.trim()
  const num = Number(raw)
  const value = raw !== '' && !Number.isNaN(num) ? num : raw
  return {
    source: form.dslSource.trim(),
    condition: {
      field: form.dslField.trim(),
      op: form.dslOp.trim(),
      value,
    },
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.ruleName.trim()) params.ruleName = filters.ruleName.trim()
    if (filters.level) params.level = filters.level
    if (filters.enabled === 'true') params.enabled = true
    if (filters.enabled === 'false') params.enabled = false
    const res = await http.get('/alert/rule/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    financeOnly.value = !!res.data.data?.financeOnly
    rows.value = res.data.data?.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.ruleName = ''
  filters.level = ''
  filters.enabled = ''
  loadList()
}

function levelLabel(level: number) {
  const names: Record<number, string> = { 1: 'L1 提示（黄）', 2: 'L2 警告（橙）', 3: 'L3 严重（红）' }
  return names[level] || `L${level}`
}

function resetForm() {
  form.ruleCode = ''
  form.ruleName = ''
  form.level = 2
  form.sourceModule = financeOnly.value ? '财务核算' : '直播管理'
  form.notifyMode = 'IN_APP'
  form.ruleDesc = ''
  form.thresholdExpr = ''
  form.dslSource = ''
  form.dslField = ''
  form.dslOp = ''
  form.dslValue = ''
  form.enabled = false
  formError.value = ''
  codeError.value = ''
  nameError.value = ''
  moduleError.value = ''
  thresholdError.value = ''
  dslError.value = ''
}

function validateForm() {
  nameError.value = ''
  moduleError.value = ''
  thresholdError.value = ''
  formError.value = ''
  codeError.value = ''
  dslError.value = ''
  const name = form.ruleName.trim()
  let ok = true
  if (!name) {
    nameError.value = '必填项，请填写'
    ok = false
  }
  if (!form.sourceModule) {
    moduleError.value = '必填项，请填写'
    ok = false
  }
  if (!ok) return false
  const expr = form.thresholdExpr.trim()
  if (!expr && !dslTouched.value) {
    thresholdError.value = '必填项，请填写'
    return false
  }
  if (expr && !dslTouched.value && !EXPR_RE.test(expr)) {
    thresholdError.value = '阈值表达式须为字段、比较符和数字，例如 delayMinutes>30'
    return false
  }
  if (!dslTouched.value) return true
  const source = form.dslSource.trim()
  const field = form.dslField.trim()
  const op = form.dslOp.trim().toUpperCase()
  const raw = form.dslValue.trim()
  if (!source || !field || !form.dslOp.trim() || raw === '') {
    dslError.value = '触发条件未填完整（1009）'
    return false
  }
  if (!IDENT_RE.test(source) || !IDENT_RE.test(field)) {
    dslError.value = '数据源或字段名非法（1009）'
    return false
  }
  if (!DSL_OPS.has(op)) {
    dslError.value = '操作符非法（1009），允许 GT、GTE、LT、LTE、EQ、NEQ'
    return false
  }
  if (!/^-?\d+(\.\d+)?$/.test(raw)) {
    dslError.value = '条件值须为数字（1009）'
    return false
  }
  form.dslOp = op
  return true
}

function openCreate() {
  editingId.value = null
  resetForm()
  showForm.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  resetForm()
  form.ruleCode = row.ruleCode
  form.ruleName = row.ruleName
  form.level = row.level || 2
  form.sourceModule = row.sourceModule || (financeOnly.value ? '财务核算' : '直播管理')
  form.notifyMode = row.notifyMode || 'IN_APP'
  form.ruleDesc = row.ruleDesc || ''
  form.thresholdExpr = row.thresholdExpr || ''
  form.enabled = row.enabled
  showForm.value = true
}

async function submitCreate() {
  if (!validateForm()) return
  const payload: Record<string, unknown> = {
    ruleName: form.ruleName,
    level: form.level,
    sourceModule: form.sourceModule,
    notifyMode: form.notifyMode,
    ruleDesc: form.ruleDesc,
    thresholdExpr: form.thresholdExpr,
    enabled: form.enabled,
  }
  if (!editingId.value) payload.ruleCode = form.ruleCode
  if (dslTouched.value) payload.triggerConfig = buildTriggerConfig()
  try {
    const res = editingId.value
      ? await http.put(`/alert/rule/${editingId.value}`, payload)
      : await http.post('/alert/rule', payload)
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    const edited = editingId.value !== null
    showForm.value = false
    editingId.value = null
    toast.value = edited ? '阈值已即时生效（热更新）' : '预警规则创建成功'
    await loadList()
  } catch (error) {
    const body = error as { code?: number; msg?: string }
    const msg = body?.msg || errorMessage(error)
    if (body?.code === 1009 && msg.includes('thresholdExpr')) {
      thresholdError.value = '阈值表达式须为字段、比较符和数字，例如 delayMinutes>30'
    } else if (body?.code === 1009) dslError.value = msg
    else if (body?.code === 1165 && msg.includes('规则名称')) nameError.value = msg
    else if (body?.code === 1165) codeError.value = msg
    else if (body?.code === 1001 && msg.includes('ruleName')) nameError.value = '规则名称不能为空'
    else formError.value = msg
  }
}

async function toggle(row: Row) {
  const enabling = !row.enabled
  try {
    const res = await http.put(`/alert/rule/${row.id}/enable`, null, { params: { enabled: enabling } })
    if (res.data.code !== 0) {
      toast.value = res.data.msg || '操作失败'
      return
    }
    toast.value = enabling ? '规则已启用' : '规则已停用'
    await loadList()
  } catch (error) {
    toast.value = errorMessage(error)
  }
}

async function run(ruleId: number) {
  toast.value = ''
  try {
    const res = await http.post(`/alert/rule/${ruleId}/trial`)
    if (res.data.code !== 0) {
      toast.value = res.data.msg || '试跑失败'
      return
    }
    const alertNo = res.data.data?.alertNo
    toast.value = alertNo ? `试跑成功，预警号 ${alertNo}` : '试跑成功'
    await loadList()
  } catch {
    toast.value = '网络错误'
  }
}

function resetHits() {
  hitStart.value = ''
  hitEnd.value = ''
  hitError.value = ''
  loadHits()
}

function openHits() {
  hitStart.value = bjDate(-29)
  hitEnd.value = bjDate(0)
  showHits.value = true
  loadHits()
}

async function loadHits() {
  hitError.value = ''
  const params: Record<string, string> = {}
  if (hitStart.value || hitEnd.value) {
    if (!hitStart.value || !hitEnd.value) {
      hitError.value = '请同时填写起止日期'
      hitRows.value = []
      return
    }
    if (hitStart.value > hitEnd.value) {
      hitError.value = '起始日期不能晚于结束日期'
      hitRows.value = []
      return
    }
    params.dateRange = `${hitStart.value},${hitEnd.value}`
  }
  try {
    const res = await http.get('/alert/rule/hit-stats', { params })
    hitRows.value = res.data.data || []
  } catch (error) {
    hitError.value = errorMessage(error)
    hitRows.value = []
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
.req {
  color: var(--red);
}
.hit-modal {
  width: 800px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 48px);
  overflow: auto;
}
</style>
