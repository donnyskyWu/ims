<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>抖音内部账号采集</h1>
        <div class="sub">C2/C3/C4 · 同一 IMS 定时器采集作品、作品日快照与粉丝日统计</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="goTasks">采集任务</button>
        <button class="btn btn-sec btn-sm" type="button" @click="goAccount">抖音账号台账</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      凭证加密入库，页面只显示掩码和凭证引用。作品写入 <code>oa_douyin_video</code>，作品日快照写入
      <code>oa_douyin_video_snapshot</code>，粉丝列表写入 <code>oa_douyin_follower</code>，粉丝日统计写入
      <code>oa_douyin_follower_daily</code>。同一天重复采集按日更新。播放、点赞、评论、转发来自作品列表；Collector
      作品统计与列表重复，日快照已覆盖。Cookie 已失效、浏览器引擎不可用与粉丝统计失败分开显示。
    </p>

    <form class="qbar" style="align-items: flex-end" @submit.prevent="saveAccount">
      <label class="fld">
        昵称
        <input v-model="form.accountName" data-testid="dy-nickname" required />
      </label>
      <label class="fld">
        公司
        <select v-model.number="form.companyId" data-testid="dy-company" required>
          <option disabled value="">请选择</option>
          <option v-for="item in companies" :key="item.id" :value="item.id">{{ item.companyName }}</option>
        </select>
      </label>
      <label class="fld">
        IP 组
        <select v-model.number="form.ipGroupId" data-testid="dy-ip-group" required>
          <option disabled value="">请选择</option>
          <option v-for="item in groups" :key="item.id" :value="item.id">{{ item.groupName }}</option>
        </select>
      </label>
      <label class="fld">
        平台账号 ID
        <input v-model="form.platformAccountId" data-testid="dy-platform-id" required />
      </label>
      <label class="fld">
        凭证
        <input
          v-model="form.cookie"
          data-testid="dy-credential"
          type="password"
          autocomplete="new-password"
          :placeholder="editingId ? '留空则不修改' : '只写入，不回显'"
          :required="!editingId"
        />
      </label>
      <label class="fld">
        频率
        <select v-model="form.frequency" data-testid="dy-frequency">
          <option value="HOURLY">HOURLY</option>
          <option value="DAILY">DAILY</option>
          <option value="WEEKLY">WEEKLY</option>
        </select>
      </label>
      <label class="fld">
        Cron
        <input v-model="form.cron" data-testid="dy-cron" />
      </label>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="dy-save">{{ editingId ? '更新账号' : '保存账号' }}</button>
      <button v-if="editingId" class="btn btn-sec btn-sm" type="button" @click="resetForm">取消编辑</button>
    </form>
    <p v-if="notice" class="hint" data-testid="dy-notice">{{ notice }}</p>
    <p v-if="nextRunAt" class="hint" data-testid="dy-next-run">下次定时采集 {{ nextRunAt }}（IMS 定时器，可随时手动触发）</p>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="dy-account-table">
          <thead>
            <tr>
              <th>昵称</th>
              <th>平台账号 ID</th>
              <th>凭证掩码</th>
              <th>凭证引用</th>
              <th>绑定</th>
              <th>健康</th>
              <th>最新粉丝</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!accounts.length">
              <td colspan="8">暂无抖音内部账号</td>
            </tr>
            <tr v-for="row in accounts" :key="row.id" :data-testid="'dy-row-' + row.platformAccountId">
              <td>{{ row.accountName }}</td>
              <td class="mono">{{ row.platformAccountId || '—' }}</td>
              <td class="mono" data-testid="dy-mask">{{ row.credentialMask || '未配置' }}</td>
              <td class="mono">{{ row.credentialRef || '—' }}</td>
              <td>{{ row.collectBindSummary }}</td>
              <td data-testid="dy-health">{{ row.healthLabel }}</td>
              <td class="num" data-testid="dy-follower-latest">{{ followerText(row) }}</td>
              <td>
                <button class="btn-txt btn" type="button" @click="editRow(row)">编辑</button>
                <button class="btn-txt btn" type="button" @click="bindRow(row)">导入 Collector</button>
                <button class="btn-txt btn" type="button" @click="probeRow(row)">测试连接</button>
                <button class="btn-txt btn" type="button" data-testid="dy-run" @click="runRow(row)">立即采集</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 16px">粉丝日快照</h2>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="dy-follower-daily">
          <thead>
            <tr>
              <th>账号</th>
              <th>统计日</th>
              <th>粉丝数</th>
              <th>新增</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!followerRows.length">
              <td colspan="4">暂无粉丝日快照</td>
            </tr>
            <tr v-for="snap in followerRows" :key="snap.key">
              <td>{{ snap.accountName }}</td>
              <td class="num" data-testid="dy-follower-date">{{ snap.statDate }}</td>
              <td class="num" data-testid="dy-follower-count">{{ snap.followerCount }}</td>
              <td class="num">{{ snap.newFollowerCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 16px">作品日快照</h2>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="dy-video-snapshot">
          <thead>
            <tr>
              <th>账号</th>
              <th>作品</th>
              <th>统计日</th>
              <th>播放</th>
              <th>点赞</th>
              <th>评论</th>
              <th>转发</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!videoRows.length">
              <td colspan="7">暂无作品日快照</td>
            </tr>
            <tr v-for="snap in videoRows" :key="snap.key">
              <td>{{ snap.accountName }}</td>
              <td class="mono" data-testid="dy-video-id">{{ snap.videoId }}</td>
              <td class="num" data-testid="dy-video-date">{{ snap.statDate }}</td>
              <td class="num" data-testid="dy-video-play">{{ snap.playCount }}</td>
              <td class="num" data-testid="dy-video-like">{{ snap.likeCount }}</td>
              <td class="num" data-testid="dy-video-comment">{{ snap.commentCount }}</td>
              <td class="num" data-testid="dy-video-share">{{ snap.shareCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <h2 style="margin: 16px 0 8px; font-size: 16px">采集记录</h2>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table data-testid="dy-log-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>状态</th>
              <th>条数</th>
              <th>耗时</th>
              <th>开始时间</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!logs.length">
              <td colspan="6">暂无采集记录</td>
            </tr>
            <tr v-for="row in logs" :key="row.id">
              <td>{{ row.taskName }}</td>
              <td data-testid="dy-log-status">{{ row.statusLabel || row.status }}</td>
              <td class="num" data-testid="dy-log-count">{{ row.recordCount }}</td>
              <td class="num" data-testid="dy-log-duration">{{ row.durationMs }} ms</td>
              <td class="num">{{ row.startedAt }}</td>
              <td>{{ row.errorSummary || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, http } from '../../api/http'

type Opt = { id: number; companyName?: string; groupName?: string }
type FollowerDaily = { statDate: string; followerCount: number; newFollowerCount: number }
type VideoSnapshot = {
  videoId: string
  statDate: string
  playCount: number
  likeCount: number
  commentCount: number
  shareCount: number
}
type AccountRow = {
  id: number
  accountName: string
  platformAccountId: string
  credentialMask: string
  credentialRef: string
  collectBindSummary: string
  healthLabel: string
  followerCount?: number | null
  followerStatDate?: string
  followerDaily?: FollowerDaily[]
  videoSnapshots?: VideoSnapshot[]
}
type LogRow = {
  id: string
  taskName: string
  status: string
  statusLabel?: string
  recordCount: number
  durationMs: number
  startedAt: string
  errorSummary?: string | null
}

const router = useRouter()
const companies = ref<Opt[]>([])
const groups = ref<Opt[]>([])
const accounts = ref<AccountRow[]>([])
const logs = ref<LogRow[]>([])
const notice = ref('')
const nextRunAt = ref('')
const editingId = ref<number | null>(null)
const form = reactive({
  accountName: '',
  companyId: '' as number | '',
  ipGroupId: '' as number | '',
  platformAccountId: '',
  cookie: '',
  frequency: 'DAILY',
  cron: '0 2 * * *',
})

const followerRows = computed(() => {
  const rows: Array<FollowerDaily & { accountName: string; key: string }> = []
  for (const account of accounts.value) {
    for (const snap of account.followerDaily || []) {
      rows.push({ ...snap, accountName: account.accountName, key: `${account.id}-${snap.statDate}` })
    }
  }
  return rows
})

const videoRows = computed(() => {
  const rows: Array<VideoSnapshot & { accountName: string; key: string }> = []
  for (const account of accounts.value) {
    for (const snap of account.videoSnapshots || []) {
      rows.push({ ...snap, accountName: account.accountName, key: `${account.id}-${snap.videoId}-${snap.statDate}` })
    }
  }
  return rows
})

function followerText(row: AccountRow) {
  if (row.followerCount == null) return '—'
  return row.followerStatDate ? `${row.followerCount}（${row.followerStatDate}）` : String(row.followerCount)
}

function goTasks() {
  router.push('/ims/collect/task')
}
function goAccount() {
  router.push('/ims/corp/account/douyin')
}

function resetForm() {
  editingId.value = null
  form.accountName = ''
  form.platformAccountId = ''
  form.cookie = ''
  form.frequency = 'DAILY'
  form.cron = '0 2 * * *'
}

async function loadOptions() {
  const [companyRes, groupRes] = await Promise.all([
    http.get('/corp/resource/company/page', { params: { pageNo: 1, pageSize: 50, companyName: 'E2E抖音采集' } }),
    http.get('/ip-group/list', { params: { pageNo: 1, pageSize: 50, keyword: 'E2E抖音采集' } }),
  ])
  const companyList = (companyRes.data?.data?.list || []) as Opt[]
  const groupList = (groupRes.data?.data?.list || []) as Opt[]
  if (!companyList.length) {
    const all = await http.get('/corp/resource/company/page', { params: { pageNo: 1, pageSize: 50 } })
    companies.value = all.data?.data?.list || []
  } else {
    companies.value = companyList
  }
  if (!groupList.length) {
    const all = await http.get('/ip-group/list', { params: { pageNo: 1, pageSize: 50 } })
    groups.value = all.data?.data?.list || []
  } else {
    groups.value = groupList
  }
}

async function loadAccounts() {
  const res = await http.get('/collect/douyin/account/page', { params: { pageNo: 1, pageSize: 50 } })
  accounts.value = res.data?.data?.list || []
}

async function loadLogs() {
  const res = await http.get('/collect/douyin/log/page', { params: { pageNo: 1, pageSize: 20 } })
  logs.value = res.data?.data?.list || []
}

function editRow(row: AccountRow) {
  editingId.value = row.id
  form.accountName = row.accountName
  form.platformAccountId = row.platformAccountId
  form.cookie = ''
  notice.value = '编辑时凭证留空则保持原值，页面不会回显明文。'
}

async function saveAccount() {
  notice.value = ''
  const payload: Record<string, unknown> = {
    accountName: form.accountName,
    platformAccountId: form.platformAccountId,
    frequency: form.frequency,
    cron: form.cron,
  }
  if (form.companyId) payload.companyId = form.companyId
  if (form.ipGroupId) payload.ipGroupId = form.ipGroupId
  if (form.cookie) payload.cookie = form.cookie
  try {
    const res = editingId.value
      ? await http.put(`/collect/douyin/account/${editingId.value}`, payload)
      : await http.post('/collect/douyin/account', payload)
    const data = res.data?.data
    nextRunAt.value = data?.task?.nextRunAt || ''
    const mask = data?.account?.credentialMask || ''
    notice.value = mask ? `已保存，凭证掩码 ${mask}` : '已保存'
    form.cookie = ''
    editingId.value = null
    await loadAccounts()
  } catch (e: unknown) {
    notice.value = errorMessage(e)
  }
}

async function bindRow(row: AccountRow) {
  notice.value = ''
  try {
    const res = await http.post(`/collect/douyin/account/${row.id}/bind`)
    notice.value = `已导入 Collector：${res.data?.data?.healthLabel || '已绑定'}`
    await loadAccounts()
  } catch (e: unknown) {
    notice.value = errorMessage(e)
  }
}

async function probeRow(row: AccountRow) {
  notice.value = ''
  try {
    const res = await http.post(`/collect/douyin/account/${row.id}/probe`)
    const label = res.data?.data?.healthLabel || res.data?.data?.notice || '已探活'
    notice.value = `测试连接：${label}`
    await loadAccounts()
  } catch (e: unknown) {
    notice.value = errorMessage(e)
    await loadAccounts()
  }
}

async function runRow(row: AccountRow) {
  notice.value = ''
  try {
    const res = await http.post(`/collect/douyin/account/${row.id}/run`)
    const data = res.data?.data || {}
    notice.value = `采集${data.statusLabel || data.status || ''}，${data.recordCount ?? 0} 条，耗时 ${data.durationMs ?? 0} ms`
    await Promise.all([loadAccounts(), loadLogs()])
  } catch (e: unknown) {
    notice.value = errorMessage(e)
    await loadLogs()
  }
}

onMounted(async () => {
  try {
    await loadOptions()
    await Promise.all([loadAccounts(), loadLogs()])
  } catch (e: unknown) {
    notice.value = errorMessage(e)
  }
})
</script>
