<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>选题计划</h1>
        <div class="sub">选题库：筛选、详情、待评审编辑、落选复活（CONTENT-002）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" data-testid="topic-create-open" @click="openCreate">提报选题</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="topicNo" placeholder="选题编号" style="width: 150px" data-testid="topic-filter-no" />
      <input v-model="keyword" placeholder="标题关键词" style="width: 160px" data-testid="topic-filter-keyword" />
      <select v-model="sourceFilter" style="width: 120px" data-testid="topic-filter-source">
        <option value="">全部来源</option>
        <option v-for="item in sourceOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="statusFilter" style="width: 130px" data-testid="topic-filter-status">
        <option value="">全部状态</option>
        <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="submitterFilter" style="width: 160px" data-testid="topic-filter-submitter">
        <option value="">全部提报人</option>
        <option v-for="user in submitters" :key="user.id" :value="user.id">{{ user.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="topic-filter-search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="topic-filter-reset" @click="resetFilters">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>选题编号</th>
              <th>标题</th>
              <th>来源</th>
              <th>提报人</th>
              <th>计划发布日</th>
              <th>挂接 SOP</th>
              <th>状态</th>
              <th>评审意见</th>
              <th>出任务</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="10"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="10">
                <div class="empty"><div class="et">{{ error || '暂无选题' }}</div></div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.topicNo }}</td>
              <td><b>{{ row.title }}</b></td>
              <td>{{ sourceLabel(row.sourceType) }}</td>
              <td>{{ row.submitterName || '—' }}</td>
              <td>{{ row.planPublishDate || '—' }}</td>
              <td>{{ row.sopName || '—' }}</td>
              <td data-testid="topic-status">{{ statusLabel(row.topicStatus) }}</td>
              <td data-testid="topic-opinion-cell">{{ row.reviewOpinion || '—' }}</td>
              <td data-testid="topic-task-gate">{{ row.canCreateTask ? '可出任务' : '未立项不可出任务' }}</td>
              <td>
                <div class="row-acts">
                  <button class="btn btn-sec btn-sm" type="button" data-testid="topic-detail" @click="openDetail(row)">详情</button>
                  <button
                    v-if="row.topicStatus === 'PENDING_REVIEW'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="topic-edit"
                    @click="openEdit(row)"
                  >
                    编辑
                  </button>
                  <button
                    v-if="row.topicStatus === 'PENDING_REVIEW'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    @click="openReview(row)"
                  >
                    评审
                  </button>
                  <button
                    v-if="row.topicStatus === 'PENDING_REVIEW'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="topic-cancel"
                    @click="openCancel(row)"
                  >
                    取消
                  </button>
                  <button
                    v-if="row.topicStatus === 'REJECTED'"
                    class="btn btn-sec btn-sm"
                    type="button"
                    data-testid="topic-revive"
                    @click="openRevive(row)"
                  >
                    复活
                  </button>
                  <span v-else-if="row.contentProjectId" class="hint">内容项目 #{{ row.contentProjectId }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <ProtoDrawer :open="createOpen" :title="editorMode === 'edit' ? '编辑选题' : '提报选题'" width="600px" @close="createOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input v-model="form.title" maxlength="256" data-testid="topic-title" />
        </div>
        <div class="fld">
          <label>内容要求 *</label>
          <textarea v-model="form.description" maxlength="2000" rows="4" data-testid="topic-description" />
        </div>
        <div class="fld">
          <label>来源类型 *</label>
          <select v-model="form.sourceType" data-testid="topic-source">
            <option v-for="item in sourceOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <template v-if="editorMode === 'edit'">
          <div class="fld">
            <label>计划发布日</label>
            <input v-model="form.planPublishDate" type="date" data-testid="topic-edit-plan-date" />
          </div>
          <div class="fld">
            <label>建议 SOP</label>
            <select v-model="form.sopId" data-testid="topic-edit-sop">
              <option value="">不挂接</option>
              <option v-for="sop in sops" :key="sop.id" :value="String(sop.id)">{{ sop.sopName }}</option>
            </select>
          </div>
        </template>
      </div>
      <p v-if="createError" class="hint bad">{{ createError }}</p>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="createOpen = false">取消</button>
        <button class="btn btn-pri" type="button" data-testid="topic-submit" :disabled="saving" @click="saveTopic">提交</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="reviewOpen" title="评审立项" width="640px" @close="reviewOpen = false">
      <div v-if="reviewRow" class="formrow one">
        <div class="fld">
          <label>标题</label>
          <div>{{ reviewRow.title }}</div>
        </div>
        <div class="fld">
          <label>内容要求</label>
          <div data-testid="topic-review-requirement">{{ reviewRow.description }}</div>
        </div>
        <div class="fld">
          <label>挂接 SOP *</label>
          <select v-model="reviewForm.sopId" data-testid="topic-sop">
            <option value="">请选择 SOP</option>
            <option v-for="sop in sops" :key="sop.id" :value="String(sop.id)">{{ sop.sopName }}</option>
          </select>
        </div>
        <div class="fld">
          <label>计划发布日 *</label>
          <input v-model="reviewForm.planPublishDate" type="date" data-testid="topic-plan-date" />
        </div>
        <div class="fld">
          <label>评审意见</label>
          <textarea v-model="reviewForm.reviewOpinion" maxlength="512" rows="3" data-testid="topic-opinion" placeholder="落选时必填" />
        </div>
      </div>
      <p v-if="reviewError" class="hint bad" data-testid="topic-review-error">{{ reviewError }}</p>
      <template #footer>
        <button class="btn btn-sec" type="button" :disabled="reviewing" @click="submitReview('REJECT')">落选</button>
        <button class="btn btn-pri" type="button" data-testid="topic-approve" :disabled="reviewing" @click="submitReview('APPROVE_PROJECT')">立项</button>
      </template>
    </ProtoDrawer>

    <ProtoDrawer :open="detailOpen" title="选题详情" width="560px" @close="detailOpen = false">
      <div v-if="detailRow" class="formrow one" data-testid="topic-detail-drawer">
        <div class="fld">
          <label>选题编号</label>
          <div class="mono">{{ detailRow.topicNo }}</div>
        </div>
        <div class="fld">
          <label>标题</label>
          <div data-testid="topic-detail-title">{{ detailRow.title }}</div>
        </div>
        <div class="fld">
          <label>内容要求</label>
          <div data-testid="topic-detail-requirement">{{ detailRow.description || '—' }}</div>
        </div>
        <div class="fld">
          <label>来源 / 提报人</label>
          <div>{{ sourceLabel(detailRow.sourceType) }} · {{ detailRow.submitterName || '—' }}</div>
        </div>
        <div class="fld">
          <label>状态</label>
          <div data-testid="topic-detail-status">{{ statusLabel(detailRow.topicStatus) }}</div>
        </div>
        <div class="fld">
          <label>计划发布日 / SOP</label>
          <div>{{ detailRow.planPublishDate || '—' }} · {{ detailRow.sopName || '—' }}</div>
        </div>
        <div class="fld">
          <label>评审意见</label>
          <div data-testid="topic-detail-opinion">{{ detailRow.reviewOpinion || '—' }}</div>
        </div>
        <div class="fld">
          <label>关联内容项目</label>
          <div v-if="detailRow.contentProjectId" data-testid="topic-detail-project">
            内容项目 #{{ detailRow.contentProjectId }} · {{ projectStatusLabel(detailRow.contentProjectStatus) }}
            <div class="chain" data-testid="topic-detail-chain">
              <span
                v-for="step in detailRow.contentStatusChain"
                :key="step.status"
                :class="{ on: step.current }"
                :data-current="step.current ? '1' : '0'"
              >{{ step.label }}</span>
            </div>
          </div>
          <div v-else data-testid="topic-detail-project">尚未立项，无内容项目</div>
        </div>
      </div>
    </ProtoDrawer>

    <div v-if="reviveRow" class="modal-mask" data-testid="topic-revive-modal">
      <div class="modal-card">
        <h3>复活确认</h3>
        <p>将「{{ reviveRow.title }}」复活回待评审。落选意见保留在详情中。</p>
        <p v-if="reviveError" class="hint bad">{{ reviveError }}</p>
        <div class="modal-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="reviveRow = null">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="topic-revive-confirm" :disabled="reviving" @click="confirmRevive">确认复活</button>
        </div>
      </div>
    </div>

    <div v-if="cancelRow" class="modal-mask" data-testid="topic-cancel-modal">
      <div class="modal-card">
        <h3>取消选题</h3>
        <p>取消后进入已取消，不可出任务。</p>
        <textarea v-model="cancelOpinion" maxlength="512" rows="3" placeholder="取消原因 *" data-testid="topic-cancel-opinion" />
        <p v-if="cancelError" class="hint bad">{{ cancelError }}</p>
        <div class="modal-acts">
          <button class="btn btn-sec btn-sm" type="button" @click="cancelRow = null">关闭</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="topic-cancel-confirm" :disabled="cancelling" @click="confirmCancel">确认取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type ChainStep = { status: string; label: string; current: boolean }

type TopicRow = {
  id: number
  topicNo: string
  title: string
  description: string
  sourceType: string
  submitterName: string
  planPublishDate: string
  topicStatus: string
  sopId: number | null
  sopName: string
  reviewOpinion: string
  contentProjectId: number | null
  contentProjectStatus: string
  contentStatusChain: ChainStep[]
  canCreateTask: boolean
}

const STATUS_LABEL: Record<string, string> = {
  PENDING_REVIEW: '待评审',
  APPROVED_PROJECT: '已立项',
  REJECTED: '落选',
  CANCELLED: '已取消',
}
const SOURCE_LABEL: Record<string, string> = {
  HOTSPOT: '热点',
  TALENT: '达人',
  BRAND: '品牌',
  ORIGINAL: '自主',
}
const PROJECT_LABEL: Record<string, string> = {
  DRAFT: '草稿',
  IN_PROGRESS: '制作中',
  PENDING_REVIEW: '待审核',
  APPROVED: '已通过',
  PUBLISHED: '已发布',
  ARCHIVED: '已归档',
}

const statusOptions = Object.entries(STATUS_LABEL).map(([value, label]) => ({ value, label }))
const sourceOptions = Object.entries(SOURCE_LABEL).map(([value, label]) => ({ value, label }))

const rows = ref<TopicRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const topicNo = ref('')
const keyword = ref('')
const sourceFilter = ref('')
const statusFilter = ref('')
const submitterFilter = ref('')
const submitters = ref<{ id: string; label: string }[]>([])
const createOpen = ref(false)
const editorMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const saving = ref(false)
const createError = ref('')
const form = ref({ title: '', description: '', sourceType: 'ORIGINAL', planPublishDate: '', sopId: '' })
const reviewOpen = ref(false)
const reviewing = ref(false)
const reviewError = ref('')
const reviewRow = ref<TopicRow | null>(null)
const reviewForm = ref({ sopId: '', planPublishDate: '', reviewOpinion: '' })
const sops = ref<{ id: number; sopName: string }[]>([])
const detailOpen = ref(false)
const detailRow = ref<TopicRow | null>(null)
const reviveRow = ref<TopicRow | null>(null)
const reviveError = ref('')
const reviving = ref(false)
const cancelRow = ref<TopicRow | null>(null)
const cancelOpinion = ref('')
const cancelError = ref('')
const cancelling = ref(false)

function statusLabel(status: string) {
  return STATUS_LABEL[status] || status
}

function sourceLabel(source: string) {
  return SOURCE_LABEL[source] || source
}

function projectStatusLabel(status: string) {
  return PROJECT_LABEL[status] || status || '—'
}

function formatBiz(err: unknown) {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { code?: number; msg?: string } | undefined
    if (data?.code) return `${data.code} ${data.msg || '操作失败'}`
  }
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number | string; msg?: string }
    if (typeof body.code === 'number' && body.code) return `${body.code} ${body.msg || '操作失败'}`
  }
  return errorMessage(err)
}

async function loadSubmitters() {
  try {
    const { data } = await http.get('/system/user/page', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    const list = (data.data.list || []) as { id: string | number; username: string; nickname?: string }[]
    submitters.value = list.map((user) => ({
      id: String(user.id),
      label: user.nickname ? `${user.nickname}（${user.username}）` : user.username,
    }))
  } catch {
    submitters.value = []
  }
}

async function loadSops() {
  const { data } = await http.get('/content/sop/list', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
  sops.value = data.data.list
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/topic/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        topicNo: topicNo.value.trim() || undefined,
        keyword: keyword.value.trim() || undefined,
        sourceType: sourceFilter.value || undefined,
        topicStatus: statusFilter.value || undefined,
        submitterUserId: submitterFilter.value ? Number(submitterFilter.value) : undefined,
      },
    })
    rows.value = data.data.list
    total.value = data.data.total
  } catch (e) {
    error.value = formatBiz(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  topicNo.value = ''
  keyword.value = ''
  sourceFilter.value = ''
  statusFilter.value = ''
  submitterFilter.value = ''
  loadList()
}

function openCreate() {
  editorMode.value = 'create'
  editingId.value = null
  form.value = { title: '', description: '', sourceType: 'ORIGINAL', planPublishDate: '', sopId: '' }
  createError.value = ''
  createOpen.value = true
}

async function openEdit(row: TopicRow) {
  editorMode.value = 'edit'
  editingId.value = row.id
  form.value = {
    title: row.title,
    description: row.description,
    sourceType: row.sourceType,
    planPublishDate: row.planPublishDate || '',
    sopId: row.sopId ? String(row.sopId) : '',
  }
  createError.value = ''
  createOpen.value = true
  try {
    await loadSops()
  } catch (e) {
    sops.value = []
    createError.value = formatBiz(e)
  }
}

async function saveTopic() {
  saving.value = true
  createError.value = ''
  const payload = {
    title: form.value.title,
    description: form.value.description,
    sourceType: form.value.sourceType,
    planPublishDate: form.value.planPublishDate || undefined,
    sopId: form.value.sopId ? Number(form.value.sopId) : undefined,
  }
  try {
    if (editorMode.value === 'edit' && editingId.value) {
      await http.put(`/content/topic/${editingId.value}`, payload)
    } else {
      await http.post('/content/topic', {
        title: payload.title,
        description: payload.description,
        sourceType: payload.sourceType,
      })
    }
    createOpen.value = false
    await loadList()
  } catch (e) {
    createError.value = formatBiz(e)
  } finally {
    saving.value = false
  }
}

async function openReview(row: TopicRow) {
  reviewRow.value = row
  reviewForm.value = { sopId: '', planPublishDate: '', reviewOpinion: '' }
  reviewError.value = ''
  reviewOpen.value = true
  try {
    await loadSops()
  } catch (e) {
    sops.value = []
    reviewError.value = formatBiz(e)
  }
}

async function submitReview(action: 'APPROVE_PROJECT' | 'REJECT') {
  if (!reviewRow.value) return
  reviewing.value = true
  reviewError.value = ''
  try {
    await http.put(`/content/topic/${reviewRow.value.id}/review`, {
      action,
      planPublishDate: reviewForm.value.planPublishDate || undefined,
      sopId: reviewForm.value.sopId ? Number(reviewForm.value.sopId) : undefined,
      reviewOpinion: reviewForm.value.reviewOpinion || undefined,
    })
    reviewOpen.value = false
    await loadList()
  } catch (e) {
    reviewError.value = formatBiz(e)
  } finally {
    reviewing.value = false
  }
}

function openDetail(row: TopicRow) {
  detailRow.value = row
  detailOpen.value = true
}

function openRevive(row: TopicRow) {
  reviveRow.value = row
  reviveError.value = ''
}

async function confirmRevive() {
  if (!reviveRow.value) return
  reviving.value = true
  reviveError.value = ''
  try {
    await http.put(`/content/topic/${reviveRow.value.id}/review`, { action: 'REVIVE' })
    reviveRow.value = null
    await loadList()
  } catch (e) {
    reviveError.value = formatBiz(e)
  } finally {
    reviving.value = false
  }
}

function openCancel(row: TopicRow) {
  cancelRow.value = row
  cancelOpinion.value = ''
  cancelError.value = ''
}

async function confirmCancel() {
  if (!cancelRow.value) return
  cancelling.value = true
  cancelError.value = ''
  try {
    await http.put(`/content/topic/${cancelRow.value.id}/review`, {
      action: 'CANCEL',
      reviewOpinion: cancelOpinion.value,
    })
    cancelRow.value = null
    await loadList()
  } catch (e) {
    cancelError.value = formatBiz(e)
  } finally {
    cancelling.value = false
  }
}

onMounted(() => {
  loadSubmitters()
  loadList()
})
</script>

<style scoped>
.row-acts { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.chain { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.chain span { padding: 2px 8px; border-radius: 6px; background: #f4f5f7; color: #666; font-size: 12px; }
.chain span.on { background: #e8f1ff; color: #0b57d0; font-weight: 600; }
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
}
.modal-card { width: 360px; max-width: 92vw; background: #fff; border-radius: 12px; padding: 16px 18px; }
.modal-card h3 { margin: 0 0 8px; }
.modal-card p { margin: 0 0 10px; font-size: 13px; line-height: 1.5; }
.modal-card textarea { width: 100%; margin-bottom: 8px; }
.modal-acts { display: flex; justify-content: flex-end; gap: 8px; }
</style>
