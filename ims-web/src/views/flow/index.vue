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
      <select v-model="instFilters.instanceStatus" data-testid="flow-instance-status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="RUNNING">进行中</option>
        <option value="APPROVED">已通过</option>
        <option value="REJECTED">已驳回</option>
        <option value="CANCELLED">已撤销</option>
        <option value="TIMEOUT">已超时</option>
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

    <div
      v-if="tab === 'timeout' && timeoutStats"
      class="hint"
      style="margin-bottom: 8px; display: flex; gap: 16px; flex-wrap: wrap; align-items: center"
    >
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
    </div>

    <p v-if="tab === 'todo' && rejectDone" class="hint" data-testid="flow-reject-done">{{ rejectDone }}</p>

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
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无超时待办' }}</div></div></td>
            </tr>
            <tr v-for="row in timeoutRows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.instanceNo }}</td>
              <td>{{ row.templateName }}</td>
              <td>{{ row.nodeName }}</td>
              <td>{{ row.assigneeName || '—' }}</td>
              <td class="num">{{ row.timeoutDurationMinutes }}</td>
              <td class="num">{{ row.remindCount }}</td>
              <td>
                <span class="btn-txt btn" @click="urgeTask(row)">督办</span>
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
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无待办' }}</div></div></td>
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
                  <span class="btn-txt btn" style="color: var(--red)" data-testid="flow-reject" @click="openReject(row)">驳回</span>
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
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!instRows.length">
              <td colspan="8">
                <div class="empty" data-testid="flow-instance-empty">
                  <div class="et">{{ error || instEmptyTitle }}</div>
                  <div v-if="!error" class="es">{{ instEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in instRows" v-else :key="String(row.id)">
              <td class="mono" style="color: var(--blue)">{{ row.instanceNo }}</td>
              <td style="font-weight: 500">{{ row.title }}</td>
              <td>{{ row.templateName }}</td>
              <td><span class="tag tag-info">{{ row.instanceStatusLabel }}</span></td>
              <td>{{ row.currentNodeName || '—' }}</td>
              <td>{{ row.initiatorName || '—' }}</td>
              <td class="csub">{{ row.startedAt }}</td>
              <td>
                <button
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="flow-instance-detail"
                  @click="openDetail(row)"
                >
                  详情
                </button>
              </td>
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

    <div v-if="startOpen" class="modal-mask" @click.self="startOpen = false">
      <div class="modal-card" style="width: min(420px, 92vw)">
        <h3 style="margin: 0 0 12px">发起流程</h3>
        <label class="lbl">已发布模板</label>
        <select v-model="startForm.templateId" style="width: 100%; margin-bottom: 10px">
          <option v-for="t in publishedTemplates" :key="t.id" :value="t.id">
            {{ t.templateName }}（{{ t.templateCode }}）
          </option>
        </select>
        <label class="lbl">标题</label>
        <input v-model="startForm.title" placeholder="formData.title" style="width: 100%; margin-bottom: 10px" />
        <label class="lbl">businessKey（可选 · 幂等）</label>
        <input v-model="startForm.businessKey" style="width: 100%; margin-bottom: 12px" />
        <p v-if="startMsg" class="hint" :class="{ err: startErr }">{{ startMsg }}</p>
        <div class="acts" style="justify-content: flex-end; gap: 8px">
          <button class="btn btn-sec btn-sm" type="button" @click="startOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" :disabled="startLoading" @click="submitStart">
            {{ startLoading ? '提交中…' : '提交发起' }}
          </button>
        </div>
      </div>
    </div>

    <ProtoDrawer
      :open="detailOpen"
      :title="detail ? `实例详情 · ${detail.instanceNo}` : '实例详情'"
      width="640px"
      @close="detailOpen = false"
    >
      <div v-if="detailLoading" class="empty"><div class="et">加载中</div></div>
      <template v-else-if="detail">
        <p class="hint" data-testid="flow-detail-edge">{{ detail.edgeCopy }}</p>
        <p class="csub" style="margin: 8px 0">
          {{ detail.templateName }} · {{ detail.instanceStatusLabel }} · {{ detail.currentNodeName || '—' }}
        </p>
        <div class="fld">
          <label>表单</label>
          <div v-if="detail.formEmpty" class="empty" data-testid="flow-detail-form-empty" style="padding: 16px">
            <div class="et">未填写表单字段</div>
          </div>
          <ul v-else style="margin: 4px 0 0; padding-left: 18px">
            <li v-for="pair in formPairs" :key="pair[0]">{{ pair[0] }}：{{ pair[1] }}</li>
          </ul>
        </div>
        <div class="fld" style="margin-top: 12px">
          <label>流转轨迹</label>
          <div v-if="!detail.traceLog.length" class="empty" data-testid="flow-detail-trace-empty" style="padding: 16px">
            <div class="et">暂无流转记录</div>
          </div>
          <ul v-else style="margin: 4px 0 0; padding-left: 18px">
            <li v-for="(item, i) in detail.traceLog" :key="`${item.nodeOrder}-${i}`">
              {{ item.nodeName }} · {{ actionLabel(item.action) }}
              <span v-if="item.comment"> · {{ item.comment }}</span>
            </li>
          </ul>
        </div>
        <div class="fld" style="margin-top: 12px">
          <label>抄送</label>
          <div v-if="!detail.ccRecords.length" class="empty" data-testid="flow-detail-cc-empty" style="padding: 16px">
            <div class="et">暂无抄送记录</div>
          </div>
        </div>
      </template>
      <p v-else-if="detailError" class="hint err">{{ detailError }}</p>
      <template #foot>
        <button class="btn btn-sec btn-sm" type="button" @click="detailOpen = false">关闭</button>
        <button
          v-if="detail?.canRevoke"
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="flow-revoke"
          @click="openRevoke"
        >
          撤销
        </button>
      </template>
    </ProtoDrawer>

    <div v-if="revokeOpen" class="modal-mask" data-testid="flow-revoke-modal" @click.self="closeRevoke">
      <div class="modal-card" style="width: min(420px, 92vw)">
        <h3 style="margin: 0 0 8px">撤销流程</h3>
        <p data-testid="flow-revoke-copy">撤销后已完成节点留痕，实例进入已撤销。</p>
        <p v-if="revokeMsg" class="hint err" data-testid="flow-revoke-msg">{{ revokeMsg }}</p>
        <div class="acts" style="justify-content: flex-end; gap: 8px; margin-top: 12px">
          <button class="btn btn-sec btn-sm" type="button" data-testid="flow-revoke-cancel" @click="closeRevoke">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="flow-revoke-confirm" :disabled="revokeSaving" @click="submitRevoke">
            {{ revokeSaving ? '提交中…' : '确认撤销' }}
          </button>
        </div>
      </div>
    </div>

    <ProtoDrawer :open="rejectOpen" title="驳回待办" width="480px" @close="closeReject">
      <p class="hint" data-testid="flow-reject-copy">建议填写退回意见，可不填。驳回后实例进入已驳回，已完成节点留痕。</p>
      <p v-if="rejectTarget" class="csub">{{ rejectTarget.instanceNo }} · {{ rejectTarget.nodeName }}</p>
      <div class="fld" style="margin-top: 10px">
        <label>退回意见</label>
        <textarea v-model="rejectComment" data-testid="flow-reject-comment" rows="3" placeholder="可不填" />
      </div>
      <p v-if="rejectMsg" class="hint err" data-testid="flow-reject-msg">{{ rejectMsg }}</p>
      <template #foot>
        <button class="btn btn-sec btn-sm" type="button" data-testid="flow-reject-cancel" @click="closeReject">取消</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="flow-reject-confirm" :disabled="rejectSaving" @click="submitReject">
          {{ rejectSaving ? '提交中…' : '确认驳回' }}
        </button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

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
const instFilters = ref({ keyword: '', instanceStatus: '' })
const tplFilters = ref({ templateName: '', businessDomain: '', status: '' })

const instFiltered = computed(() => !!(instFilters.value.keyword.trim() || instFilters.value.instanceStatus))
const instEmptyTitle = computed(() => {
  if (instFilters.value.instanceStatus === 'TIMEOUT') return '暂无已超时实例'
  if (instFiltered.value) return '没有符合条件的流程实例'
  return '暂无实例'
})
const instEmptyHint = computed(() => {
  if (instFilters.value.instanceStatus === 'TIMEOUT') return '超时终态才会出现在这里；临期待办请到超时督办'
  if (instFiltered.value) return '调整标题、单号或状态后再查询'
  return '点右上角「发起流程」创建第一条实例'
})

type FlowDetail = {
  instanceNo: string
  title: string
  templateName: string
  instanceStatus: string
  instanceStatusLabel: string
  currentNodeName: string
  initiatorName: string
  formData: Record<string, string | number | null>
  formEmpty: boolean
  canRevoke: boolean
  edgeCopy: string
  traceLog: { nodeOrder: number; nodeName: string; action: string; comment?: string }[]
  ccRecords: unknown[]
}

const detailOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detail = ref<FlowDetail | null>(null)
const revokeOpen = ref(false)
const revokeSaving = ref(false)
const revokeMsg = ref('')
const rejectOpen = ref(false)
const rejectSaving = ref(false)
const rejectComment = ref('')
const rejectMsg = ref('')
const rejectDone = ref('')
const rejectTarget = ref<{ id: number; instanceNo: string; nodeName: string } | null>(null)

const formPairs = computed(() => {
  const data = detail.value?.formData || {}
  return Object.entries(data).filter(([, value]) => value !== null && String(value).trim() !== '')
})

function actionLabel(action: string) {
  const map: Record<string, string> = {
    PENDING: '待处理',
    APPROVED: '通过',
    REJECTED: '驳回',
    TRANSFERRED: '转交',
    CANCELLED: '已撤销',
  }
  return map[action] || action
}
const startOpen = ref(false)
const startLoading = ref(false)
const startMsg = ref('')
const startErr = ref(false)
const publishedTemplates = ref<{ id: number; templateCode: string; templateName: string }[]>([])
const startForm = ref({ templateId: 0, title: '', businessKey: '' })

async function loadInstances() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    const keyword = instFilters.value.keyword.trim()
    if (keyword) params.keyword = keyword
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
    const res = await http.get('/flow/timeout/rate')
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

async function loadTimeoutDistribution() {
  try {
    const res = await http.get('/flow/timeout/distribution')
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
    const res = await http.get('/flow/timeout/list', { params: { pageNo: 1, pageSize: 20 } })
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

async function urgeTask(row: { id: number; remindCount: number }) {
  const msg = window.prompt('督办说明（可选，≤256 字）', '请尽快处理该审批待办') || ''
  try {
    const res = await http.put(`/flow/timeout/${row.id}/urge`, { urgeMessage: msg.slice(0, 256) })
    if (res.data.code !== 0) {
      alert(res.data.msg || '督办失败')
      return
    }
    await loadTimeouts()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : '网络错误')
  }
}

async function loadTodos() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/flow/task/my-todo', { params: { pageNo: 1, pageSize: 20 } })
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

async function openDetail(row: Record<string, unknown>) {
  const instanceNo = String(row.instanceNo || '')
  if (!instanceNo) return
  detailOpen.value = true
  detailLoading.value = true
  detailError.value = ''
  detail.value = null
  revokeOpen.value = false
  try {
    const res = await http.get(`/flow/instance/${encodeURIComponent(instanceNo)}`)
    detail.value = res.data.data as FlowDetail
  } catch (e: unknown) {
    const body = e as { msg?: string }
    detailError.value = body.msg || (e instanceof Error ? e.message : '加载失败')
  } finally {
    detailLoading.value = false
  }
}

function openRevoke() {
  revokeMsg.value = ''
  revokeOpen.value = true
}

function closeRevoke() {
  if (revokeSaving.value) return
  revokeOpen.value = false
}

async function submitRevoke() {
  if (!detail.value) return
  revokeSaving.value = true
  revokeMsg.value = ''
  try {
    await http.put(`/flow/instance/${encodeURIComponent(detail.value.instanceNo)}/revoke`, {})
    revokeOpen.value = false
    await openDetail({ instanceNo: detail.value.instanceNo })
    await loadInstances()
  } catch (e: unknown) {
    const body = e as { code?: number; msg?: string }
    if (body.code === 1140) revokeMsg.value = '实例已结束不可撤销'
    else if (body.code === 1139) revokeMsg.value = '仅发起人或管理员可撤销'
    else revokeMsg.value = body.msg || '撤销失败'
  } finally {
    revokeSaving.value = false
  }
}

function openReject(row: { id: number; instanceNo: string; nodeName: string }) {
  rejectTarget.value = row
  rejectComment.value = ''
  rejectMsg.value = ''
  rejectOpen.value = true
}

function closeReject() {
  if (rejectSaving.value) return
  rejectOpen.value = false
}

async function submitReject() {
  const row = rejectTarget.value
  if (!row) return
  rejectSaving.value = true
  rejectMsg.value = ''
  try {
    await http.put(`/flow/task/${row.id}/handle`, {
      action: 'REJECT',
      comment: rejectComment.value.trim(),
    })
    rejectDone.value = `已驳回 ${row.instanceNo}。实例进入已驳回，已完成节点留痕。`
    rejectOpen.value = false
    await loadTodos()
  } catch (e: unknown) {
    const body = e as { code?: number; msg?: string }
    const msg = body.msg || (e instanceof Error ? e.message : '驳回失败')
    rejectMsg.value = body.code === 1001 && msg.includes('终态') ? '实例已结束，无法驳回' : msg
  } finally {
    rejectSaving.value = false
  }
}

function resetTpl() {
  tplFilters.value = { templateName: '', businessDomain: '', status: '' }
  loadTemplates()
}

async function openStart() {
  startMsg.value = ''
  startErr.value = false
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
    if (publishedTemplates.value.length && !startForm.value.templateId) {
      startForm.value.templateId = publishedTemplates.value[0].id
    }
  } catch (e: unknown) {
    startMsg.value = e instanceof Error ? e.message : '网络错误'
    startErr.value = true
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
  rejectDone.value = ''
  if (t === 'instance') loadInstances()
  else if (t === 'todo') loadTodos()
  else if (t === 'timeout') loadTimeouts()
  else loadTemplates()
})

onMounted(loadInstances)
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.hint.err {
  color: var(--red);
}
</style>
