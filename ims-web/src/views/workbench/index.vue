<template>
  <div class="page">
    <div style="margin: 6px 0 22px">
      <h1 style="font-size: 30px; font-weight: 700; letter-spacing: -0.7px; line-height: 1.07">{{ hello }}，{{ name }}</h1>
      <div class="sub" style="margin-top: 6px">{{ dashLine }}</div>
    </div>
    <div class="g4">
      <div class="card stat">
        <span class="l">待办预览</span>
        <div class="n">{{ dashReady ? dash.todoCount ?? '—' : '—' }}</div>
        <div class="d">{{ dashError || 'GET /auth/workbench/dashboard' }}</div>
      </div>
      <router-link class="card stat hov" to="/ims/flow" style="text-decoration: none; color: inherit">
        <span class="l">流程待办</span>
        <div class="n">{{ dashReady ? dash.flowTodoCount ?? '—' : '—' }}</div>
        <div class="d">GET /flow/task/my-todo · 流程管理</div>
      </router-link>
      <div class="card stat">
        <span class="l">未读消息</span>
        <div class="n">{{ dashReady ? dash.unreadMessageCount ?? '—' : '—' }}</div>
        <div class="d">{{ dashError || 'GET /auth/workbench/dashboard' }}</div>
      </div>
    </div>
    <div class="g4" data-testid="wb-mine-cards">
      <router-link
        v-for="card in mineCards"
        :key="card.key"
        class="card stat hov"
        :class="{ 'wb-card-empty': card.empty }"
        :to="card.to"
        :data-testid="card.testId"
        style="text-decoration: none; color: inherit"
      >
        <span class="l">
          {{ card.label }}
          <span
            v-if="card.badge"
            class="badge"
            style="position: static; margin-left: 6px"
            data-testid="wb-cert-warn"
          >{{ card.badge }}</span>
        </span>
        <div class="n">{{ card.value }}</div>
        <div class="d">{{ card.hint }}</div>
      </router-link>
    </div>
    <div class="sec rowline" style="justify-content: space-between; align-items: baseline">
      <span>流程待办</span>
      <router-link class="btn btn-txt btn-sm" to="/ims/flow">全部流程</router-link>
    </div>
    <div class="tbl-block" style="margin-bottom: 16px">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>实例单号</th>
              <th>模板</th>
              <th>节点</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!flowReady">
              <td colspan="3" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!flowTodos.length">
              <td colspan="3" style="white-space: normal">
                <div class="empty"><div class="et">{{ flowError || '暂无流程待办' }}</div></div>
              </td>
            </tr>
            <tr
              v-for="row in flowTodos"
              v-else
              :key="row.id"
              :data-testid="flowAccountNo(row) ? 'wb-acct-transfer-flow' : undefined"
            >
              <td class="mono">{{ row.instanceNo }}</td>
              <td>
                {{ row.templateName }}
                <span v-if="flowAccountNo(row)">{{ flowAccountNo(row) }}</span>
              </td>
              <td>
                {{ row.nodeName }}
                <button
                  v-if="transferFlowPath(row)"
                  class="btn btn-txt btn-sm"
                  type="button"
                  data-testid="wb-acct-transfer-flow-go"
                  @click="router.push(transferFlowPath(row))"
                >
                  去处理
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="sec">待办</div>
    <div class="tbl-block" style="margin-bottom: 16px">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>状态</th>
              <th>逾期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!todoReady">
              <td colspan="4" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!todos.length">
              <td colspan="4" style="white-space: normal">
                <div class="empty"><div class="et">{{ todoError || '没有待办' }}</div></div>
              </td>
            </tr>
            <tr
              v-for="(row, index) in todos"
              v-else
              :key="String(row.id ?? index)"
              :style="row.overdue ? 'background:#fff4f2' : ''"
              :data-testid="String(row.taskType || '') === 'acct_transfer' ? 'wb-acct-transfer-todo' : undefined"
            >
              <td>{{ cell(row, ['title']) }}</td>
              <td>{{ cell(row, ['status']) }}</td>
              <td>{{ overdueLabel(row) }}</td>
              <td>
                <router-link
                  v-if="String(row.taskType) === 'exam'"
                  class="btn btn-txt"
                  to="/ims/perf/exam"
                >
                  去考试
                </router-link>
                <button
                  v-if="transferTodoPath(row)"
                  class="btn btn-txt"
                  type="button"
                  data-testid="wb-acct-transfer-go"
                  @click="router.push(transferTodoPath(row))"
                >
                  去处理
                </button>
                <button
                  v-else-if="String(row.status) === 'PENDING' && row.id != null"
                  class="btn btn-txt"
                  type="button"
                  @click="closeTodo(row)"
                >
                  关闭
                </button>
                <span v-else class="hint">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div class="sec rowline" style="justify-content: space-between; align-items: center">
      <span>
        消息
        <span
          v-if="dashReady && (dash.unreadMessageCount || 0) > 0"
          class="badge"
          style="position: static; margin-left: 8px"
          data-testid="wb-msg-unread"
        >{{ dash.unreadMessageCount }}</span>
      </span>
      <span>
        <button class="btn btn-txt btn-sm" type="button" data-testid="wb-msg-read-all" @click="readAll">全部已读</button>
        <router-link class="btn btn-txt btn-sm" to="/ims/workbench/messages">查看更多</router-link>
      </span>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>已读</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!msgReady">
              <td colspan="3" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!messages.length">
              <td colspan="3" style="white-space: normal">
                <div class="empty"><div class="et">{{ msgError || '没有消息' }}</div></div>
              </td>
            </tr>
            <tr v-for="(row, index) in messages" v-else :key="String(row.id ?? index)">
              <td>{{ cell(row, ['title']) }}</td>
              <td>{{ readLabel(row) }}</td>
              <td>
                <button v-if="!isRead(row)" class="btn btn-txt" type="button" @click="read(row)">标为已读</button>
                <span v-else class="hint">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <p v-if="actionError" class="hint">{{ actionError }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'
import { asList, cell, readData } from '../../api/read'
import { notifyInboxChanged, onInboxChanged } from '../../inbox/sync'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const user = useUserStore()

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

function transferTodoPath(row: Record<string, unknown>) {
  if (String(row.taskType || '') !== 'acct_transfer') return ''
  const refId = Number(row.refId || 0)
  if (!refId) return ''
  const platform = String(row.content || '').split('|')[0] || 'DOUYIN'
  return `/ims/corp/account/${platformSlug(platform)}?transferId=${refId}`
}

function flowForm(row: Record<string, unknown>) {
  const form = row.formData
  if (!form || typeof form !== 'object') return null
  return form as { transferId?: number; platform?: string; accountNo?: string }
}

function flowAccountNo(row: Record<string, unknown>) {
  return String(flowForm(row)?.accountNo || '')
}

function transferFlowPath(row: Record<string, unknown>) {
  const form = flowForm(row)
  if (!form?.transferId) return ''
  return `/ims/corp/account/${platformSlug(String(form.platform || 'DOUYIN'))}?transferId=${form.transferId}`
}
const dash = reactive<{
  todoCount?: number
  flowTodoCount?: number
  unreadMessageCount?: number
  myAccountCount?: number
  myAssetCount?: number
  myCertCount?: number
  myCertWarningCount?: number
  myLiveSessionCount?: number
}>({})
const flowTodos = ref<Record<string, unknown>[]>([])
const flowReady = ref(false)
const flowError = ref('')
const dashReady = ref(false)
const dashError = ref('')
const todos = ref<Record<string, unknown>[]>([])
const todoReady = ref(false)
const todoError = ref('')
const messages = ref<Record<string, unknown>[]>([])
const msgReady = ref(false)
const msgError = ref('')
const actionError = ref('')
const name = computed(() => user.profile?.nickname || user.profile?.username || '同事')
const hello = computed(() => {
  const hour = new Date().getHours()
  if (hour < 5) return '凌晨好'
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})
const dashLine = computed(() => {
  if (!dashReady.value) return '正在读取工作台'
  if (dashError.value) return dashError.value
  const flow = dash.flowTodoCount ?? '—'
  return `待办 ${dash.todoCount ?? '—'} · 流程 ${flow} · 未读 ${dash.unreadMessageCount ?? '—'}`
})

const mineCards = computed(() => {
  const ready = dashReady.value
  const account = dash.myAccountCount ?? 0
  const asset = dash.myAssetCount ?? 0
  const cert = dash.myCertCount ?? 0
  const warn = dash.myCertWarningCount ?? 0
  const live = dash.myLiveSessionCount ?? 0
  const show = (count: number) => (ready ? String(count) : '—')
  const emptyHint = (count: number, text: string) => (ready ? (count > 0 ? '名下统计桩' : text) : '统计桩')
  return [
    {
      key: 'account',
      label: '我名下账号',
      value: show(account),
      hint: emptyHint(account, '暂无'),
      to: '/ims/corp/account/douyin',
      testId: 'wb-card-account',
      empty: ready && account === 0,
      badge: '',
    },
    {
      key: 'asset',
      label: '我名下资产',
      value: show(asset),
      hint: emptyHint(asset, '暂无'),
      to: '/ims/corp/device/office',
      testId: 'wb-card-asset',
      empty: ready && asset === 0,
      badge: '',
    },
    {
      key: 'cert',
      label: '我的证件',
      value: show(cert),
      hint: ready ? (warn > 0 ? `预警 ${warn}` : '暂无预警') : '统计桩',
      to: '/ims/corp/resource/certificate',
      testId: 'wb-card-cert',
      empty: ready && cert === 0 && warn === 0,
      badge: ready && warn > 0 ? String(warn) : '',
    },
    {
      key: 'live',
      label: '我的场次',
      value: show(live),
      hint: emptyHint(live, '暂无'),
      to: '/ims/live/sessions',
      testId: 'wb-card-session',
      empty: ready && live === 0,
      badge: '',
    },
  ]
})

async function load() {
  const board = await readData('/auth/workbench/dashboard')
  dashReady.value = true
  dashError.value = board.error
  if (board.data && typeof board.data === 'object') Object.assign(dash, board.data)

  const flowRes = await readData('/flow/task/my-todo', { pageNo: 1, pageSize: 5 })
  flowReady.value = true
  flowError.value = flowRes.error
  flowTodos.value = asList(flowRes.data)

  const todoRes = await readData('/auth/workbench/todos', { pageNo: 1, pageSize: 20, status: 'PENDING' })
  todoReady.value = true
  todoError.value = todoRes.error
  todos.value = asList(todoRes.data)

  const msgRes = await readData('/auth/workbench/messages', { pageNo: 1, pageSize: 20 })
  msgReady.value = true
  msgError.value = msgRes.error
  messages.value = asList(msgRes.data)
}

function isRead(row: Record<string, unknown>) {
  return row.read === true || row.read === 1 || row.read === '1'
}

function readLabel(row: Record<string, unknown>) {
  return isRead(row) ? '是' : '否'
}

function overdueDays(deadline: unknown) {
  if (typeof deadline !== 'string' || deadline.length < 10) return 1
  const stamp = Date.parse(deadline.endsWith('Z') ? deadline : `${deadline}Z`)
  if (Number.isNaN(stamp)) return 1
  const days = Math.ceil((Date.now() - stamp) / 86_400_000)
  return days > 0 ? days : 1
}

function overdueLabel(row: Record<string, unknown>) {
  if (row.overdue === true) return `逾期 ${overdueDays(row.deadline)} 天`
  if (row.overdue === false) return '否'
  return cell(row, ['overdue'])
}

async function read(row: Record<string, unknown>) {
  actionError.value = ''
  const id = row.id
  if (id === undefined || id === null || id === '') {
    actionError.value = '这条消息没有 id，无法标记已读'
    return
  }
  try {
    await http.put(`/auth/workbench/messages/${id}/read`)
    notifyInboxChanged()
    await load()
  } catch (error) {
    actionError.value = errorMessage(error)
  }
}

async function readAll() {
  actionError.value = ''
  try {
    await http.put('/auth/workbench/messages/read-all')
    notifyInboxChanged()
    await load()
  } catch (error) {
    actionError.value = errorMessage(error)
  }
}

async function closeTodo(row: Record<string, unknown>) {
  actionError.value = ''
  const id = row.id
  if (id === undefined || id === null || id === '') {
    actionError.value = '这条待办没有 id，无法关闭'
    return
  }
  try {
    await http.put(`/auth/workbench/todos/${id}`, { action: 'CLOSE' })
    await load()
  } catch (error) {
    actionError.value = errorMessage(error)
  }
}

let stopInbox: (() => void) | null = null
onMounted(() => {
  load()
  stopInbox = onInboxChanged(load)
})
onBeforeUnmount(() => stopInbox?.())
</script>

<style scoped>
.wb-card-empty {
  border: 1px dashed var(--line);
  box-shadow: none;
}
</style>
