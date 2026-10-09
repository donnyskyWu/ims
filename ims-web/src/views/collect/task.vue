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
        <button class="btn btn-sec btn-sm" type="button" @click="goWechatChannels">视频号内部账号</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增单账号任务</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      Channel-A 默认租户级统一采集（02:00）；Channel-D 外部竞品统一任务（22:00）。启动后按「下次执行」由本地定时器触发，停止后不再调度。编辑抽屉<strong>无 Cookie</strong>，凭证见公司资产账号 · 采集 Tab（ADR-047）。失败日志在采集日志页重试，不依赖真实快手引擎。
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
              <th>下次执行</th>
              <th>健康</th>
              <th>成功/失败</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="11"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="11">
                <div class="empty" data-testid="task-empty">
                  <div class="et">{{ error || (filtersActive ? '没有符合筛选的采集任务' : '暂无采集任务') }}</div>
                  <div class="es">{{ filtersActive ? '换个条件，或重置筛选后再看排期' : '新增单账号任务或确保统一任务后，这里显示下次执行' }}</div>
                </div>
              </td>
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
              <td class="num" style="font-size: 11px" data-testid="task-next-run">{{ row.scheduleLabel || row.nextRunAt || '尚未排期' }}</td>
              <td data-testid="task-health">{{ row.healthLabel || '无账号探活' }}</td>
              <td class="num">
                <span style="color: var(--green)">{{ row.successCount }}</span> /
                <span style="color: var(--red)">{{ row.failCount }}</span>
              </td>
              <td data-testid="task-status">{{ row.statusLabel || row.status }}</td>
              <td>
                <button
                  v-if="row.status === 'DISABLED'"
                  class="btn-txt btn"
                  type="button"
                  data-testid="task-start"
                  @click="startTask(row)"
                >
                  启动
                </button>
                <button
                  v-else
                  class="btn-txt btn"
                  type="button"
                  data-testid="task-stop"
                  @click="stopTask(row)"
                >
                  停止
                </button>
                <button class="btn-txt btn" type="button" data-testid="task-run" @click="runTask(row)">立即执行</button>
                <button class="btn-txt btn" type="button" @click="goLogs(row)">日志</button>
                <button
                  v-if="row.isExternalUnified"
                  class="btn-txt btn"
                  type="button"
                  data-testid="collect-external-members"
                  @click="openExternalMembers(row)"
                >
                  外部成员
                </button>
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

    <ProtoDrawer
      :open="membersOpen"
      :title="membersTitle"
      width="520px"
      @close="membersOpen = false"
    >
      <p class="hint" style="margin-bottom: 10px">
        只列出状态启用且打开「是否采集」的竞品关键词与外部账号。
      </p>
      <div v-if="membersLoading" class="empty"><div class="et">加载中</div></div>
      <div v-else-if="!members.length" class="empty" data-testid="collect-members-empty">
        <div class="et">{{ membersHint || '暂无开启采集的外部账号或关键词' }}</div>
        <div class="es">到竞品关键字配置打开「是否采集」后，再回到这里查看</div>
      </div>
      <table v-else data-testid="collect-members-table">
        <thead>
          <tr>
            <th>成员</th>
            <th>平台</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in members" :key="item.memberKind + '-' + item.refId">
            <td>{{ item.memberName }}</td>
            <td><span class="chip">{{ item.platformType }}</span></td>
          </tr>
        </tbody>
      </table>
      <div class="drawer-actions">
        <button class="btn btn-sec btn-sm" type="button" @click="membersOpen = false">关闭</button>
        <button class="btn btn-sec btn-sm" type="button" @click="goKeywords">竞品关键字配置</button>
      </div>
    </ProtoDrawer>

    <ProtoDrawer :open="drawerOpen" :title="editingId ? '编辑任务' : '新增单账号任务'" width="480px" @close="drawerOpen = false">
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
        <p v-if="editingId" class="hint" data-testid="task-monitor">
          最近 {{ monitor.lastRunAt || '—' }} · 下次 {{ monitor.nextRunAt || monitor.scheduleLabel || '尚未排期' }} · 成功
          {{ monitor.successCount }} / 失败 {{ monitor.failCount }} · 健康 {{ monitor.healthLabel || '无账号探活' }}
        </p>
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
import { computed, reactive, ref } from 'vue'
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
const membersOpen = ref(false)
const membersTitle = ref('外部成员')
const members = ref<Array<{ memberKind: string; memberName: string; platformType: string; refId: string }>>([])
const membersHint = ref('')
const membersLoading = ref(false)

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
const monitor = reactive({
  lastRunAt: '',
  nextRunAt: '',
  scheduleLabel: '',
  successCount: 0,
  failCount: 0,
  healthLabel: '',
})
const filtersActive = computed(
  () =>
    Boolean(filters.taskName || filters.platformType || filters.method || filters.frequency || filters.status),
)

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
  form.status = row.status === 'DISABLED' ? 'DISABLED' : 'ENABLED'
  monitor.lastRunAt = row.lastRunAt || ''
  monitor.nextRunAt = row.nextRunAt || ''
  monitor.scheduleLabel = row.scheduleLabel || ''
  monitor.successCount = row.successCount || 0
  monitor.failCount = row.failCount || 0
  monitor.healthLabel = row.healthLabel || ''
  drawerOpen.value = true
}

async function startTask(row: any) {
  try {
    await http.post(`/collect/task/${row.id}/start`)
    await loadList()
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
}

async function stopTask(row: any) {
  try {
    await http.post(`/collect/task/${row.id}/stop`)
    await loadList()
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
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
function goWechatChannels() {
  router.push('/ims/collect/wechat-channels')
}
function goKeywords() {
  membersOpen.value = false
  router.push('/ims/collect/external/keyword')
}

async function openExternalMembers(row: { id: string; taskName: string }) {
  membersTitle.value = `外部统一任务成员 · ${row.taskName}`
  membersOpen.value = true
  membersLoading.value = true
  membersHint.value = ''
  members.value = []
  try {
    const res = await http.get(`/collect/task/${row.id}/members`)
    if (res.data?.code !== 0) {
      membersHint.value = res.data?.msg || '加载失败'
      return
    }
    members.value = res.data?.data?.list || []
  } catch (e: unknown) {
    membersHint.value = errorMessage(e)
  } finally {
    membersLoading.value = false
  }
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
