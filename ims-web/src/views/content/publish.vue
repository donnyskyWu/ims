<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>发布管理</h1>
        <div class="sub">CONTENT-006 · 发布单 / 回填 / 督办（PUB-R2）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新建发布单</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/content/list">内容管理</router-link>
      </div>
    </div>
    <div class="hint" data-testid="publish-supervise" style="margin-bottom: 10px">
      督办：待发布 {{ pendingCount }}
      <span
        v-if="overdueCount > 0"
        data-testid="publish-overdue-count"
        style="margin-left: 12px; color: var(--red); font-weight: 600"
      >超计划 24h {{ overdueCount }}</span>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.publishNo" placeholder="发布单号" style="width: 140px" />
      <select v-model="filters.publishStatus" style="width: 130px">
        <option value="">全部状态</option>
        <option value="PENDING_PUBLISH">待发布</option>
        <option value="ARCHIVED">已归档</option>
        <option value="PUBLISH_FAILED">发布失败</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>发布单号</th>
              <th>平台</th>
              <th>账号</th>
              <th>计划时间</th>
              <th>状态</th>
              <th>链接回执</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无发布单' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.publishNo }}</td>
              <td>{{ row.platform }}</td>
              <td class="mono">{{ row.accountNo }}</td>
              <td class="num" style="font-size: 12px">{{ row.planPublishAt }}</td>
              <td><span class="chip">{{ statusLabel(row.publishStatus) }}</span></td>
              <td>
                <a v-if="row.publishUrl" :href="row.publishUrl" target="_blank" rel="noopener">已回填</a>
                <span
                  v-else
                  data-testid="publish-receipt-pending"
                  :style="receiptOverdue(row) ? 'color: var(--red); font-weight: 600' : 'color: var(--orange)'"
                >{{ receiptOverdue(row) ? '待回填 · 超 24h' : '待回填' }}</span>
              </td>
              <td>
                <button
                  v-if="row.publishStatus === 'PENDING_PUBLISH'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  @click="openReceipt(row)"
                >
                  回填
                </button>
                <button
                  v-if="row.publishStatus === 'ARCHIVED'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="openArchive(row)"
                >
                  归档
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="createOpen" title="新建发布单" width="520px" @close="createOpen = false">
      <p class="hint">内容须终审通过 · 计划时间早于当前 24h 将触发督办 hint</p>
      <div class="formrow one">
        <div class="fld">
          <label>内容项目 id *</label>
          <input v-model.number="createForm.contentProjectId" type="number" min="1" />
        </div>
        <div class="fld">
          <label>平台账号 id *</label>
          <input v-model.number="createForm.accountId" type="number" min="1" />
        </div>
        <div class="fld">
          <label>平台 *</label>
          <input v-model="createForm.platform" placeholder="DOUYIN" />
        </div>
        <div class="fld">
          <label>计划发布时间 *</label>
          <input v-model="createForm.planPublishAt" placeholder="2026-10-08T20:00:00+08:00" />
        </div>
        <div class="fld">
          <label>文案</label>
          <input v-model="createForm.caption" maxlength="512" />
        </div>
      </div>
      <template #footer>
        <button class="btn btn-sec btn-sm" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri btn-sm" type="button" :disabled="creating" @click="submitCreate">保存</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="receiptOpen" title="回填发布链接" width="480px" @close="receiptOpen = false">
      <p class="hint">回填后自动归档打包（PUB-R3）</p>
      <label class="rowline" style="flex-direction: column; align-items: stretch; gap: 4px">
        发布链接
        <input v-model="receiptForm.publishUrl" placeholder="https://..." />
      </label>
      <label class="rowline" style="flex-direction: column; align-items: stretch; gap: 4px; margin-top: 8px">
        发布时间
        <input v-model="receiptForm.publishedAt" placeholder="2026-10-08T20:00:00+08:00" />
      </label>
      <div class="rowline" style="margin-top: 16px; justify-content: flex-end; gap: 8px">
        <button class="btn btn-sec btn-sm" type="button" @click="receiptOpen = false">取消</button>
        <button class="btn btn-pri btn-sm" type="button" @click="submitReceipt">保存</button>
      </div>
    </ProtoDrawer>

    <ProtoDrawer :open="archiveOpen" :title="`归档 · ${archive?.archiveNo || ''}`" width="560px" @close="archiveOpen = false">
      <p v-if="archive" class="hint">打包路径：{{ archive.packageUrl || '—' }}</p>
      <ul v-if="archive?.fileList?.length">
        <li v-for="f in archive.fileList" :key="f.fileKey">{{ f.fileType }} · {{ f.fileName }}</li>
      </ul>
      <p v-else class="empty"><div class="et">无文件清单</div></p>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { http } from '../../api/http'

const loading = ref(false)
const error = ref('')
const rows = ref<any[]>([])
const total = ref(0)
const pendingCount = ref(0)
const overdueCount = ref(0)
const filters = reactive({ publishNo: '', publishStatus: '' })

const createOpen = ref(false)
const creating = ref(false)
const createForm = reactive({
  contentProjectId: 0,
  accountId: 0,
  platform: 'DOUYIN',
  planPublishAt: '',
  caption: '',
})

const receiptOpen = ref(false)
const receiptTarget = ref<any>(null)
const receiptForm = reactive({ publishUrl: '', publishedAt: '' })

const archiveOpen = ref(false)
const archive = ref<any>(null)

function statusLabel(s: string) {
  const map: Record<string, string> = {
    PENDING_PUBLISH: '待发布',
    ARCHIVED: '已归档',
    PUBLISH_FAILED: '发布失败',
  }
  return map[s] || s
}

function receiptOverdue(row: { planPublishAt?: string; publishStatus?: string; publishUrl?: string }) {
  if (row.publishUrl) return false
  if (row.publishStatus !== 'PENDING_PUBLISH' && row.publishStatus !== 'PUBLISH_FAILED') return false
  return overdueHours(row.planPublishAt || '') >= 24
}

function overdueHours(planPublishAt: string) {
  const raw = planPublishAt.trim()
  if (!raw) return 0
  const text = raw.replace(/Z$/i, '+00:00')
  const hasZone = /[+-]\d{2}:\d{2}$/.test(text)
  const parsed = new Date(hasZone ? text : `${text}+08:00`)
  if (Number.isNaN(parsed.getTime())) return 0
  return Math.max(0, (Date.now() - parsed.getTime()) / 3600000)
}

async function pendingTotal(overdueOnly: boolean) {
  const params: Record<string, string | number | boolean> = { pageNo: 1, pageSize: 1 }
  if (overdueOnly) params.overdueOnly = true
  const { data } = await http.get('/content/publish/pending', { params })
  if (data.code !== 0) return 0
  return Number(data.data?.total || 0)
}

async function loadPendingHint() {
  try {
    const [pending, overdue] = await Promise.all([pendingTotal(false), pendingTotal(true)])
    pendingCount.value = pending
    overdueCount.value = overdue
  } catch {
    /* 督办条失败不挡列表 */
  }
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 50 }
    if (filters.publishStatus) params.publishStatus = filters.publishStatus
    const { data } = await http.get('/content/publish/list', { params })
    if (data.code !== 0) {
      error.value = data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    let list = data.data?.list || []
    if (filters.publishNo.trim()) {
      const kw = filters.publishNo.trim()
      list = list.filter((r: any) => String(r.publishNo || '').includes(kw))
    }
    rows.value = list
    total.value = filters.publishNo.trim() ? list.length : data.data?.total || list.length
  } catch (e: any) {
    error.value = e?.message || '网络错误'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.contentProjectId = 0
  createForm.accountId = 0
  createForm.platform = 'DOUYIN'
  createForm.planPublishAt = ''
  createForm.caption = ''
  createOpen.value = true
}

async function submitCreate() {
  if (!createForm.contentProjectId || !createForm.accountId || !createForm.platform.trim() || !createForm.planPublishAt.trim()) {
    alert('请填写必填项')
    return
  }
  creating.value = true
  try {
    const res = await http.post('/content/publish', {
      contentProjectId: createForm.contentProjectId,
      accountId: createForm.accountId,
      platform: createForm.platform.trim(),
      planPublishAt: createForm.planPublishAt.trim(),
      caption: createForm.caption.trim(),
    })
    if (res.data.code !== 0) {
      alert(res.data.msg || '创建失败')
      return
    }
    createOpen.value = false
    await loadList()
    await loadPendingHint()
  } catch (e: any) {
    alert(e?.message || '网络错误')
  } finally {
    creating.value = false
  }
}

function openReceipt(row: any) {
  receiptTarget.value = row
  receiptForm.publishUrl = row.publishUrl || ''
  receiptForm.publishedAt = new Date().toISOString().slice(0, 19) + '+08:00'
  receiptOpen.value = true
}

async function submitReceipt() {
  const id = receiptTarget.value?.id
  if (!id) return
  const res = await http.put(`/content/publish/${id}/receipt`, {
    publishUrl: receiptForm.publishUrl,
    publishedAt: receiptForm.publishedAt,
  })
  if (res.data.code !== 0) {
    alert(res.data.msg || '回填失败')
    return
  }
  receiptOpen.value = false
  await loadList()
  await loadPendingHint()
}

async function openArchive(row: any) {
  const res = await http.get(`/content/publish/${row.id}/archive`)
  if (res.data.code !== 0) {
    alert(res.data.msg || '加载归档失败')
    return
  }
  archive.value = res.data.data
  archiveOpen.value = true
}

onMounted(() => {
  loadPendingHint()
  loadList()
})
</script>
