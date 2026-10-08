<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>上报模板</h1>
        <div class="sub">REPORT-001 · /admin-api/ims/report/template · 09 REPORT</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建模板</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/report/submission')">填报单管理</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      模板字段配置后，上报人按模板逐项填报；提交进入审核流（REPORT-002/003）。
    </p>
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
              <td class="mono num" style="color: var(--blue)">{{ row.templateNo }}</td>
              <td style="font-weight: 500">{{ row.templateName }}</td>
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
                <button class="btn btn-sec btn-sm" type="button" @click="disableRow(row)" :disabled="row.status === 'DISABLED'">
                  停用
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal card" style="max-width: 480px; padding: 20px">
        <h3 style="margin: 0 0 12px">新建上报模板</h3>
        <div class="fld"><label>模板名称</label><input v-model="form.templateName" /></div>
        <div class="fld">
          <label>周期</label>
          <select v-model="form.periodType">
            <option value="DAILY">每日</option>
            <option value="WEEKLY">每周</option>
            <option value="MONTHLY">每月</option>
          </select>
        </div>
        <div class="fld"><label>截止规则</label><input v-model="form.deadlineRule" placeholder="22:00" /></div>
        <div class="fld"><label>责任部门</label><input v-model="form.deptName" placeholder="运营中心" /></div>
        <div class="fld">
          <label>业务线</label>
          <select v-model="form.businessLine">
            <option value="BUSINESS">业务</option>
            <option value="FINANCE">财务</option>
            <option value="ADMIN">行政</option>
          </select>
        </div>
        <div class="fld"><label>示例字段标签</label><input v-model="form.sampleFieldLabel" placeholder="当日 GMV" /></div>
        <div class="acts" style="margin-top: 16px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
        <p v-if="formError" class="hint" style="color: var(--red); margin-top: 8px">{{ formError }}</p>
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
  templateNo: string
  templateName: string
  fieldCount: number
  periodType: string
  deadlineRule: string
  deptName: string
  usageCount: number
  status: string
}

const router = useRouter()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ templateName: '', periodType: '', status: '' })
const form = reactive({
  templateName: '',
  periodType: 'DAILY',
  deadlineRule: '22:00',
  deptName: '',
  businessLine: 'BUSINESS',
  sampleFieldLabel: '当日 GMV',
})

function go(path: string) {
  router.push(path)
}

function periodLabel(period: string, rule: string) {
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

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.templateName) params.templateName = filters.templateName
    if (filters.periodType) params.periodType = filters.periodType
    if (filters.status) params.status = filters.status
    const res = await http.get('/report/template/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    error.value = '网络错误'
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
  form.periodType = 'DAILY'
  form.deadlineRule = '22:00'
  form.deptName = ''
  form.businessLine = 'BUSINESS'
  form.sampleFieldLabel = '当日 GMV'
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  if (!form.templateName.trim()) {
    formError.value = '请填写模板名称'
    return
  }
  const label = form.sampleFieldLabel.trim() || '数值'
  try {
    const res = await http.post('/report/template', {
      templateName: form.templateName.trim(),
      periodType: form.periodType,
      deadlineRule: form.deadlineRule.trim() || '22:00',
      deptName: form.deptName.trim(),
      businessLine: form.businessLine,
      status: 'ENABLED',
      fieldsSchema: [
        {
          fieldKey: 'metric_value',
          fieldLabel: label,
          fieldType: 'NUMBER',
          required: true,
        },
      ],
      assignees: [],
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    showForm.value = false
    await loadList()
  } catch {
    formError.value = '网络错误'
  }
}

async function disableRow(row: Row) {
  if (!confirm(`停用模板「${row.templateName}」？`)) return
  const res = await http.delete(`/report/template/${row.id}`)
  if (res.data.code === 0) await loadList()
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
</style>
