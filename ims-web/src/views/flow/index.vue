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
      <button type="button" class="cattab" :class="{ on: tab === 'todo' }" @click="tab = 'todo'">
        我的待办<span v-if="todoBadge">({{ todoBadge }})</span>
      </button>
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
        <option value="DISABLED">停用</option>
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

    <form v-else-if="tab === 'timeout'" class="qbar" @submit.prevent="loadTimeouts">
      <input v-model="timeoutFilters.templateName" placeholder="模板名称" style="width: 150px" data-testid="flow-timeout-template" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetTimeout">重置</button>
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
    <p v-if="tab === 'timeout' && urgeDone" class="hint" data-testid="flow-urge-done">{{ urgeDone }}</p>

    <p
      v-if="tab === 'todo' && handleHint"
      class="hint"
      :class="{ err: handleHintErr }"
      data-testid="flow-handle-hint"
    >
      {{ handleHint }}
    </p>
    <p
      v-if="tab === 'template' && draftHint"
      class="hint"
      :class="{ err: draftHintErr }"
      data-testid="flow-draft-hint"
    >
      {{ draftHint }}
    </p>
    <p v-if="tab === 'timeout' && urgeHint" class="hint" data-testid="flow-dingtalk-stub">{{ urgeHint }}</p>

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
                  <div class="et">{{ timeoutEmptyText }}</div>
                  <div v-if="!error && !timeoutFilters.templateName.trim()" class="es">未超过 SLA 的待办不会出现在督办清单</div>
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
              <th>SLA 截止</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!todoRows.length">
              <td colspan="6">
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
              <td data-testid="flow-sla" :style="{ color: slaColor(row.slaTone), fontWeight: row.slaTone === 'normal' ? 400 : 600 }">
                {{ row.slaDeadline || '—' }}
                <span v-if="row.slaTone === 'warn'">临期</span>
                <span v-if="row.slaTone === 'timeout'">超时</span>
              </td>
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
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!tplRows.length">
              <td colspan="8">
                <div class="empty" data-testid="flow-template-empty">
                  <div class="et">{{ templateEmptyText }}</div>
                  <div v-if="!error && templateEmptyHint" class="es">{{ templateEmptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in tplRows" v-else :key="row.id">
              <td class="mono">{{ row.templateCode }}</td>
              <td style="font-weight: 500">{{ row.templateName }}</td>
              <td>{{ row.businessDomainLabel }}</td>
              <td>{{ row.versionLabel }}</td>
              <td class="num">{{ row.nodeCount }}</td>
              <td><span class="tag tag-info">{{ row.statusLabel }}</span></td>
              <td class="csub">{{ row.updatedAt }}</td>
              <td>
                <span class="btn-txt btn" @click="previewTemplate(row)">预览</span>
                <span v-if="row.status === 'DRAFT'" class="btn-txt btn" data-testid="flow-draft-try" @click="tryStartDraft(row)">
                  试发起
                </span>
              </td>
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
          <label>标题（必填 · ≤256）</label>
          <input v-model="startForm.title" data-testid="flow-start-title" placeholder="formData.title" />
          <p class="hint" :class="{ bad: startTitle.length > 256 }">{{ startTitle.length }}/256</p>
        </div>
        <div class="fld">
          <label>businessKey（可选 · 幂等 · ≤64）</label>
          <input v-model="startForm.businessKey" data-testid="flow-start-key" />
          <p class="hint" data-testid="flow-start-idem-hint">同一 businessKey 再次提交会沿用原单，不会新建</p>
          <p class="hint" :class="{ bad: startKey.length > 64 }">{{ startKey.length }}/64</p>
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

    <ProtoDrawer :open="approveOpen" title="通过待办" width="480px" @close="closeApprove">
      <p class="hint" data-testid="flow-approve-copy">意见可选，不超过 512 字。留空按无意见通过。</p>
      <p v-if="approveTarget" class="csub">{{ approveTarget.instanceNo }} · {{ approveTarget.nodeName }}</p>
      <div class="fld">
        <label>补充表单</label>
        <div v-if="!approveFormPairs.length" class="empty" data-testid="flow-approve-form-empty" style="padding: 12px">
          <div class="et">暂无补充表单</div>
        </div>
        <ul v-else data-testid="flow-approve-form" style="margin: 0; padding-left: 18px">
          <li v-for="pair in approveFormPairs" :key="pair[0]">{{ pair[0] }}：{{ pair[1] }}</li>
        </ul>
      </div>
      <div class="fld">
        <label>审批意见</label>
        <textarea v-model="approveComment" data-testid="flow-approve-comment" rows="3" placeholder="可不填" />
      </div>
      <p class="hint" :class="{ bad: approveComment.trim().length > 512 }">{{ approveComment.trim().length }}/512</p>
      <p v-if="approveMsg" class="hint err" data-testid="flow-approve-msg">{{ approveMsg }}</p>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" data-testid="flow-approve-cancel" @click="closeApprove">取消</button>
        <button
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="flow-approve-confirm"
          :disabled="approveSaving"
          @click="submitApprove"
        >
          {{ approveSaving ? '提交中…' : '确认通过' }}
        </button>
      </template>
    </ProtoDrawer>

    <div v-if="previewOpen" class="modal-mask" data-testid="flow-template-preview" @click.self="previewOpen = false">
      <div class="modal-card" style="width: min(480px, 92vw)">
        <h3 style="margin: 0 0 8px">流程预览 · {{ previewTitle }}</h3>
        <p class="hint">{{ previewMeta }}</p>
        <ol style="margin: 8px 0 12px; padding-left: 18px">
          <li v-for="node in previewNodes" :key="node.nodeOrder" style="margin: 4px 0">
            {{ node.nodeName }}（{{ node.nodeType }}）· {{ node.assigneePreview }}
          </li>
        </ol>
        <div class="acts" style="justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="previewOpen = false">关闭</button>
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
    slaDeadline?: string
    slaTone?: string
    formData?: { transferId?: number; platform?: string; accountNo?: string; title?: string; [key: string]: string | number | null | undefined }
  }[]
>([])
const todoBadge = ref(0)
const todoFilters = ref({ businessDomain: '' })
const timeoutFilters = ref({ templateName: '' })
const handleHint = ref('')
const handleHintErr = ref(false)
const draftHint = ref('')
const draftHintErr = ref(false)
const urgeHint = ref('')
const previewOpen = ref(false)
const previewTitle = ref('')
const previewMeta = ref('')
const previewNodes = ref<{ nodeOrder: number; nodeName: string; nodeType: string; assigneePreview: string }[]>([])
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

const todoEmptyText = computed(() => {
  if (error.value) return error.value
  if (todoFilters.value.businessDomain) return '该业务域暂无待办'
  return '暂无待办'
})
const templateEmptyText = computed(() => {
  if (error.value) return error.value
  const name = tplFilters.value.templateName.trim()
  const domain = tplFilters.value.businessDomain
  const status = tplFilters.value.status
  if (status === 'DRAFT') return '暂无草稿模板'
  if (status === 'DISABLED') return '暂无停用模板'
  if (status === 'PUBLISHED' && !name && !domain) return '暂无已发布模板'
  if (domain && !name && !status) return '该业务域暂无模板'
  if (name || domain || status) return '没有符合条件的模板'
  return '暂无模板'
})
const templateEmptyHint = computed(() => {
  if (error.value) return ''
  const name = tplFilters.value.templateName.trim()
  const domain = tplFilters.value.businessDomain
  const status = tplFilters.value.status
  if (status === 'DRAFT') return '草稿只能预览，发布后才能发起'
  if (status === 'DISABLED') return '停用后不可发起新实例，在途实例仍按原版本运行'
  if (status === 'PUBLISHED' && !name && !domain) return '发布模板后才能发起流程'
  if (domain && !name && !status) return '换一个业务域，或点重置查看全部模板'
  if (name || domain || status) return '调整名称、业务域或状态后再查询'
  return ''
})
const timeoutEmptyText = computed(() => {
  if (error.value) return error.value
  if (timeoutFilters.value.templateName.trim()) return '没有符合条件的超时待办'
  return '暂无超时待办'
})

function rejectedBody(e: unknown): { code?: number; msg?: string; data?: { remindCount?: number; commentHint?: string } } | null {
  if (e && typeof e === 'object' && 'code' in e) return e as { code?: number; msg?: string; data?: { remindCount?: number; commentHint?: string } }
  return null
}

function slaColor(tone?: string) {
  if (tone === 'timeout') return 'var(--red)'
  if (tone === 'warn') return '#b86e00'
  return 'inherit'
}
const startOpen = ref(false)
const startLoading = ref(false)
const startTemplatesLoading = ref(false)
const startMsg = ref('')
const startErr = ref(false)
const publishedTemplates = ref<{ id: number; templateCode: string; templateName: string }[]>([])
const startForm = ref({ templateId: 0, title: '', businessKey: '' })
const startTitle = computed(() => startForm.value.title.trim())
const startKey = computed(() => startForm.value.businessKey.trim())
const approveOpen = ref(false)
const approveSaving = ref(false)
const approveComment = ref('')
const approveMsg = ref('')
const approveTarget = ref<{
  id: number
  instanceNo: string
  nodeName: string
  formData?: Record<string, string | number | null | undefined>
} | null>(null)
const approveFormPairs = computed(() => {
  const data = approveTarget.value?.formData || {}
  return Object.entries(data).filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
})
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
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (timeoutFilters.value.templateName.trim()) params.templateName = timeoutFilters.value.templateName.trim()
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
    if (res.data.code === 5003) {
      urgeHint.value = res.data.msg || '钉钉推送失败已入补发队列'
      urgeOpen.value = false
      await loadTimeouts()
      return
    }
    if (res.data.code !== 0) {
      urgeMsg.value = res.data.msg || '督办失败'
      urgeErr.value = true
      return
    }
    const count = res.data.data?.remindCount
    urgeDone.value = `已督办 ${row.instanceNo}，提醒次数 ${count ?? row.remindCount + 1}`
    urgeHint.value = `已通过钉钉桩提醒处理人${count != null ? `（第 ${count} 次）` : ''}`
    urgeOpen.value = false
    await loadTimeouts()
  } catch (e: unknown) {
    const body = rejectedBody(e)
    if (body?.code === 5003) {
      urgeHint.value = body.msg || '钉钉推送失败已入补发队列'
      urgeOpen.value = false
      await loadTimeouts()
      return
    }
    urgeMsg.value = body?.msg || (e instanceof Error ? e.message : '网络错误')
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
    if (!todoFilters.value.businessDomain) todoBadge.value = total.value
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

async function refreshTodoBadge() {
  try {
    const res = await http.get('/flow/task/my-todo', { params: { pageNo: 1, pageSize: 1 } })
    if (res.data.code === 0) todoBadge.value = res.data.data.total || 0
  } catch {
    /* 徽标失败不阻断列表 */
  }
}

function openApprove(row: {
  id: number
  instanceNo: string
  nodeName: string
  formData?: Record<string, string | number | null | undefined>
}) {
  approveTarget.value = row
  approveComment.value = ''
  approveMsg.value = ''
  approveOpen.value = true
}

function closeApprove() {
  if (approveSaving.value) return
  approveOpen.value = false
}

async function submitApprove() {
  const row = approveTarget.value
  if (!row) return
  const comment = approveComment.value.trim()
  if (comment.length > 512) {
    approveMsg.value = '审批意见不能超过 512 字'
    return
  }
  approveSaving.value = true
  approveMsg.value = ''
  handleHint.value = ''
  handleHintErr.value = false
  try {
    const res = await http.put(`/flow/task/${row.id}/handle`, { action: 'APPROVE', comment })
    const hint = String(res.data.data?.commentHint || '')
    handleHint.value = hint ? `通过成功。${hint}` : '通过成功'
    approveOpen.value = false
    await loadTodos()
    await refreshTodoBadge()
  } catch (e: unknown) {
    const body = rejectedBody(e)
    approveMsg.value = body?.msg || (e instanceof Error ? e.message : '网络错误')
    if (body?.code === 1135 || String(body?.msg || '').includes('已处理')) {
      approveOpen.value = false
      await loadTodos()
    }
  } finally {
    approveSaving.value = false
  }
}

async function handleTask(row: { id: number; instanceNo?: string; nodeName?: string }, action: 'APPROVE' | 'REJECT') {
  if (action === 'APPROVE') {
    openApprove({
      id: row.id,
      instanceNo: row.instanceNo || '',
      nodeName: row.nodeName || '',
      formData: (row as { formData?: Record<string, string | number | null | undefined> }).formData,
    })
    return
  }
  const entered = window.prompt('驳回意见（可选，驳回建议填写）', '')
  if (entered === null) return
  if (!confirm('确认驳回该待办？')) return
  handleHint.value = ''
  handleHintErr.value = false
  try {
    const res = await http.put(`/flow/task/${row.id}/handle`, { action, comment: entered })
    const hint = String(res.data.data?.commentHint || '')
    handleHintErr.value = false
    handleHint.value = hint ? `驳回成功。${hint}` : '驳回成功'
    await loadTodos()
    await refreshTodoBadge()
  } catch (e: unknown) {
    const body = rejectedBody(e)
    handleHintErr.value = true
    handleHint.value = body?.msg || (e instanceof Error ? e.message : '网络错误')
    if (body?.code === 1135 || String(body?.msg || '').includes('已处理')) await loadTodos()
  }
}

function resetTodo() {
  todoFilters.value = { businessDomain: '' }
  handleHint.value = ''
  loadTodos()
}

function resetTimeout() {
  timeoutFilters.value = { templateName: '' }
  urgeHint.value = ''
  loadTimeouts()
}

async function previewTemplate(row: Record<string, unknown>) {
  draftHint.value = ''
  try {
    const res = await http.get(`/flow/template/${Number(row.id)}/preview`)
    if (res.data.code !== 0) {
      draftHintErr.value = true
      draftHint.value = res.data.msg || '预览失败'
      return
    }
    const data = res.data.data
    previewTitle.value = data.templateName || String(row.templateName || '')
    const graph = data.graphType === 'SERIAL' ? '串行' : data.graphType
    const draftNote = data.canStart ? '已发布，可发起' : '草稿仅可预览，不可发起'
    previewMeta.value = `${graph} · ${data.statusLabel || ''} · ${draftNote}`
    previewNodes.value = data.nodes || []
    previewOpen.value = true
  } catch (e: unknown) {
    draftHintErr.value = true
    draftHint.value = e instanceof Error ? e.message : '网络错误'
  }
}

async function tryStartDraft(row: Record<string, unknown>) {
  draftHint.value = ''
  draftHintErr.value = false
  const templateId = Number(row.id)
  try {
    const res = await http.post('/flow/instance', {
      templateId,
      formData: { title: '草稿试发起' },
      businessKey: `draft-try-${templateId}-${Date.now()}`,
    })
    draftHintErr.value = false
    draftHint.value = `已发起：${res.data.data.instanceNo}`
  } catch (e: unknown) {
    const body = rejectedBody(e)
    draftHintErr.value = true
    if (body?.code === 1134) {
      draftHint.value = `草稿不可发起（1134）：${body.msg || '仅已发布模板可发起新实例'}`
      return
    }
    draftHint.value = body?.msg || (e instanceof Error ? e.message : '网络错误')
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
  if (!startForm.value.templateId) {
    startMsg.value = '请选择模板'
    startErr.value = true
    return
  }
  if (!startTitle.value) {
    startMsg.value = '请填写标题'
    startErr.value = true
    return
  }
  if (startTitle.value.length > 256) {
    startMsg.value = '标题不能超过 256 字'
    startErr.value = true
    return
  }
  if (startKey.value.length > 64) {
    startMsg.value = 'businessKey 不能超过 64 字'
    startErr.value = true
    return
  }
  startLoading.value = true
  startMsg.value = ''
  startErr.value = false
  try {
    const payload: Record<string, unknown> = {
      templateId: startForm.value.templateId,
      formData: { title: startTitle.value },
    }
    if (startKey.value) payload.businessKey = startKey.value
    const res = await http.post('/flow/instance', payload)
    const data = res.data.data || {}
    if (data.idempotent) {
      startMsg.value = `该 businessKey 已发起过，沿用原单 ${data.instanceNo}（未新建）`
      startErr.value = false
      return
    }
    startMsg.value = `已发起：${data.instanceNo}`
    startOpen.value = false
    tab.value = 'instance'
    await loadInstances()
  } catch (e: unknown) {
    const body = rejectedBody(e)
    startMsg.value = body?.msg || (e instanceof Error ? e.message : '网络错误')
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

onMounted(() => {
  loadInstances()
  refreshTodoBadge()
})
</script>

<style scoped>
.flow-modal-mask,
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 220;
}
.flow-modal-card,
.modal-card {
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
.hint.err {
  color: var(--red);
}
</style>
