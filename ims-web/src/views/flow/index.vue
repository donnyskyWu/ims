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
              <td>{{ row.templateName }}</td>
              <td>{{ row.nodeName }}</td>
              <td>{{ row.initiatorName || '—' }}</td>
              <td>
                <span class="btn-txt btn" @click="handleTask(row, 'APPROVE')">通过</span>
                <span class="btn-txt btn" style="color: var(--red)" @click="handleTask(row, 'REJECT')">驳回</span>
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
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无实例' }}</div></div></td>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { http } from '../../api/http'

const tab = ref<'instance' | 'template' | 'todo' | 'timeout'>('instance')
const loading = ref(false)
const error = ref('')
const total = ref(0)
const instRows = ref<Record<string, unknown>[]>([])
const todoRows = ref<{ id: number; instanceNo: string; templateName: string; nodeName: string; initiatorName: string }[]>([])
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
  if (t === 'instance') loadInstances()
  else if (t === 'todo') loadTodos()
  else if (t === 'timeout') loadTimeouts()
  else loadTemplates()
})

onMounted(loadInstances)
</script>
