<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>预警规则</h1>
        <div class="sub">ALERT-001 · 试跑 POST /alert/rule/{id}/trial · 13 ALERT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建规则</button>
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

onMounted(loadList)
</script>
