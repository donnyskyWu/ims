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
        <div class="d" data-testid="wb-todo-hint">{{ todoWidgetHint }}</div>
        <button
          v-if="dashReady && dashError"
          class="btn btn-txt btn-sm"
          type="button"
          data-testid="wb-dash-retry"
          @click="load"
        >
          重试
        </button>
      </div>
      <router-link class="card stat hov" to="/ims/flow" style="text-decoration: none; color: inherit">
        <span class="l">流程待办</span>
        <div class="n">{{ dashReady ? dash.flowTodoCount ?? '—' : '—' }}</div>
        <div class="d" data-testid="wb-flow-hint">{{ flowWidgetHint }}</div>
      </router-link>
      <div class="card stat">
        <span class="l">未读消息</span>
        <div class="n">{{ dashReady ? dash.unreadMessageCount ?? '—' : '—' }}</div>
        <div class="d" data-testid="wb-unread-hint">{{ unreadWidgetHint }}</div>
      </div>
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
                <div class="empty">
                  <div class="et">{{ flowError ? '加载失败' : '暂无流程待办' }}</div>
                  <div v-if="flowError" class="es">{{ flowError }}</div>
                  <button
                    v-if="flowError"
                    class="btn btn-txt btn-sm"
                    type="button"
                    data-testid="wb-flow-retry"
                    @click="load"
                  >
                    重试
                  </button>
                </div>
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
                <div class="empty">
                  <div class="et">{{ todoError ? '加载失败' : '没有待办' }}</div>
                  <div v-if="todoError" class="es">{{ todoError }}</div>
                  <button
                    v-if="todoError"
                    class="btn btn-txt btn-sm"
                    type="button"
                    data-testid="wb-todo-retry"
                    @click="load"
                  >
                    重试
                  </button>
                </div>
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
                <div class="empty">
                  <div class="et">{{ msgError ? '加载失败' : '没有消息' }}</div>
                  <div v-if="msgError" class="es">{{ msgError }}</div>
                  <button
                    v-if="msgError"
                    class="btn btn-txt btn-sm"
                    type="button"
                    data-testid="wb-msg-retry"
                    @click="load"
                  >
                    重试
                  </button>
                </div>
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
const dash = reactive<{ todoCount?: number; flowTodoCount?: number; unreadMessageCount?: number }>({})
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
  if (dashError.value) return '工作台加载失败'
  const flow = dash.flowTodoCount ?? '—'
  return `待办 ${dash.todoCount ?? '—'} · 流程 ${flow} · 未读 ${dash.unreadMessageCount ?? '—'}`
})

function widgetHint(ready: boolean, error: string, count: number | undefined, zero: string, normal: string) {
  if (!ready) return '正在读取'
  if (error) return '加载失败'
  if ((count ?? 0) === 0) return zero
  return normal
}

const todoWidgetHint = computed(() =>
  widgetHint(dashReady.value, dashError.value, dash.todoCount, '暂无待办', '本人待处理'),
)
const flowWidgetHint = computed(() =>
  widgetHint(dashReady.value, dashError.value, dash.flowTodoCount, '暂无流程待办', '待我处理的流程'),
)
const unreadWidgetHint = computed(() =>
  widgetHint(dashReady.value, dashError.value, dash.unreadMessageCount, '暂无未读', '站内未读'),
)

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

function overdueLabel(row: Record<string, unknown>) {
  if (row.overdue === true) return '是'
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
