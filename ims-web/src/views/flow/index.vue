<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>流程管理</h1>
        <div class="sub">FLOW-002/004 · 发起 · 超时督办/BR-115 · 14 FLOW</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openStart">发起流程</button>
        <button class="btn btn-sec btn-sm" type="button" disabled>模板设计</button>
      </div>
    </div>
    <div class="cattabs">
      <button type="button" class="cattab" :class="{ on: tab === 'instance' }" @click="tab = 'instance'">流程实例</button>
      <button type="button" class="cattab" :class="{ on: tab === 'todo' }" @click="tab = 'todo'">我的待办</button>
      <button type="button" class="cattab" :class="{ on: tab === 'timeout' }" @click="tab = 'timeout'">超时督办</button>
      <button type="button" class="cattab" :class="{ on: tab === 'template' }" @click="tab = 'template'">流程模板</button>
    </div>

    <form v-if="tab === 'instance'" class="qbar" @submit.prevent="loadInstances">
      <input v-model="instFilters.keyword" placeholder="标题/单号" style="width: 140px" />
      <select v-model="instFilters.instanceStatus" style="width: 110px">
        <option value="">全部状态</option>
        <option value="RUNNING">进行中</option>
        <option value="APPROVED">已通过</option>
        <option value="REJECTED">已驳回</option>
        <option value="CANCELLED">已撤销</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetInst">重置</button>
    </form>

    <form v-else-if="tab === 'template'" class="qbar" @submit.prevent="loadTemplates">
      <input v-model="tplFilters.templateName" placeholder="模板名称/编码" style="width: 150px" />
      <select v-model="tplFilters.businessDomain" style="width: 110px">
        <option value="">全部域</option>
        <option value="ADMIN">行政域</option>
        <option value="FINANCE">财务域</option>
        <option value="BUSINESS">业务域</option>
        <option value="COMMON">通用</option>
      </select>
      <select v-model="tplFilters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="PUBLISHED">已发布</option>
        <option value="DRAFT">草稿</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetTpl">重置</button>
    </form>

    <form v-else-if="tab === 'todo'" class="qbar" data-testid="flow-todo-qbar" @submit.prevent="loadTodos">
      <select v-model="todoFilters.businessDomain" data-testid="flow-todo-domain" style="width: 110px">
        <option value="">全部域</option>
        <option value="ADMIN">行政域</option>
        <option value="FINANCE">财务域</option>
        <option value="BUSINESS">业务域</option>
        <option value="COMMON">通用</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetTodo">重置</button>
    </form>

    <form v-else-if="tab === 'timeout'" class="qbar" data-testid="flow-timeout-qbar" @submit.prevent="loadTimeouts">
      <select v-model="timeoutFilters.businessDomain" data-testid="flow-timeout-domain" style="width: 110px">
        <option value="">全部域</option>
        <option value="ADMIN">行政域</option>
        <option value="FINANCE">财务域</option>
        <option value="BUSINESS">业务域</option>
        <option value="COMMON">通用</option>
      </select>
      <input
        v-model="timeoutFilters.assigneeName"
        data-testid="flow-timeout-assignee"
        placeholder="处理人"
        style="width: 120px"
      />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetTimeout">重置</button>
    </form>

    <div v-if="tab === 'timeout'" style="margin-bottom: 8px">
      <div class="hint" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center">
        <label class="csub" for="flow-stat-month">统计月</label>
        <input
          id="flow-stat-month"
          v-model="statMonthInput"
          data-testid="flow-stat-month"
          placeholder="YYYY-MM"
          style="width: 110px"
          @change="applyStatMonth"
        />
        <button class="btn btn-sec btn-sm" type="button" data-testid="flow-stat-month-apply" @click="applyStatMonth">
          查询统计
        </button>
        <span v-if="statMonthMsg" class="hint bad" data-testid="flow-stat-month-msg">{{ statMonthMsg }}</span>
        <template v-else-if="timeoutStats && !statMonthEmpty">
          <span>
            月度超时率
            <strong :style="{ color: timeoutStats.monthlyTimeoutRate <= timeoutStats.targetRate ? '#1e8e3e' : '#c93400' }">
              {{ (timeoutStats.monthlyTimeoutRate * 100).toFixed(1) }}%
            </strong>
            （BR-115 目标 &lt;{{ (timeoutStats.targetRate * 100).toFixed(0) }}%）
          </span>
          <span>超时节点 <strong>{{ timeoutStats.timeoutCount }}</strong> / {{ timeoutStats.totalExecuted }}</span>
          <span>督办累计 <strong>{{ timeoutStats.urgeCount }}</strong></span>
          <span class="csub">{{ timeoutStats.statMonth }}</span>
          <span v-if="timeoutDist?.durationBuckets?.length" class="csub">
            时长分布：
            <template v-for="(b, i) in timeoutDist.durationBuckets" :key="b.bucketKey">
              {{ b.bucketLabel }} <strong>{{ b.count }}</strong
              ><span v-if="i < timeoutDist.durationBuckets.length - 1"> · </span>
            </template>
          </span>
        </template>
      </div>
      <div v-if="!statMonthMsg && statMonthEmpty" class="empty" data-testid="flow-stat-month-empty">
        <div class="et">该统计月暂无执行记录</div>
        <div class="es">超时率按当月已执行节点计算；换一个月或回到本月</div>
      </div>
    </div>
    <p v-if="tab === 'timeout' && urgeDone" class="hint" data-testid="flow-urge-done">{{ urgeDone }}</p>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table v-if="tab === 'timeout'">
          <thead>
            <tr>
              <th>实例单号</th>
              <th>模板</th>
              <th>节点</th>
              <th>处理人</th>
              <th>超时时长(分)</th>
              <th>提醒次数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!timeoutRows.length">
              <td colspan="7">
                <div class="empty" data-testid="flow-timeout-empty">
                  <div class="et">{{ error || timeoutEmptyTitle }}</div>
                  <div v-if="!error" class="es">{{ timeoutEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in timeoutRows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.instanceNo }}</td>
              <td>{{ row.templateName }}</td>
              <td>{{ row.nodeName }}</td>
              <td>{{ row.assigneeName || '—' }}</td>
              <td class="num">{{ row.timeoutDurationMinutes }}</td>
              <td class="num">{{ row.remindCount }}</td>
              <td>
                <span class="btn-txt btn" @click="openUrge(row)">督办</span>
              </td>
            </tr>
          </tbody>
        </table>
        <table v-else-if="tab === 'todo'">
          <thead>
            <tr>
              <th>实例单号</th>
              <th>模板</th>
              <th>节点</th>
              <th>发起人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!todoRows.length">
              <td colspan="5">
                <div class="empty" data-testid="flow-todo-empty">
                  <div class="et">{{ error || todoEmptyTitle }}</div>
                  <div v-if="!error" class="es">{{ todoEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in todoRows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.instanceNo }}</td>
              <td>
                {{ row.templateName }}
                <span v-if="row.formData?.accountNo">{{ row.formData.accountNo }}</span>
              </td>
              <td>{{ row.nodeName }}</td>
              <td>{{ row.initiatorName || '—' }}</td>
              <td>
                <button
                  v-if="row.formData?.transferId"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="flow-acct-transfer-go"
                  @click="router.push(transferFlowPath(row))"
                >
                  去处理
                </button>
                <template v-else>
                  <span class="btn-txt btn" @click="handleTask(row, 'APPROVE')">通过</span>
                  <span class="btn-txt btn" style="color: var(--red)" @click="handleTask(row, 'REJECT')">驳回</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
        <table v-else-if="tab === 'instance'">
          <thead>
            <tr>
              <th>实例单号</th>
              <th>标题</th>
              <th>模板</th>
              <th>状态</th>
              <th>当前节点</th>
              <th>发起人</th>
              <th>发起时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!instRows.length">
              <td colspan="7">
                <div class="empty" data-testid="flow-instance-empty">
                  <div class="et">{{ error || instEmptyTitle }}</div>
                  <div v-if="!error" class="es">{{ instEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in instRows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.instanceNo }}</td>
              <td style="font-weight: 500">{{ row.title }}</td>
              <td>{{ row.templateName }}</td>
              <td><span class="tag tag-info">{{ row.instanceStatusLabel }}</span></td>
              <td>{{ row.currentNodeName || '—' }}</td>
              <td>{{ row.initiatorName || '—' }}</td>
              <td class="csub">{{ row.startedAt }}</td>
            </tr>
          </tbody>
        </table>
        <table v-else>
          <thead>
            <tr>
              <th>模板编码</th>
              <th>模板名称</th>
              <th>业务域</th>
              <th>版本</th>
              <th>节点数</th>
              <th>状态</th>
              <th>更新</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!tplRows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无模板' }}</div></div></td>
            </tr>
            <tr v-for="row in tplRows" v-else :key="row.id">
              <td class="mono">{{ row.templateCode }}</td>
              <td style="font-weight: 500">{{ row.templateName }}</td>
              <td>{{ row.businessDomainLabel }}</td>
              <td>{{ row.versionLabel }}</td>
              <td class="num">{{ row.nodeCount }}</td>
              <td><span class="tag tag-info">{{ row.statusLabel }}</span></td>
              <td class="csub">{{ row.updatedAt }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > 0" class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="startOpen" title="发起流程" width="640px" @close="startOpen = false">
      <div v-if="startTemplatesLoading" class="empty"><div class="et">加载模板…</div></div>
      <div v-else-if="!publishedTemplates.length" class="empty" data-testid="flow-start-empty">
        <div class="et">暂无已发布模板</div>
        <div class="es">发布模板后才能发起流程</div>
      </div>
      <template v-else>
        <div class="fld">
          <label>已发布模板</label>
          <select v-model="startForm.templateId" data-testid="flow-start-template">
            <option v-for="t in publishedTemplates" :key="t.id" :value="t.id">
              {{ t.templateName }}（{{ t.templateCode }}）
            </option>
          </select>
        </div>
        <div class="fld">
          <label>标题</label>
          <input v-model="startForm.title" data-testid="flow-start-title" placeholder="formData.title" />
        </div>
        <div class="fld">
          <label>businessKey（可选 · 幂等）</label>
          <input v-model="startForm.businessKey" data-testid="flow-start-key" />
        </div>
      </template>
      <p v-if="startMsg" class="hint" :class="{ bad: startErr }" data-testid="flow-start-msg">{{ startMsg }}</p>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="startOpen = false">取消</button>
        <button
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="flow-start-submit"
          :disabled="startLoading || startTemplatesLoading || !publishedTemplates.length"
          @click="submitStart"
        >
          {{ startLoading ? '提交中…' : '提交发起' }}
        </button>
      </template>
    </ProtoDrawer>

    <div v-if="urgeOpen" class="flow-modal-mask" @click.self="closeUrge">
      <div class="flow-modal-card" data-testid="flow-urge-modal" role="dialog" aria-labelledby="flow-urge-title">
        <h3 id="flow-urge-title">手动督办</h3>
        <p class="hint">{{ urgeTarget?.instanceNo }} · {{ urgeTarget?.nodeName }}</p>
        <div class="fld">
          <label>督办说明</label>
          <textarea v-model="urgeMessage" data-testid="flow-urge-message" rows="4" />
        </div>
        <p class="hint" :class="{ bad: urgeMessage.length > 256 }">{{ urgeMessage.length }}/256</p>
        <p v-if="urgeMsg" class="hint" :class="{ bad: urgeErr }" data-testid="flow-urge-msg">{{ urgeMsg }}</p>
        <div class="flow-modal-acts">
          <button class="btn btn-sec btn-sm" type="button" data-testid="flow-urge-cancel" @click="closeUrge">取消</button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            data-testid="flow-urge-confirm"
            :disabled="urgeSaving"
            @click="confirmUrge"
          >
            {{ urgeSaving ? '提交中…' : '确认督办' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

const URGE_DEFAULT = '请尽快处理该审批待办'

const router = useRouter()

function platformSlug(platform: string) {
  const map: Record<string, string> = {
    DOUYIN: 'douyin',
    KUAISHOU: 'kuaishou',
    XIAOHONGSHU: 'xiaohongshu',
    WECHAT_OFFICIAL: 'wechat-official',
    WECHAT_CHANNELS: 'wechat-channels',
  }
  return map[platform.trim().toUpperCase()] || 'douyin'
}

function transferFlowPath(row: { formData?: { transferId?: number; platform?: string } }) {
  const id = row.formData?.transferId
  if (!id) return ''
  return `/ims/corp/account/${platformSlug(String(row.formData?.platform || 'DOUYIN'))}?transferId=${id}`
}

const tab = ref<'instance' | 'template' | 'todo' | 'timeout'>('instance')
const loading = ref(false)
const error = ref('')
const total = ref(0)
const instRows = ref<Record<string, unknown>[]>([])
const todoRows = ref<
  {
    id: number
    instanceNo: string
    templateName: string
    nodeName: string
    initiatorName: string
    formData?: { transferId?: number; platform?: string; accountNo?: string }
  }[]
>([])
const timeoutRows = ref<
  {
    id: number
    instanceNo: string
    templateName: string
    nodeName: string
    assigneeName: string
    timeoutDurationMinutes: number
    remindCount: number
  }[]
>([])
const timeoutStats = ref<{
  monthlyTimeoutRate: number
  targetRate: number
  timeoutCount: number
  totalExecuted: number
  urgeCount: number
  statMonth: string
} | null>(null)
const timeoutDist = ref<{
  durationBuckets: { bucketKey: string; bucketLabel: string; count: number }[]
} | null>(null)
const tplRows = ref<Record<string, unknown>[]>([])
const STAT_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/

function beijingStatMonth(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
  }).formatToParts(date)
  const year = parts.find((part) => part.type === 'year')?.value ?? '1970'
  const month = parts.find((part) => part.type === 'month')?.value ?? '01'
  return `${year}-${month}`
}

const instFilters = ref({ keyword: '', instanceStatus: '' })
const todoFilters = ref({ businessDomain: '' })
const timeoutFilters = ref({ businessDomain: '', assigneeName: '' })
const statMonthInput = ref(beijingStatMonth())
const appliedStatMonth = ref(beijingStatMonth())
const statMonthMsg = ref('')
const tplFilters = ref({ templateName: '', businessDomain: '', status: '' })
const startOpen = ref(false)
const startLoading = ref(false)
const startTemplatesLoading = ref(false)
const startMsg = ref('')
const startErr = ref(false)
const publishedTemplates = ref<{ id: number; templateCode: string; templateName: string }[]>([])
const startForm = ref({ templateId: 0, title: '', businessKey: '' })
const urgeOpen = ref(false)
const urgeSaving = ref(false)
const urgeMessage = ref(URGE_DEFAULT)
const urgeMsg = ref('')
const urgeErr = ref(false)
const urgeDone = ref('')
const urgeTarget = ref<{ id: number; instanceNo: string; nodeName: string; remindCount: number } | null>(null)

const todoFiltered = computed(() => !!todoFilters.value.businessDomain)
const todoEmptyTitle = computed(() => (todoFiltered.value ? '该业务域暂无待办' : '暂无待办'))
const todoEmptyHint = computed(() =>
  todoFiltered.value ? '换一个业务域，或点重置查看全部待办' : '发起流程后，处理人会在这里看到待办',
)
const instFiltered = computed(() => !!(instFilters.value.keyword.trim() || instFilters.value.instanceStatus))
const instEmptyTitle = computed(() => (instFiltered.value ? '没有符合条件的流程实例' : '暂无实例'))
const instEmptyHint = computed(() =>
  instFiltered.value ? '调整标题、单号或状态后再查询' : '点右上角「发起流程」创建第一条实例',
)
const timeoutAssignee = computed(() => timeoutFilters.value.assigneeName.trim())
const timeoutEmptyTitle = computed(() => {
  const domain = timeoutFilters.value.businessDomain
  const name = timeoutAssignee.value
  if (domain && name) return '没有符合条件的超时待办'
  if (domain) return '该业务域暂无超时待办'
  if (name) return '该处理人暂无超时待办'
  return '暂无超时待办'
})
const timeoutEmptyHint = computed(() => {
  const domain = timeoutFilters.value.businessDomain
  const name = timeoutAssignee.value
  if (domain && name) return '调整业务域或处理人后再查询'
  if (domain) return '换一个业务域，或清空筛选后再查'
  if (name) return '核对处理人姓名后再查询'
  return '未超过 SLA 的待办不会出现在督办清单'
})
const statMonthEmpty = computed(
  () => !statMonthMsg.value && !!timeoutStats.value && timeoutStats.value.totalExecuted === 0,
)

async function loadInstances() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (instFilters.value.keyword) params.keyword = instFilters.value.keyword
    if (instFilters.value.instanceStatus) params.instanceStatus = instFilters.value.instanceStatus
    const res = await http.get('/flow/instance/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      instRows.value = []
      total.value = 0
      return
    }
    instRows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

async function loadTimeoutRate() {
  try {
    const params: Record<string, string> = {}
    if (appliedStatMonth.value) params.statMonth = appliedStatMonth.value
    const res = await http.get('/flow/timeout/rate', { params })
    if (res.data.code === 0) {
      const d = res.data.data
      timeoutStats.value = {
        monthlyTimeoutRate: d.monthlyTimeoutRate ?? 0,
        targetRate: d.targetRate ?? 0.1,
        timeoutCount: d.timeoutCount ?? 0,
        totalExecuted: d.totalExecuted ?? 0,
        urgeCount: d.urgeCount ?? 0,
        statMonth: d.statMonth ?? '',
      }
    }
  } catch {
    timeoutStats.value = null
  }
}

async function applyStatMonth() {
  const raw = statMonthInput.value.trim()
  if (raw && !STAT_MONTH_RE.test(raw)) {
    statMonthMsg.value = '统计月请填写 YYYY-MM'
    return
  }
  statMonthMsg.value = ''
  appliedStatMonth.value = raw || beijingStatMonth()
  statMonthInput.value = appliedStatMonth.value
  await Promise.all([loadTimeoutRate(), loadTimeoutDistribution()])
}

async function loadTimeoutDistribution() {
  try {
    const params: Record<string, string> = {}
    if (appliedStatMonth.value) params.statMonth = appliedStatMonth.value
    const res = await http.get('/flow/timeout/distribution', { params })
    if (res.data.code === 0) {
      timeoutDist.value = {
        durationBuckets: res.data.data.durationBuckets ?? [],
      }
    }
  } catch {
    timeoutDist.value = null
  }
}

async function loadTimeouts() {
  loading.value = true
  error.value = ''
  try {
    await loadTimeoutRate()
    await loadTimeoutDistribution()
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (timeoutFilters.value.businessDomain) params.businessDomain = timeoutFilters.value.businessDomain
    if (timeoutAssignee.value) params.assigneeName = timeoutAssignee.value
    const res = await http.get('/flow/timeout/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      timeoutRows.value = []
      total.value = 0
      return
    }
    timeoutRows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function openUrge(row: { id: number; instanceNo: string; nodeName: string; remindCount: number }) {
  urgeTarget.value = row
  urgeMessage.value = URGE_DEFAULT
  urgeMsg.value = ''
  urgeErr.value = false
  urgeOpen.value = true
}

function closeUrge() {
  if (urgeSaving.value) return
  urgeOpen.value = false
}

async function confirmUrge() {
  const row = urgeTarget.value
  if (!row) return
  const text = urgeMessage.value.trim()
  if (!text) {
    urgeMsg.value = '请填写督办说明'
    urgeErr.value = true
    return
  }
  if (urgeMessage.value.length > 256 || text.length > 256) {
    urgeMsg.value = '督办说明不能超过 256 字'
    urgeErr.value = true
    return
  }
  urgeSaving.value = true
  urgeMsg.value = ''
  urgeErr.value = false
  try {
    const res = await http.put(`/flow/timeout/${row.id}/urge`, { urgeMessage: text })
    if (res.data.code !== 0) {
      urgeMsg.value = res.data.msg || '督办失败'
      urgeErr.value = true
      return
    }
    urgeDone.value = `已督办 ${row.instanceNo}，提醒次数 ${row.remindCount + 1}`
    urgeOpen.value = false
    await loadTimeouts()
  } catch (e: unknown) {
    urgeMsg.value = e instanceof Error ? e.message : '网络错误'
    urgeErr.value = true
  } finally {
    urgeSaving.value = false
  }
}

async function loadTodos() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (todoFilters.value.businessDomain) params.businessDomain = todoFilters.value.businessDomain
    const res = await http.get('/flow/task/my-todo', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      todoRows.value = []
      total.value = 0
      return
    }
    todoRows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

async function handleTask(row: { id: number }, action: 'APPROVE' | 'REJECT') {
  const label = action === 'APPROVE' ? '通过' : '驳回'
  if (!confirm(`确认${label}该待办？`)) return
  try {
    const res = await http.put(`/flow/task/${row.id}/handle`, { action, comment: `前端${label}` })
    if (res.data.code !== 0) {
      alert(res.data.msg || `${label}失败`)
      return
    }
    await loadTodos()
    if (tab.value === 'instance') await loadInstances()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : '网络错误')
  }
}

async function loadTemplates() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (tplFilters.value.templateName) params.templateName = tplFilters.value.templateName
    if (tplFilters.value.businessDomain) params.businessDomain = tplFilters.value.businessDomain
    if (tplFilters.value.status) params.status = tplFilters.value.status
    const res = await http.get('/flow/template/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      tplRows.value = []
      total.value = 0
      return
    }
    tplRows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function resetInst() {
  instFilters.value = { keyword: '', instanceStatus: '' }
  loadInstances()
}

function resetTpl() {
  tplFilters.value = { templateName: '', businessDomain: '', status: '' }
  loadTemplates()
}

function resetTodo() {
  todoFilters.value = { businessDomain: '' }
  loadTodos()
}

function resetTimeout() {
  timeoutFilters.value = { businessDomain: '', assigneeName: '' }
  loadTimeouts()
}

async function openStart() {
  startMsg.value = ''
  startErr.value = false
  startTemplatesLoading.value = true
  startOpen.value = true
  try {
    const res = await http.get('/flow/template/list', {
      params: { pageNo: 1, pageSize: 50, status: 'PUBLISHED' },
    })
    if (res.data.code !== 0) {
      startMsg.value = res.data.msg || '模板加载失败'
      startErr.value = true
      publishedTemplates.value = []
      return
    }
    publishedTemplates.value = (res.data.data.list || []) as typeof publishedTemplates.value
    const ids = new Set(publishedTemplates.value.map((t) => t.id))
    if (!ids.has(startForm.value.templateId)) {
      startForm.value.templateId = publishedTemplates.value[0]?.id ?? 0
    }
  } catch (e: unknown) {
    startMsg.value = e instanceof Error ? e.message : '网络错误'
    startErr.value = true
    publishedTemplates.value = []
  } finally {
    startTemplatesLoading.value = false
  }
}

async function submitStart() {
  if (!startForm.value.templateId || !startForm.value.title.trim()) {
    startMsg.value = '请选择模板并填写标题'
    startErr.value = true
    return
  }
  startLoading.value = true
  startMsg.value = ''
  startErr.value = false
  try {
    const payload: Record<string, unknown> = {
      templateId: startForm.value.templateId,
      formData: { title: startForm.value.title.trim() },
    }
    if (startForm.value.businessKey.trim()) payload.businessKey = startForm.value.businessKey.trim()
    const res = await http.post('/flow/instance', payload)
    if (res.data.code !== 0) {
      startMsg.value = res.data.msg || '发起失败'
      startErr.value = true
      return
    }
    startMsg.value = `已发起：${res.data.data.instanceNo}`
    startOpen.value = false
    tab.value = 'instance'
    await loadInstances()
  } catch (e: unknown) {
    startMsg.value = e instanceof Error ? e.message : '网络错误'
    startErr.value = true
  } finally {
    startLoading.value = false
  }
}

watch(tab, (t) => {
  if (t === 'instance') loadInstances()
  else if (t === 'todo') loadTodos()
  else if (t === 'timeout') loadTimeouts()
  else loadTemplates()
})

onMounted(loadInstances)
</script>

<style scoped>
.flow-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 220;
}
.flow-modal-card {
  width: min(480px, 92vw);
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
.flow-modal-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.flow-modal-acts {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
