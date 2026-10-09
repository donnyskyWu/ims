<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>采集日志</h1>
        <div class="sub">UX-M10 P-M10-003 · typeResults 详情 · 16 COLLECT</div>
      </div>
      <div class="acts">
        <span v-if="successRate24h != null" class="chip">近 24h 成功率 {{ successRate24h }}%</span>
        <span v-if="failureAccountCount > 0" class="chip" style="border-color: var(--red); color: var(--red)">
          连续失败账号 {{ failureAccountCount }}
        </span>
        <button class="btn btn-sec btn-sm" type="button" @click="openManualFill">手工补录</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model.number="filters.taskId" type="number" placeholder="任务 id" style="width: 100px" />
      <input v-model.number="filters.accountId" type="number" placeholder="账号 id" style="width: 100px" />
      <select v-model="filters.status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="SUCCESS">成功</option>
        <option value="FAILED">失败</option>
        <option value="PARTIAL">部分成功</option>
        <option value="COOKIE_EXPIRED">Cookie 已失效</option>
        <option value="ENGINE_UNAVAILABLE">浏览器引擎不可用</option>
      </select>
      <input v-model="filters.dateFrom" placeholder="开始日期 YYYY-MM-DD" style="width: 150px" />
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
              <th>状态</th>
              <th>开始时间</th>
              <th>耗时</th>
              <th>记录数</th>
              <th>重试</th>
              <th>错误</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无日志' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.taskName }}</td>
              <td>{{ row.statusLabel || row.status }}</td>
              <td class="num" style="font-size: 12px">{{ row.startedAt }}</td>
              <td class="num">{{ (row.durationMs / 1000).toFixed(1) }}s</td>
              <td class="num">{{ row.recordCount }}</td>
              <td class="num" data-testid="log-retry-count">{{ row.retryCount }}</td>
              <td>
                <span v-if="row.errorSummary" class="btn-txt btn btn-danger-txt">{{ row.errorSummary }}</span>
                <span v-else style="color: var(--green)">—</span>
              </td>
              <td>
                <button class="btn-txt btn" type="button" @click="openDetail(row)">详情</button>
                <button
                  v-if="row.retryable"
                  class="btn-txt btn"
                  type="button"
                  data-testid="log-retry"
                  @click="retryLog(row)"
                >
                  重试
                </button>
                <button v-if="row.repairAccountId" class="btn-txt btn" type="button" @click="repairBind(row)">
                  修复绑定
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="manualOpen" title="手工补录" width="420px" @close="manualOpen = false">
      <form class="qbar" style="flex-direction: column; align-items: stretch; gap: 10px" @submit.prevent="submitManualFill">
        <label>任务 id<input v-model.number="manual.taskId" type="number" required style="width: 100%" /></label>
        <label>账号 id（可选）<input v-model.number="manual.accountId" type="number" style="width: 100%" /></label>
        <label>补录条数<input v-model.number="manual.recordCount" type="number" min="1" style="width: 100%" /></label>
        <label>数据类型<input v-model="manual.dataType" placeholder="WORK" style="width: 100%" /></label>
        <label>备注<textarea v-model="manual.remark" rows="2" style="width: 100%" /></label>
        <button class="btn btn-pri btn-sm" type="submit" :disabled="manualSaving">提交补录</button>
        <p v-if="manualMsg" class="hint">{{ manualMsg }}</p>
      </form>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" title="日志详情" width="520px" @close="detailOpen = false">
      <div v-if="detail">
        <p><b>状态</b> {{ detail.statusLabel || detail.status }} · {{ detail.startedAt }}</p>
        <p v-if="detail.errorSummary" class="hint" style="color: var(--red)">{{ detail.errorSummary }}</p>
        <p class="hint">重试次数 {{ detail.retryCount ?? 0 }}</p>
        <button
          v-if="detail.retryable"
          class="btn btn-sec btn-sm"
          type="button"
          data-testid="log-retry-detail"
          @click="retryLog(detail)"
        >
          重试本次失败
        </button>
        <div class="csub" style="margin: 12px 0 8px">typeResults</div>
        <details v-for="(tr, idx) in detail.typeResults" :key="idx" style="margin-bottom: 8px">
          <summary>{{ tr.dataType }} · {{ tr.status }} · {{ tr.recordCount ?? 0 }} 条</summary>
          <pre class="mono" style="font-size: 11px; white-space: pre-wrap">{{ JSON.stringify(tr, null, 2) }}</pre>
        </details>
        <button v-if="detail.repairAccountId" class="btn btn-pri btn-sm" type="button" @click="repairBind(detail)">
          前往账号采集 Tab
        </button>
      </div>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const route = useRoute()
const router = useRouter()
const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const successRate24h = ref<number | null>(null)
const failureAccountCount = ref(0)
const detailOpen = ref(false)
const detail = ref<any | null>(null)
const manualOpen = ref(false)
const manualSaving = ref(false)
const manualMsg = ref('')
const manual = reactive({
  taskId: undefined as number | undefined,
  accountId: undefined as number | undefined,
  recordCount: 1,
  dataType: 'WORK',
  remark: '',
})

const filters = reactive({
  taskId: undefined as number | undefined,
  accountId: undefined as number | undefined,
  status: '',
  dateFrom: '',
})

const PLATFORM_SLUG: Record<string, string> = {
  DOUYIN: 'douyin',
  KUAISHOU: 'kuaishou',
  WECHAT_CHANNELS: 'wechat-channels',
  WECHAT_OFFICIAL: 'wechat-official',
  XIAOHONGSHU: 'xiaohongshu',
}

async function loadQuality() {
  try {
    const res = await http.get('/collect/quality/summary')
    const body = res.data
    if (body?.code === 0) {
      if (body.data.successRate24h != null) successRate24h.value = body.data.successRate24h
      failureAccountCount.value = body.data.consecutiveFailureAccountCount ?? 0
    }
  } catch {
    /* optional */
  }
}

function openManualFill() {
  manualMsg.value = ''
  if (filters.taskId) manual.taskId = filters.taskId
  manualOpen.value = true
}

async function submitManualFill() {
  if (!manual.taskId) {
    manualMsg.value = '请填写任务 id'
    return
  }
  manualSaving.value = true
  manualMsg.value = ''
  try {
    const payload: Record<string, unknown> = {
      taskId: manual.taskId,
      recordCount: manual.recordCount || 1,
      dataType: manual.dataType || 'WORK',
      remark: manual.remark,
    }
    if (manual.accountId) payload.accountId = manual.accountId
    const res = await http.post('/collect/manual-fill', payload)
    if (res.data?.code !== 0) {
      manualMsg.value = res.data?.msg || '补录失败'
      return
    }
    manualMsg.value = '补录成功'
    manualOpen.value = false
    await loadList()
    await loadQuality()
  } catch (e: unknown) {
    manualMsg.value = errorMessage(e)
  } finally {
    manualSaving.value = false
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.taskId) params.taskId = filters.taskId
    if (filters.accountId) params.accountId = filters.accountId
    if (filters.status) params.status = filters.status
    if (filters.dateFrom) params.dateFrom = filters.dateFrom
    const res = await http.get('/collect/log/page', { params })
    rows.value = res.data?.data?.list || []
    total.value = res.data?.data?.total || 0
    successRate24h.value = res.data?.data?.successRate24h ?? null
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.taskId = undefined
  filters.accountId = undefined
  filters.status = ''
  filters.dateFrom = ''
  loadList()
}

async function retryLog(row: any) {
  if (!row?.taskId) return
  error.value = ''
  try {
    const res = await http.post(`/collect/task/${row.taskId}/run`)
    if (res.data?.code !== 0) {
      error.value = res.data?.msg || '重试失败'
      return
    }
    detailOpen.value = false
    await loadList()
    await loadQuality()
  } catch (e: unknown) {
    error.value = errorMessage(e)
  }
}

async function openDetail(row: any) {
  const res = await http.get(`/collect/log/${row.id}`)
  detail.value = res.data?.data
  detailOpen.value = true
}

async function repairBind(row: any) {
  const accountId = row.repairAccountId
  if (!accountId) return
  let slug = 'douyin'
  try {
    const acct = await http.get(`/corp/account/${accountId}`)
    const pt = acct.data?.data?.platformType as string
    slug = PLATFORM_SLUG[pt] || 'douyin'
  } catch {
    /* keep default */
  }
  router.push({
    path: `/ims/corp/account/${slug}`,
    query: { openId: String(accountId), tab: 'collect' },
  })
}

onMounted(() => {
  const q = route.query
  if (q.taskId) filters.taskId = Number(q.taskId)
  loadQuality()
  loadList().then(() => {
    if (q.logId) {
      const row = rows.value.find((r) => String(r.id) === String(q.logId))
      if (row) openDetail(row)
    }
  })
})

watch(
  () => route.query.taskId,
  (v) => {
    if (v) filters.taskId = Number(v)
  },
)
</script>
