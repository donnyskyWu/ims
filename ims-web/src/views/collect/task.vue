<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>采集任务</h1>
        <div class="sub">UX-M10 P-M10-001/002 · Channel-A/B/C/D · 16 COLLECT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="ensureUnified">确保统一任务</button>
        <button class="btn btn-sec btn-sm" type="button" @click="ensureExternal">确保外部统一任务</button>
        <button class="btn btn-sec btn-sm" type="button" @click="goDouyin">抖音内部账号</button>
        <button class="btn btn-sec btn-sm" type="button" @click="goKuaishou">快手内部账号</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增单账号任务</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      Channel-A 默认租户级统一采集（02:00）；Channel-D 外部竞品统一任务（22:00）。编辑抽屉<strong>无 Cookie</strong>，凭证见公司资产账号 · 采集 Tab（ADR-047）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.taskName" placeholder="任务名" style="width: 140px" />
      <select v-model="filters.platformType" style="width: 110px">
        <option value="">全部平台</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filters.method" style="width: 110px">
        <option value="">全部方式</option>
        <option value="INTERNAL">INTERNAL</option>
        <option value="EXTERNAL">EXTERNAL</option>
      </select>
      <select v-model="filters.frequency" style="width: 100px">
        <option value="">全部频率</option>
        <option value="HOURLY">HOURLY</option>
        <option value="DAILY">DAILY</option>
        <option value="WEEKLY">WEEKLY</option>
      </select>
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="ENABLED">ENABLED</option>
        <option value="DISABLED">DISABLED</option>
        <option value="RUNNING">RUNNING</option>
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
              <th>任务名</th>
              <th>平台/账号</th>
              <th>方式</th>
              <th>频率</th>
              <th>Cron</th>
              <th>最近执行</th>
              <th>成功/失败</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9"><div class="empty"><div class="et">{{ error || '暂无采集任务' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td>
                {{ row.taskName }}
                <span v-if="row.isUnified" class="chip" style="margin-left: 4px">统一</span>
                <span v-if="row.isExternalUnified" class="chip" style="margin-left: 4px">外部统一</span>
                <div v-if="row.bindWarning" class="hint" style="color: var(--orange)">{{ row.bindWarning }}</div>
              </td>
              <td style="font-size: 12px">{{ row.platformAccountLabel || '—' }}</td>
              <td><span class="chip">{{ row.method }}</span></td>
              <td class="num">{{ row.frequency }}</td>
              <td class="mono" style="font-size: 11px">{{ row.cron }}</td>
              <td class="num" style="font-size: 11px">{{ row.lastRunAt || '—' }}</td>
              <td class="num">
                <span style="color: var(--green)">{{ row.successCount }}</span> /
                <span style="color: var(--red)">{{ row.failCount }}</span>
              </td>
              <td>{{ row.status }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="runTask(row)">立即执行</button>
                <button class="btn-txt btn" type="button" @click="goLogs(row)">日志</button>
                <button
                  v-if="!row.isUnified && !row.isExternalUnified"
                  class="btn-txt btn"
                  type="button"
                  @click="openEdit(row)"
                >
                  编辑
                </button>
                <button
                  v-if="!row.isUnified && !row.isExternalUnified"
                  class="btn-txt btn btn-danger-txt"
                  type="button"
                  @click="removeTask(row)"
                >
                  删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer v-model="drawerOpen" :title="editingId ? '编辑任务' : '新增单账号任务'" width="480px">
      <form class="drawer-form" @submit.prevent="saveTask">
        <label>任务名<input v-model="form.taskName" required /></label>
        <label>
          平台
          <select v-model="form.platformType" required>
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
        </label>
        <label>
          账号 ID（AccountSelect · 单账号）
          <input v-model.number="form.accountId" type="number" placeholder="oa_platform_account.id" required />
        </label>
        <label>
          频率
          <select v-model="form.frequency" required>
            <option value="HOURLY">HOURLY</option>
            <option value="DAILY">DAILY</option>
            <option value="WEEKLY">WEEKLY</option>
          </select>
        </label>
        <label>Cron<input v-model="form.cron" required placeholder="0 2 * * *" /></label>
        <label>
          状态
          <select v-model="form.status">
            <option value="ENABLED">ENABLED</option>
            <option value="DISABLED">DISABLED</option>
          </select>
        </label>
        <p class="hint">本表单不含 Cookie/Token；Channel-D 外部任务请用 API 指定 collectConfigId。</p>
        <p v-if="saveWarning" class="hint" style="color: var(--orange)">{{ saveWarning }}</p>
        <div class="drawer-actions">
          <button class="btn btn-sec" type="button" @click="drawerOpen = false">取消</button>
          <button class="btn btn-pri" type="submit">保存</button>
        </div>
      </form>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const router = useRouter()
const platforms = ['DOUYIN', 'KUAISHOU', 'WECHAT_CHANNELS', 'WECHAT_OFFICIAL', 'XIAOHONGSHU']
const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const drawerOpen = ref(false)
const editingId = ref('')
const saveWarning = ref('')

const filters = reactive({
  taskName: '',
  platformType: '',
  method: '',
  frequency: '',
  status: '',
})

const form = reactive({
  taskName: '',
  platformType: 'DOUYIN',
  accountId: undefined as number | undefined,
  frequency: 'DAILY',
  cron: '0 2 * * *',
  status: 'ENABLED',
})

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.taskName.trim()) params.taskName = filters.taskName.trim()
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.method) params.method = filters.method
    if (filters.frequency) params.frequency = filters.frequency
    if (filters.status) params.status = filters.status
    const res = await http.get('/collect/task/page', { params })
    rows.value = res.data?.data?.list || []
    total.value = res.data?.data?.total || 0
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.taskName = ''
  filters.platformType = ''
  filters.method = ''
  filters.frequency = ''
  filters.status = ''
  loadList()
}

function openCreate() {
  editingId.value = ''
  saveWarning.value = ''
  form.taskName = ''
  form.platformType = 'DOUYIN'
  form.accountId = undefined
  form.frequency = 'DAILY'
  form.cron = '0 2 * * *'
  form.status = 'ENABLED'
  drawerOpen.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  saveWarning.value = row.bindWarning || ''
  form.taskName = row.taskName
  form.platformType = row.platformType
  form.accountId = row.accountId ? Number(row.accountId) : undefined
  form.frequency = row.frequency
  form.cron = row.cron
  form.status = row.status
  drawerOpen.value = true
}

async function saveTask() {
  saveWarning.value = ''
  const body = {
    taskName: form.taskName,
    platformType: form.platformType,
    accountId: form.accountId,
    frequency: form.frequency,
    cron: form.cron,
    status: form.status,
  }
  try {
    const res = editingId.value
      ? await http.put(`/collect/task/${editingId.value}`, body)
      : await http.post('/collect/task', body)
    if (res.data?.data?.bindWarning) saveWarning.value = res.data.data.bindWarning
    drawerOpen.value = false
    await loadList()
  } catch (e: unknown) {
    saveWarning.value = errorMessage(e)
  }
}

async function runTask(row: any) {
  try {
    const res = await http.post(`/collect/task/${row.id}/run`)
    const logId = res.data?.data?.logId
    router.push({ path: '/ims/collect/log', query: { taskId: row.id, logId } })
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
}

function goLogs(row: any) {
  router.push({ path: '/ims/collect/log', query: { taskId: row.id } })
}

function goDouyin() {
  router.push('/ims/collect/douyin')
}
function goKuaishou() {
  router.push('/ims/collect/kuaishou')
}

async function removeTask(row: any) {
  if (!confirm(`删除任务「${row.taskName}」？`)) return
  await http.delete(`/collect/task/${row.id}`)
  loadList()
}

async function ensureUnified() {
  await http.post('/collect/task/ensure-unified', { platformType: filters.platformType || 'DOUYIN' })
  loadList()
}

async function ensureExternal() {
  await http.post('/collect/task/ensure-external-unified', {})
  loadList()
}

loadList()
</script>

<style scoped>
.drawer-form label {
  display: block;
  margin-bottom: 12px;
  font-size: 13px;
}
.drawer-form input,
.drawer-form select {
  display: block;
  width: 100%;
  margin-top: 4px;
}
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
