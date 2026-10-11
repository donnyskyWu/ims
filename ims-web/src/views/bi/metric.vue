<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>指标管理</h1>
        <div class="sub">FR-M6-001 · /ims/bi/metric · 17a BI0</div>
      </div>
      <div class="acts">
        <button v-if="showResultQuery" class="btn btn-sec btn-sm" type="button" data-testid="bi-metric-result-query" @click="showHistory = true">结果查询</button>
        <button v-if="showExport" class="btn btn-sec btn-sm" type="button" data-testid="bi-metric-export" @click="exportCsv">导出</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建指标</button>
      </div>
    </div>

    <p v-if="pageMsg" class="hint" data-testid="bi-metric-toast">{{ pageMsg }}</p>

    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" data-testid="bi-metric-keyword" placeholder="指标名称/编码" style="width: 160px" />
      <select v-model="filters.metricType" style="width: 130px">
        <option value="">全部类型</option>
        <option value="BASIC">基础指标</option>
        <option value="COMPOSITE">复合指标</option>
      </select>
      <select v-model="filters.category" style="width: 120px">
        <option value="">全部分类</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">启用</option>
        <option value="DISABLED">停用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="bi-metric-search">查询</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>指标名称</th>
              <th>指标编码</th>
              <th>类型</th>
              <th>分类</th>
              <th>数据源</th>
              <th>计算公式</th>
              <th>计算频率</th>
              <th>单位</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="11"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-else-if="!rows.length">
              <td colspan="11"><div class="empty" data-testid="bi-metric-empty"><div class="et">{{ emptyText }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="num">{{ row.id }}</td>
              <td style="font-weight: 500">{{ row.metricName }}</td>
              <td class="mono">{{ row.metricCode }}</td>
              <td>{{ row.metricType === 'COMPOSITE' ? '复合' : '基础' }}</td>
              <td>{{ row.category }}</td>
              <td class="mono">{{ row.dataSource || '—' }}</td>
              <td class="mono" style="font-size: 11px; max-width: 220px">{{ row.formula || '—' }}</td>
              <td>{{ freqLabel(row.calcFreq) }}</td>
              <td>{{ row.unit || '—' }}</td>
              <td>{{ row.status === 'ENABLED' ? '启用' : '停用' }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openEdit(row)">编辑</button>
                <button class="btn btn-sec btn-sm" type="button" @click="toggleStatus(row)">{{ row.status === 'ENABLED' ? '停用' : '启用' }}</button>
                <button class="btn btn-sec btn-sm" type="button" @click="preview(row.id)">试算</button>
                <button class="btn btn-sec btn-sm" type="button" @click="remove(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="previewResult" class="card hint" data-testid="bi-metric-preview-result" style="margin-top: 12px; padding: 12px">
      试算 · {{ previewResult.metricName }} = {{ previewResult.value }} {{ previewResult.unit }}
      <span v-if="previewResult.note" class="csub">（{{ previewResult.note }}）</span>
    </div>
    <p v-if="previewError" class="hint" data-testid="bi-metric-preview-error" style="color: var(--red)">{{ previewError }}</p>

    <div v-if="showHistory" class="modal-mask" @click.self="showHistory = false">
      <div class="card" style="width: 480px; padding: 20px" data-testid="bi-metric-history">
        <h3 style="margin: 0 0 12px">结果历史查询</h3>
        <p>本期不做结果历史查询（DW mt-result）。替代能力为报表中心 / 数据报表。</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showHistory = false">关闭</button>
          <router-link class="btn btn-pri btn-sm" to="/ims/bi/report/list" @click="showHistory = false">前往数据报表</router-link>
        </div>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 760px; max-height: 86vh; overflow: auto; padding: 20px">
        <h3 style="margin: 0 0 12px">{{ editingId ? '编辑指标' : '新建指标' }}</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <div>
            <label class="fld">指标名称*</label>
            <input v-model="form.metricName" class="fld-in" data-testid="bi-metric-name" maxlength="51" placeholder="1-50字" />
            <p v-if="errors.name" class="hint" data-testid="bi-metric-name-error" style="color: var(--red)">{{ errors.name }}</p>
          </div>
          <div>
            <label class="fld">指标编码*</label>
            <input v-model="form.metricCode" class="fld-in" data-testid="bi-metric-code" placeholder="英文+下划线" />
            <p v-if="errors.code" class="hint" data-testid="bi-metric-code-error" style="color: var(--red)">{{ errors.code }}</p>
          </div>
          <div>
            <label class="fld">指标类型*</label>
            <select v-model="form.metricType" class="fld-in" data-testid="bi-metric-type">
              <option value="BASIC">基础指标 BASIC</option>
              <option value="COMPOSITE">复合指标 COMPOSITE</option>
            </select>
          </div>
          <div>
            <label class="fld">分类</label>
            <select v-model="form.category" class="fld-in">
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div>
            <label class="fld">单位</label>
            <input v-model="form.unit" class="fld-in" data-testid="bi-metric-unit" placeholder="如：次 / % / 元" />
          </div>
          <div>
            <label class="fld">计算频率</label>
            <select v-model="form.calcFreq" class="fld-in" data-testid="bi-metric-freq">
              <option value="REALTIME">实时</option>
              <option value="DAILY">每日</option>
              <option value="WEEKLY">每周</option>
              <option value="MONTHLY">每月</option>
            </select>
          </div>
        </div>

        <template v-if="form.metricType === 'BASIC'">
          <label class="fld">数据源</label>
          <select v-model="form.dataSource" class="fld-in" data-testid="bi-metric-source">
            <option v-for="src in sources" :key="src.value" :value="src.value">{{ src.label }}</option>
          </select>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0 12px">
            <div>
              <label class="fld">计算方式</label>
              <select v-model="form.calcMethod" class="fld-in" data-testid="bi-metric-method">
                <option v-for="m in methods" :key="m.value" :value="m.value">{{ m.label }}</option>
              </select>
            </div>
            <div>
              <label class="fld">计算字段</label>
              <select v-model="form.calcField" class="fld-in" data-testid="bi-metric-calc-field">
                <option v-for="f in numberFields" :key="f.name" :value="f.name">{{ f.label }} ({{ f.name }})</option>
              </select>
            </div>
            <div>
              <label class="fld">汇总字段</label>
              <select v-model="form.summaryField" class="fld-in" data-testid="bi-metric-summary">
                <option v-for="f in fields" :key="f.name" :value="f.name">{{ f.label }} ({{ f.name }})</option>
              </select>
            </div>
          </div>
          <div class="fld">查询条件</div>
          <table>
            <thead><tr><th>字段</th><th>运算符</th><th>参数</th><th>值</th><th></th></tr></thead>
            <tbody>
              <tr v-for="(cond, idx) in form.conditions" :key="idx">
                <td>
                  <select v-model="cond.field">
                    <option v-for="f in fields" :key="f.name" :value="f.name">{{ f.label }}</option>
                  </select>
                </td>
                <td>
                  <select v-model="cond.op">
                    <option v-for="op in operators" :key="op" :value="op">{{ op }}</option>
                  </select>
                </td>
                <td><input v-model="cond.param" type="checkbox" data-testid="bi-metric-cond-param" /></td>
                <td><input v-model="cond.value" placeholder="值" /></td>
                <td><button class="btn btn-sec btn-sm" type="button" @click="removeCond(idx)">删除</button></td>
              </tr>
            </tbody>
          </table>
          <p v-if="condMsg" class="hint" data-testid="bi-metric-cond-error" style="color: var(--red)">{{ condMsg }}</p>
          <button class="btn btn-sec btn-sm" type="button" data-testid="bi-metric-add-cond" @click="addCond">+ 添加条件</button>
          <div class="acts" style="margin: 12px 0">
            <button class="btn btn-pri btn-sm" type="button" data-testid="bi-metric-gen" @click="generateFormula">生成公式</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="bi-metric-preview-data" @click="previewDraft">预览数据</button>
          </div>
        </template>

        <label class="fld">{{ form.metricType === 'COMPOSITE' ? '计算公式' : '计算公式（SQL 预览）' }}</label>
        <textarea v-model="form.formula" class="fld-in" data-testid="bi-metric-formula" rows="4" :placeholder="form.metricType === 'COMPOSITE' ? '如 INTERACTION_COUNT / TC_PLAY * 100' : '点击「生成公式」或手动编辑 SQL'" />
        <p v-if="form.metricType === 'BASIC'" class="hint">仅允许 SELECT。勾选「参数」的条件写入 params_json。</p>
        <p v-else class="hint">只允许指标编码、白名单函数（SUM/AVG/COUNT/MAX/MIN）和四则运算。</p>

        <div v-if="draftRows.length" data-testid="bi-metric-draft-table" style="margin-top: 8px">
          <div style="font-weight: 600; margin-bottom: 6px">预览结果（最多 20 行）</div>
          <table>
            <thead><tr><th>ip_group_name</th><th>metric_value</th></tr></thead>
            <tbody>
              <tr v-for="(line, idx) in draftRows" :key="idx">
                <td>{{ line.ip_group_name }}</td>
                <td class="num">{{ line.metric_value }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="formError" class="hint" data-testid="bi-metric-form-error" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitForm">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Cond = { field: string; op: string; value: string; param: boolean }
type Row = {
  id: number
  metricCode: string
  metricName: string
  metricType: string
  category: string
  calcFreq: string
  status: string
  formula: string
  unit: string
  dataSource: string
  calcMethod: string
  calcField: string
  summaryField: string
  conditions: Cond[]
  refCount: number
}

const categories = ['内容表现', '账号经营', '经营转化', '财务效率']
const sources = [
  { value: 'oa_content_metric', label: '内容指标' },
  { value: 'oa_content', label: '内容' },
  { value: 'oa_ip_group', label: 'IP 组' },
  { value: 'oa_platform_account', label: '平台账号' },
  { value: 'oa_live_session', label: '直播场次' },
]
const methods = [
  { value: 'SUM', label: '求和 SUM' },
  { value: 'COUNT', label: '计数 COUNT' },
  { value: 'AVG', label: '平均 AVG' },
  { value: 'MAX', label: '最大值 MAX' },
  { value: 'MIN', label: '最小值 MIN' },
  { value: 'DISTINCT_COUNT', label: '去重计数' },
]
const fields = [
  { name: 'ip_group_name', label: 'IP 组名称' },
  { name: 'play_count', label: '播放量' },
  { name: 'interaction_count', label: '互动量' },
  { name: 'stat_date', label: '统计日期' },
  { name: 'platform_code', label: '平台' },
]
const numberFields = fields.filter((f) => f.name !== 'ip_group_name' && f.name !== 'platform_code' && f.name !== 'stat_date')
const operators = ['等于 =', '不等于 !=', '大于 >', '大于等于 >=', '小于 <', '小于等于 <=', '包含 LIKE', '介于']

const showResultQuery = true
const showExport = true

const rows = ref<Row[]>([])
const loading = ref(false)
const showForm = ref(false)
const showHistory = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const condMsg = ref('')
const pageMsg = ref('')
const previewError = ref('')
const previewResult = ref<{ metricName: string; value: number; unit: string; note: string } | null>(null)
const draftRows = ref<{ ip_group_name: string; metric_value: number }[]>([])
const filters = reactive({ keyword: '', metricType: '', category: '', status: '' })
const listFiltered = ref(false)
const emptyText = computed(() => (listFiltered.value ? '当前筛选下暂无指标' : '暂无指标'))
const errors = reactive({ name: '', code: '' })
const form = reactive({
  metricName: '',
  metricCode: '',
  metricType: 'BASIC',
  category: '内容表现',
  unit: '',
  calcFreq: 'DAILY',
  dataSource: 'oa_content_metric',
  calcMethod: 'SUM',
  calcField: 'play_count',
  summaryField: 'ip_group_name',
  formula: '',
  conditions: [] as Cond[],
})

function blankCond(): Cond {
  return { field: 'stat_date', op: '介于', value: '', param: false }
}

function freqLabel(freq: string) {
  const map: Record<string, string> = { REALTIME: '实时', DAILY: '每日', WEEKLY: '每周', MONTHLY: '每月', DAY: '每日' }
  return map[freq] || freq
}

function resetForm() {
  form.metricName = ''
  form.metricCode = ''
  form.metricType = 'BASIC'
  form.category = '内容表现'
  form.unit = ''
  form.calcFreq = 'DAILY'
  form.dataSource = 'oa_content_metric'
  form.calcMethod = 'SUM'
  form.calcField = 'play_count'
  form.summaryField = 'ip_group_name'
  form.formula = ''
  form.conditions = [blankCond()]
  errors.name = ''
  errors.code = ''
  formError.value = ''
  condMsg.value = ''
  draftRows.value = []
}

async function loadList() {
  loading.value = true
  try {
    const res = await http.get('/bi/metric/list', {
      params: {
        keyword: filters.keyword || undefined,
        metricType: filters.metricType || undefined,
        category: filters.category || undefined,
        status: filters.status || undefined,
        pageNo: 1,
        pageSize: 50,
      },
    })
    if (res.data.code === 0) {
      rows.value = res.data.data.list || []
      listFiltered.value = Boolean(filters.keyword.trim() || filters.metricType || filters.category || filters.status)
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  resetForm()
  showForm.value = true
}

function openEdit(row: Row) {
  editingId.value = row.id
  resetForm()
  form.metricName = row.metricName
  form.metricCode = row.metricCode
  form.metricType = row.metricType
  form.category = row.category || '内容表现'
  form.unit = row.unit || ''
  form.calcFreq = row.calcFreq === 'DAY' ? 'DAILY' : row.calcFreq || 'DAILY'
  form.dataSource = row.dataSource || 'oa_content_metric'
  form.calcMethod = row.calcMethod || 'SUM'
  form.calcField = row.calcField || 'play_count'
  form.summaryField = row.summaryField || 'ip_group_name'
  form.formula = row.formula || ''
  form.conditions = row.conditions?.length ? row.conditions.map((c) => ({ ...c })) : [blankCond()]
  showForm.value = true
}

function addCond() {
  form.conditions.push(blankCond())
  condMsg.value = ''
}

function removeCond(idx: number) {
  if (form.conditions.length <= 1) {
    condMsg.value = '至少保留一个条件行'
    return
  }
  form.conditions.splice(idx, 1)
  condMsg.value = ''
}

function payload() {
  return {
    metricName: form.metricName.trim(),
    metricCode: form.metricCode.trim(),
    metricType: form.metricType,
    category: form.category,
    unit: form.unit.trim(),
    calcFreq: form.calcFreq,
    dataSource: form.dataSource,
    calcMethod: form.calcMethod,
    calcField: form.calcField,
    summaryField: form.summaryField,
    formula: form.formula.trim(),
    conditions: form.conditions,
  }
}

async function generateFormula() {
  formError.value = ''
  try {
    const res = await http.post('/bi/metric/formula/generate', payload())
    form.formula = res.data.data.formula || ''
    pageMsg.value = '公式已生成'
  } catch (error: unknown) {
    formError.value = errorMessage(error)
  }
}

async function previewDraft() {
  formError.value = ''
  draftRows.value = []
  try {
    const res = await http.post('/bi/metric/preview-draft', payload())
    draftRows.value = res.data.data.rows || []
    if (res.data.data.formula) form.formula = res.data.data.formula
  } catch (error: unknown) {
    formError.value = errorMessage(error)
  }
}

function validateClient() {
  errors.name = ''
  errors.code = ''
  const name = form.metricName.trim()
  if (!name) errors.name = '必填项，请填写'
  else if (name.length > 50) errors.name = '指标名称不超过 50 字'
  if (!form.metricCode.trim()) errors.code = '必填项，请填写'
  return !errors.name && !errors.code
}

async function submitForm() {
  formError.value = ''
  if (!validateClient()) return
  const body = payload()
  try {
    const res = editingId.value
      ? await http.put(`/bi/metric/${editingId.value}`, body)
      : await http.post('/bi/metric', body)
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    showForm.value = false
    pageMsg.value = '指标已保存'
    await loadList()
  } catch (error: unknown) {
    const msg = errorMessage(error)
    if (msg.includes('编码已存在')) errors.code = msg
    else if (msg.includes('50')) errors.name = msg
    else formError.value = msg
  }
}

async function toggleStatus(row: Row) {
  pageMsg.value = ''
  const next = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  try {
    await http.put(`/bi/metric/${row.id}`, { status: next })
    pageMsg.value = next === 'ENABLED' ? '已启用' : '已停用'
    await loadList()
  } catch (error: unknown) {
    pageMsg.value = errorMessage(error)
  }
}

async function preview(id: number) {
  previewError.value = ''
  previewResult.value = null
  try {
    const res = await http.post(`/bi/metric/${id}/preview`, {})
    if (res.data.code === 0) previewResult.value = res.data.data
    else previewError.value = res.data.msg || '试算失败'
  } catch (error: unknown) {
    previewError.value = errorMessage(error)
  }
}

async function remove(row: Row) {
  pageMsg.value = ''
  if (!window.confirm(`确认删除指标「${row.metricName}」？`)) return
  try {
    await http.delete(`/bi/metric/${row.id}`)
    pageMsg.value = '指标已删除'
    await loadList()
  } catch (error: unknown) {
    pageMsg.value = errorMessage(error)
  }
}

async function exportCsv() {
  pageMsg.value = ''
  try {
    const res = await http.get('/bi/metric/export', {
      params: {
        keyword: filters.keyword || undefined,
        metricType: filters.metricType || undefined,
        category: filters.category || undefined,
        status: filters.status || undefined,
      },
    })
    const csv = String(res.data.data.csv || '')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = res.data.data.filename || '指标.csv'
    link.click()
    URL.revokeObjectURL(url)
    pageMsg.value = `已导出 ${res.data.data.count || 0} 条`
  } catch (error: unknown) {
    pageMsg.value = errorMessage(error)
  }
}

onMounted(loadList)
</script>
