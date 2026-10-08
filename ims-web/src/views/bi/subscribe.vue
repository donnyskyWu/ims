<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>订阅与分享</h1>
        <div class="sub">
          BI-003 · 隐藏路由 /ims/bi/report/subscribe · go(biShare) · 钉钉 Webhook：系统参数
          <code>bi.dingtalk.webhook.url</code> 或 env <code>IMS_BI_DINGTALK_WEBHOOK_URL</code>
        </div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec btn-sm" to="/ims/bi/report/list">← 报表管理</router-link>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">订阅推送</button>
      </div>
    </div>

    <div class="tabs" style="margin-bottom: 12px">
      <div v-for="t in tabDefs" :key="t.key" class="tab" :class="{ on: tab === t.key }" @click="switchTab(t.key)">
        {{ t.label }}
      </div>
    </div>

    <div v-if="tab === 'mine'" class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>订阅</th>
              <th>周期</th>
              <th>报表</th>
              <th>推送渠道</th>
              <th>状态</th>
              <th>推送结果</th>
              <th>上次推送</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading"><td colspan="8"><div class="empty"><div class="et">加载中</div></div></td></tr>
            <tr v-for="row in subs" v-else :key="row.id">
              <td>{{ row.subName }}</td>
              <td>{{ periodLabel(row.period) }} {{ row.pushTime }}</td>
              <td>{{ row.reportName }}</td>
              <td>{{ row.channels }}</td>
              <td><span class="tag" :style="subStatusStyle(row.status)"><span class="dot"></span>{{ row.status === 'ACTIVE' ? '生效' : '暂停' }}</span></td>
              <td>
                <span class="tag" :style="pushStatusStyle(row.lastPushStatus)">{{ pushStatusLabel(row.lastPushStatus) }}</span>
              </td>
              <td>{{ row.lastPushAt }}</td>
              <td>
                <span class="btn-txt btn" @click="toggleSub(row)">{{ row.status === 'ACTIVE' ? '暂停' : '恢复' }}</span>
                <span v-if="row.status === 'ACTIVE'" class="btn-txt btn" @click="pushNow(row)">立即推送</span>
                <span class="btn-txt btn" @click="viewSnapshot(row)">查看快照</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'share'" class="tbl-block">
      <div class="hint" style="margin-bottom: 8px">
        分享不突破数据权限：链接列表按 BR-212 过滤，仅展示您有权查看的分享行
      </div>
      <div class="acts" style="margin-bottom: 8px">
        <button class="btn btn-pri btn-sm" type="button" @click="openShare">生成分享链接</button>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>报表</th>
              <th>审批</th>
              <th>过期</th>
              <th>创建人</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in shares" :key="row.id">
              <td>{{ row.targetName }}</td>
              <td>
                <span class="tag" :style="approvalStyle(row.approvalStatus)">{{ approvalLabel(row.approvalStatus) }}</span>
              </td>
              <td>{{ row.expireAt }}</td>
              <td>{{ row.creatorName }}</td>
              <td>
                <span
                  v-if="row.approvalStatus === 'APPROVED' || row.approvalStatus === 'NOT_REQUIRED'"
                  class="btn-txt btn"
                  @click="copyLink(row)"
                >复制链接</span>
                <span
                  v-if="row.approvalStatus === 'APPROVED' || row.approvalStatus === 'NOT_REQUIRED'"
                  class="btn-txt btn"
                  @click="expireShare(row)"
                >标记过期</span>
                <span v-else-if="row.approvalStatus === 'PENDING'" class="csub">待「分享审批」Tab 处理</span>
                <span v-else-if="row.approvalStatus === 'EXPIRED'" class="csub">链接已失效</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="tab === 'approve'" class="tbl-block">
      <div class="hint" style="margin-bottom: 8px">
        敏感报表（含成本/利润）分享须 R4 审批 · 通过后链接生效（BIS-R3）
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>报表</th>
              <th>创建人</th>
              <th>敏感</th>
              <th>审批</th>
              <th>过期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pendingApprovals" :key="row.id">
              <td>{{ row.targetName }}</td>
              <td>{{ row.creatorName }}</td>
              <td><span class="tag" style="background: rgba(255,59,48,.12); color: #c62828">含敏感</span></td>
              <td>
                <span class="tag" :style="approvalStyle(row.approvalStatus)">{{ approvalLabel(row.approvalStatus) }}</span>
              </td>
              <td>{{ row.expireAt }}</td>
              <td>
                <span class="btn-txt btn" @click="approveShare(row)">通过</span>
                <span class="btn-txt btn" @click="rejectShare(row)">驳回</span>
              </td>
            </tr>
            <tr v-if="!pendingApprovals.length">
              <td colspan="6"><div class="empty"><div class="et">暂无待审批分享</div></div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="tbl-block">
      <div class="hint" style="margin-bottom: 8px">发布管理仅展示按您的数据权限可见的已发布报表（BR-212）</div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>名称</th>
              <th>类型</th>
              <th>订阅数</th>
              <th>更新</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in published" :key="row.reportId">
              <td class="mono">{{ row.reportNo }}</td>
              <td>{{ row.reportName }}</td>
              <td>{{ row.reportType === 'DASHBOARD' ? '大屏' : '报表' }}</td>
              <td>{{ row.subscriptionCount }}</td>
              <td class="csub">{{ row.updatedAt }}</td>
            </tr>
            <tr v-if="!published.length"><td colspan="5"><div class="empty"><div class="et">暂无已发布报表</div></div></td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="snapshot" class="card" style="margin-top: 12px; padding: 14px">
      <b>快照 · {{ snapshot.subName }}</b>
      <p class="csub">{{ snapshot.snapshotAt }} · GMV {{ snapshot.summary?.gmv }}</p>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 400px; padding: 18px">
        <h3 style="margin: 0 0 10px">新建订阅</h3>
        <label class="fld">名称</label>
        <input v-model="form.subName" class="fld-in" />
        <label class="fld">报表 ID</label>
        <input v-model.number="form.reportId" class="fld-in" type="number" />
        <label class="fld">周期</label>
        <select v-model="form.period" class="fld-in">
          <option value="DAY">每日</option>
          <option value="WEEK">每周</option>
          <option value="MONTH">每月</option>
        </select>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitSub">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showShareForm" class="modal-mask" @click.self="showShareForm = false">
      <div class="card" style="width: 420px; padding: 18px">
        <h3 style="margin: 0 0 10px">生成分享链接</h3>
        <label class="fld">报表 ID</label>
        <input v-model.number="shareForm.reportId" class="fld-in" type="number" />
        <label class="fld">有效期（天）</label>
        <input v-model.number="shareForm.expireDays" class="fld-in" type="number" min="7" max="30" />
        <label class="fld" style="display: flex; align-items: center; gap: 8px; margin-top: 8px">
          <input v-model="shareForm.sensitive" type="checkbox" />
          含成本/利润等敏感数据（须审批）
        </label>
        <p v-if="shareForm.sensitive" class="csub" style="margin: 8px 0 0">
          提交后进入「分享审批」Tab，R4 通过前链接不可用（BIS-R3）
        </p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showShareForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitShare">生成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'

type SubRow = {
  id: number
  subName: string
  period: string
  pushTime: string
  reportName: string
  channels: string
  status: string
  lastPushStatus: string
  lastPushAt: string
}

const tabDefs = [
  { key: 'mine', label: '我的订阅' },
  { key: 'share', label: '分享链接' },
  { key: 'approve', label: '分享审批' },
  { key: 'publish', label: '发布管理' },
]
const route = useRoute()
const router = useRouter()
const tab = ref('mine')
const loading = ref(false)
const subs = ref<SubRow[]>([])
type ShareRow = {
  id: number
  targetName: string
  approvalStatus: string
  expireAt: string
  creatorName: string
  shareUrl?: string
  sensitive?: boolean
}

const shares = ref<ShareRow[]>([])
const published = ref<Record<string, unknown>[]>([])
const snapshot = ref<{ subName: string; snapshotAt: string; summary: { gmv: number } } | null>(null)
const showForm = ref(false)
const showShareForm = ref(false)
const form = reactive({ subName: '', reportId: 0, period: 'WEEK' })
const shareForm = reactive({ reportId: 0, sensitive: false, expireDays: 7 })

const pendingApprovals = computed(() => shares.value.filter((r) => r.approvalStatus === 'PENDING'))

function switchTab(key: string) {
  tab.value = key
  router.replace({ query: { ...route.query, tab: key } })
  loadTab()
}

function periodLabel(p: string) {
  return { DAY: '每日', WEEK: '每周', MONTH: '每月' }[p] || p
}

function subStatusStyle(st: string) {
  return st === 'ACTIVE'
    ? { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
    : { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}

function pushStatusLabel(st: string) {
  const s = (st || '—').trim()
  const map: Record<string, string> = {
    '—': '未推送',
    DING_OK: '钉钉成功',
    DING_FAIL: '钉钉失败',
    SITE_OK: '站内成功',
    FAILED_RETRIED: '失败已重试',
  }
  return map[s] || s
}

function pushStatusStyle(st: string) {
  const s = (st || '—').trim()
  if (s === 'DING_OK' || s === 'SITE_OK') {
    return { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
  }
  if (s === 'DING_FAIL' || s === 'FAILED_RETRIED') {
    return { background: 'rgba(255,59,48,.12)', color: '#c62828' }
  }
  return { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}

async function loadSubs() {
  loading.value = true
  try {
    const res = await http.get('/bi/subscribe/list', { params: { pageNo: 1, pageSize: 20 } })
    if (res.data.code === 0) subs.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadShares() {
  const res = await http.get('/bi/subscribe/share-link/list', { params: { pageNo: 1, pageSize: 20 } })
  if (res.data.code === 0) shares.value = res.data.data.list || []
}

async function loadPublished() {
  const res = await http.get('/bi/subscribe/publish/list', { params: { pageNo: 1, pageSize: 20 } })
  if (res.data.code === 0) published.value = res.data.data.list || []
}

function approvalLabel(st: string) {
  const map: Record<string, string> = {
    NOT_REQUIRED: '无需审批',
    PENDING: '待审批',
    APPROVED: '已通过',
    REJECTED: '已驳回',
    EXPIRED: '已过期',
  }
  return map[st] || st
}

function approvalStyle(st: string) {
  if (st === 'APPROVED' || st === 'NOT_REQUIRED') {
    return { background: 'rgba(52,199,89,.12)', color: '#1e8e3e' }
  }
  if (st === 'PENDING') {
    return { background: 'rgba(255,149,0,.12)', color: '#e65100' }
  }
  if (st === 'REJECTED') {
    return { background: 'rgba(255,59,48,.12)', color: '#c62828' }
  }
  if (st === 'EXPIRED') {
    return { background: 'rgba(142,142,147,.18)', color: '#48484a' }
  }
  return { background: 'rgba(142,142,147,.12)', color: '#6d6d72' }
}

function loadTab() {
  if (tab.value === 'mine') loadSubs()
  else if (tab.value === 'share' || tab.value === 'approve') loadShares()
  else loadPublished()
}

function openCreate() {
  showForm.value = true
}

async function submitSub() {
  const res = await http.post('/bi/subscribe', form)
  if (res.data.code === 0) {
    showForm.value = false
    await loadSubs()
  }
}

async function toggleSub(row: SubRow) {
  const status = row.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE'
  await http.put(`/bi/subscribe/${row.id}`, { status })
  await loadSubs()
}

async function viewSnapshot(row: SubRow) {
  const res = await http.get(`/bi/subscribe/snapshot/${row.id}`)
  if (res.data.code === 0) snapshot.value = res.data.data
}

async function pushNow(row: SubRow) {
  const res = await http.post(`/bi/subscribe/${row.id}/push-now`)
  if (res.data.code !== 0) {
    alert(res.data.msg || '推送失败')
    return
  }
  snapshot.value = res.data.data.snapshot
  await loadSubs()
}

function openShare() {
  shareForm.reportId = Number(form.reportId) || shareForm.reportId || 0
  shareForm.sensitive = false
  shareForm.expireDays = 7
  showShareForm.value = true
}

async function submitShare() {
  const reportId = Number(shareForm.reportId)
  if (!reportId) {
    alert('请填写报表 ID')
    return
  }
  const res = await http.post('/bi/subscribe/share-link', {
    reportId,
    sensitive: shareForm.sensitive,
    expireDays: shareForm.expireDays,
  })
  if (res.data.code !== 0) {
    alert(res.data.msg || '生成失败')
    return
  }
  showShareForm.value = false
  await loadShares()
  if (res.data.data?.approvalStatus === 'PENDING') {
    tab.value = 'approve'
    router.replace({ query: { ...route.query, tab: 'approve' } })
  }
}

async function copyLink(row: { shareUrl?: string }) {
  if (row.shareUrl) await navigator.clipboard.writeText(window.location.origin + row.shareUrl)
}

async function approveShare(row: ShareRow) {
  const res = await http.put(`/bi/subscribe/share-approval/${row.id}`, { approvalStatus: 'APPROVED' })
  if (res.data.code !== 0) {
    alert(res.data.msg || '审批失败')
    return
  }
  await loadShares()
}

async function rejectShare(row: ShareRow) {
  const res = await http.put(`/bi/subscribe/share-approval/${row.id}`, { approvalStatus: 'REJECTED' })
  if (res.data.code !== 0) {
    alert(res.data.msg || '驳回失败')
    return
  }
  await loadShares()
}

async function expireShare(row: ShareRow) {
  const res = await http.put(`/bi/subscribe/share-approval/${row.id}`, { approvalStatus: 'EXPIRED' })
  if (res.data.code !== 0) {
    alert(res.data.msg || '标记失败')
    return
  }
  await loadShares()
}

onMounted(() => {
  const q = String(route.query.tab || 'mine')
  if (tabDefs.some((t) => t.key === q)) tab.value = q
  loadTab()
})
</script>
