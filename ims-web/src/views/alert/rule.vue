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
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.ruleName" placeholder="规则名称" style="width: 160px" />
      <select v-model="filters.enabled" style="width: 110px">
        <option value="">全部状态</option>
        <option value="true">已启用</option>
        <option value="false">未启用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编码</th>
              <th>名称</th>
              <th>级别</th>
              <th>阈值/表达式</th>
              <th>命中</th>
              <th>启停</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无规则' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.ruleCode }}</td>
              <td style="font-weight: 500">{{ row.ruleName }}</td>
              <td class="num">L{{ row.level }}</td>
              <td class="mono">{{ row.thresholdExpr || '—' }}</td>
              <td class="num">{{ row.hitCount }}</td>
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
          <span class="sp"></span>
          <button class="btn btn-sec btn-sm" type="button" @click="showHits = false">关闭</button>
        </form>
        <p v-if="hitError" class="hint" style="color: var(--red)">{{ hitError }}</p>
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
        <label class="fld">规则名称</label>
        <input v-model="form.ruleName" class="fld-in" />
        <label class="fld">阈值表达式</label>
        <input v-model="form.thresholdExpr" class="fld-in" placeholder="delayMinutes>30" />
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
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const codeError = ref('')
const dslError = ref('')
const filters = reactive({ ruleName: '', enabled: '' })
const form = reactive({
  ruleCode: '',
  ruleName: '',
  thresholdExpr: '',
  dslSource: '',
  dslField: '',
  dslOp: '',
  dslValue: '',
  enabled: false,
})
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

const dslTouched = computed(
  () => !!(form.dslSource.trim() || form.dslField.trim() || form.dslOp.trim() || form.dslValue.trim()),
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
    if (filters.ruleName) params.ruleName = filters.ruleName
    if (filters.enabled === 'true') params.enabled = true
    if (filters.enabled === 'false') params.enabled = false
    const res = await http.get('/alert/rule/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.ruleCode = ''
  form.ruleName = ''
  form.thresholdExpr = ''
  form.dslSource = ''
  form.dslField = ''
  form.dslOp = ''
  form.dslValue = ''
  form.enabled = false
  formError.value = ''
  codeError.value = ''
  dslError.value = ''
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
  form.thresholdExpr = row.thresholdExpr || ''
  form.enabled = row.enabled
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  codeError.value = ''
  dslError.value = ''
  const payload: Record<string, unknown> = {
    ruleName: form.ruleName,
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
    if (edited) toast.value = '阈值已即时生效（热更新）'
    await loadList()
  } catch (error) {
    const body = error as { code?: number; msg?: string }
    const msg = body?.msg || errorMessage(error)
    if (body?.code === 1009) dslError.value = msg
    else if (body?.code === 1165) codeError.value = msg
    else formError.value = msg
  }
}

async function toggle(row: Row) {
  await http.put(`/alert/rule/${row.id}/enable`, null, { params: { enabled: !row.enabled } })
  await loadList()
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
.hit-modal {
  width: 800px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 48px);
  overflow: auto;
}
</style>
