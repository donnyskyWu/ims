<template>
  <div class="msg-bell">
    <button
      class="tb-ic"
      type="button"
      aria-label="消息中心"
      data-testid="topbar-msg-bell"
      @click="openDrawer"
    >
      <Ico name="bell" :size="19" />
      <span v-if="unreadCount > 0" class="badge" data-testid="topbar-unread-badge">{{ badgeText }}</span>
    </button>
    <div v-if="open" class="mask on" data-testid="topbar-msg-mask" @click="closeDrawer" />
    <aside v-if="open" class="msgdrawer on" data-testid="topbar-msg-drawer" aria-label="消息中心抽屉">
      <div class="drawer-h">
        <b>{{ detail ? '消息详情' : '消息中心' }}</b>
        <div style="display: flex; gap: 8px; align-items: center">
          <button
            v-if="!detail"
            class="btn btn-sec btn-sm"
            type="button"
            data-testid="topbar-msg-read-all"
            @click="readAll"
          >
            全部已读
          </button>
          <button v-if="detail" class="btn btn-txt btn-sm" type="button" @click="detail = null">返回</button>
          <button class="btn btn-sec btn-sm" type="button" @click="closeDrawer">关闭</button>
        </div>
      </div>
      <div v-if="detail" class="drawer-b" data-testid="topbar-msg-detail">
        <div class="mt">{{ detail.title }}</div>
        <div class="md">{{ detail.sourceModule || '站内' }} · {{ timeLabel(detail.createdAt) }}</div>
        <p style="margin-top: 12px; font-size: 13px; line-height: 1.55">{{ detail.content || '无正文' }}</p>
        <div v-if="sourcePath(detail)" style="margin-top: 16px">
          <button class="btn btn-pri btn-sm" type="button" @click="openSource(detail)">查看来源</button>
        </div>
      </div>
      <div v-else class="mg-list">
        <div v-if="loading" class="empty"><div class="et">加载中</div></div>
        <div v-else-if="error" class="empty"><div class="et">{{ error }}</div></div>
        <div v-else-if="!rows.length" class="empty" data-testid="topbar-msg-empty">
          <div class="et">暂无消息</div>
        </div>
        <div
          v-for="row in rows"
          v-else
          :key="row.id"
          class="mg-i"
          :class="{ read: row.read }"
          data-testid="topbar-msg-item"
          @click="openDetail(row)"
        >
          <span class="mg-ud" />
          <div>
            <div class="mt">{{ row.title }}</div>
            <div class="mc">{{ row.content || row.sourceModule || '站内消息' }}</div>
            <div class="md">{{ row.read ? '已读' : '未读' }} · {{ timeLabel(row.createdAt) }}</div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../api/http'
import { onInboxChanged, notifyInboxChanged } from '../inbox/sync'
import Ico from './Ico.vue'

type InboxMessage = {
  id: number
  title: string
  content?: string
  read?: boolean
  sourceModule?: string
  refType?: string
  refId?: number
  createdAt?: string
}

const router = useRouter()
const open = ref(false)
const loading = ref(false)
const error = ref('')
const rows = ref<InboxMessage[]>([])
const detail = ref<InboxMessage | null>(null)
const unreadCount = ref(0)

const badgeText = computed(() => (unreadCount.value > 99 ? '99+' : String(unreadCount.value)))

function timeLabel(value?: string) {
  if (!value) return '—'
  return value.slice(0, 16).replace('T', ' ')
}

function sourcePath(row: InboxMessage) {
  const ref = row.refType || ''
  const id = Number(row.refId || 0)
  if (!ref || !id) return ''
  if (ref === 'cert_remind' || ref === 'cert_expire') return '/ims/corp/resource/certificate'
  if (ref === 'acct_recharge_verify' || ref === 'acct_transfer') return '/ims/corp/account/douyin'
  if (ref === 'live_report_overdue' || ref === 'live_session' || ref === 'live_alarm') return '/ims/live/sessions'
  return ''
}

async function refreshCount() {
  try {
    const res = await http.get('/auth/workbench/dashboard')
    unreadCount.value = Number(res.data.data?.unreadMessageCount || 0)
  } catch {
    unreadCount.value = 0
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/auth/workbench/messages', { params: { pageNo: 1, pageSize: 20 } })
    rows.value = res.data.data?.list || []
  } catch (err) {
    error.value = errorMessage(err)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function openDrawer() {
  open.value = true
  detail.value = null
  await loadList()
}

function closeDrawer() {
  open.value = false
  detail.value = null
}

async function openDetail(row: InboxMessage) {
  detail.value = row
  if (row.read) return
  try {
    await http.put(`/auth/workbench/messages/${row.id}/read`)
    notifyInboxChanged()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function readAll() {
  error.value = ''
  try {
    await http.put('/auth/workbench/messages/read-all')
    notifyInboxChanged()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function syncInbox() {
  await refreshCount()
  if (open.value) await loadList()
}

function openSource(row: InboxMessage) {
  const path = sourcePath(row)
  if (!path) return
  closeDrawer()
  router.push(path)
}

let stop: (() => void) | null = null
onMounted(() => {
  refreshCount()
  stop = onInboxChanged(syncInbox)
})
onBeforeUnmount(() => stop?.())
</script>

<style scoped>
.msg-bell {
  display: flex;
  flex: none;
}
</style>
