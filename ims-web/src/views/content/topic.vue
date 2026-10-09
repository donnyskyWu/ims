<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>选题计划</h1>
        <div class="sub">选题提报、状态空态与立项（CONTENT-002 · TOP-R1）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" data-testid="topic-create-open" @click="openCreate">提报选题</button>
      </div>
    </div>
    <div class="tabs" data-testid="topic-view-switch">
      <div class="tab" :class="{ on: view === 'list' }" data-testid="topic-view-list" @click="showList">列表</div>
      <div class="tab" :class="{ on: view === 'board' }" data-testid="topic-view-board" @click="showBoard">状态看板</div>
    </div>
    <form v-if="view === 'list'" class="qbar" @submit.prevent="loadList">
      <input v-model="keyword" placeholder="标题关键词" style="width: 180px" data-testid="topic-filter-keyword" />
      <select v-model="statusFilter" style="width: 140px" data-testid="topic-filter-status">
        <option value="">全部状态</option>
        <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="topic-filter-search">查询</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="topic-filter-reset" @click="resetFilters">重置</button>
    </form>
    <div v-if="view === 'list'" class="tbl-block">
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
              <th>出任务</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="9">
                <div class="empty" data-testid="topic-list-empty" :data-status="statusFilter || 'ALL'">
                  <div class="et">{{ listEmptyTitle }}</div>
                  <div class="es">{{ listEmptyHint }}</div>
                </div>
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
              <td data-testid="topic-task-gate">{{ row.canCreateTask ? '可出任务' : '未立项不可出任务' }}</td>
              <td>
                <button
                  v-if="row.topicStatus === 'PENDING_REVIEW'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="openReview(row)"
                >
                  评审
                </button>
                <span v-else-if="row.contentProjectId" class="hint">内容项目 #{{ row.contentProjectId }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>

    <div v-else class="topic-board" data-testid="topic-status-board">
      <section
        v-for="item in statusOptions"
        :key="item.value"
        class="topic-col"
        :data-testid="`topic-status-col-${item.value}`"
      >
        <header>
          <b>{{ item.label }}</b>
          <span class="count" :data-testid="`topic-status-count-${item.value}`">{{ boardCol(item.value).total }}</span>
        </header>
        <div v-if="boardCol(item.value).loading" class="empty"><div class="et">加载中</div></div>
        <div
          v-else-if="boardCol(item.value).error"
          class="empty"
          :data-testid="`topic-status-empty-${item.value}`"
          :data-status="item.value"
        >
          <div class="et">{{ boardCol(item.value).error }}</div>
          <div class="es">这一列加载失败，可重新打开状态看板</div>
        </div>
        <div
          v-else-if="!boardCol(item.value).rows.length"
          class="empty"
          :data-testid="`topic-status-empty-${item.value}`"
          :data-status="item.value"
        >
          <div class="et">暂无{{ item.label }}选题</div>
          <div class="es">{{ item.emptyHint }}</div>
        </div>
        <article
          v-for="row in boardCol(item.value).rows"
          v-else
          :key="row.id"
          class="topic-card"
          data-testid="topic-board-card"
          :data-status="item.value"
        >
          <b>{{ row.title }}</b>
          <div class="mono">{{ row.topicNo }}</div>
          <div class="meta">{{ row.planPublishDate || '未排期' }}<span v-if="row.sopName"> · {{ row.sopName }}</span></div>
          <button
            v-if="row.topicStatus === 'PENDING_REVIEW'"
            class="btn btn-sec btn-sm"
            type="button"
            @click="openReview(row)"
          >
            评审
          </button>
        </article>
      </section>
    </div>

    <ProtoDrawer :open="createOpen" title="提报选题" width="600px" @close="createOpen = false">
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
            <option value="HOTSPOT">热点</option>
            <option value="TALENT">达人</option>
            <option value="BRAND">品牌</option>
            <option value="ORIGINAL">自主</option>
          </select>
        </div>
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
        <div class="fld" :class="{ err: sopError }">
          <label>挂接 SOP *</label>
          <select v-model="reviewForm.sopId" data-testid="topic-sop" :class="{ err: sopError }" @change="clearSopError">
            <option value="">请选择 SOP</option>
            <option v-for="sop in sops" :key="sop.id" :value="String(sop.id)">{{ sop.sopName }}</option>
          </select>
          <p v-if="sopError" class="ferr" data-testid="topic-sop-error">{{ sopError }}</p>
        </div>
        <div class="fld">
          <label>计划发布日 *</label>
          <input
            v-model="reviewForm.planPublishDate"
            type="date"
            data-testid="topic-plan-date"
            :class="{ err: planDateError }"
            @input="clearPlanDateError"
          />
          <p v-if="planDateError" class="ferr" data-testid="topic-plan-date-error">{{ planDateError }}</p>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'

type TopicRow = {
  id: number
  topicNo: string
  title: string
  description: string
  sourceType: string
  submitterName: string
  planPublishDate: string
  topicStatus: string
  sopName: string
  contentProjectId: number | null
  canCreateTask: boolean
}

type BoardCol = {
  rows: TopicRow[]
  total: number
  loading: boolean
  error: string
}

const STATUS_OPTIONS = [
  { value: 'PENDING_REVIEW', label: '待评审', emptyHint: '提报后会出现在这一列' },
  { value: 'APPROVED_PROJECT', label: '已立项', emptyHint: '评审立项并通过后会出现在这一列' },
  { value: 'REJECTED', label: '落选', emptyHint: '落选归档后会出现在这一列' },
  { value: 'CANCELLED', label: '已取消', emptyHint: '取消后的选题会出现在这一列' },
] as const

const STATUS_LABEL: Record<string, string> = Object.fromEntries(STATUS_OPTIONS.map((item) => [item.value, item.label]))
const SOURCE_LABEL: Record<string, string> = {
  HOTSPOT: '热点',
  TALENT: '达人',
  BRAND: '品牌',
  ORIGINAL: '自主',
}

const statusOptions = STATUS_OPTIONS
const view = ref<'list' | 'board'>('list')
const rows = ref<TopicRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const statusFilter = ref('')
const board = ref<Record<string, BoardCol>>({})
const createOpen = ref(false)
const saving = ref(false)
const createError = ref('')
const form = ref({ title: '', description: '', sourceType: 'ORIGINAL' })
const reviewOpen = ref(false)
const reviewing = ref(false)
const reviewError = ref('')
const sopError = ref('')
const planDateError = ref('')
const reviewRow = ref<TopicRow | null>(null)
const reviewForm = ref({ sopId: '', planPublishDate: '', reviewOpinion: '' })
const sops = ref<{ id: number; sopName: string }[]>([])

const listEmptyTitle = computed(() => {
  if (error.value) return error.value
  const status = STATUS_LABEL[statusFilter.value]
  const text = keyword.value.trim()
  if (status && text) return `暂无符合条件的${status}选题`
  if (status) return `暂无${status}选题`
  if (text) return '没有符合关键词的选题'
  return '暂无选题'
})

const listEmptyHint = computed(() => {
  if (error.value) return '请稍后重试'
  if (statusFilter.value || keyword.value.trim()) return '调整筛选条件，或重置后查看全部选题'
  return '点击「提报选题」后进入待评审'
})

function statusLabel(status: string) {
  return STATUS_LABEL[status] || status
}

function sourceLabel(source: string) {
  return SOURCE_LABEL[source] || source
}

function boardCol(status: string): BoardCol {
  return board.value[status] || { rows: [], total: 0, loading: true, error: '' }
}

function formatBiz(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    if (body.code) return `${body.code} ${body.msg || '操作失败'}`
  }
  return errorMessage(err)
}

function bizCode(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const code = (err as { code?: number }).code
    return typeof code === 'number' ? code : 0
  }
  return 0
}

function clearApproveFieldErrors() {
  sopError.value = ''
  planDateError.value = ''
}

function markMissingApproveFields() {
  sopError.value = reviewForm.value.sopId ? '' : '请选择挂接 SOP'
  planDateError.value = reviewForm.value.planPublishDate ? '' : '请填写计划发布日'
}

function clearSopError() {
  if (reviewForm.value.sopId) sopError.value = ''
}

function clearPlanDateError() {
  if (reviewForm.value.planPublishDate) planDateError.value = ''
}

watch(() => reviewForm.value.sopId, (value) => {
  if (value) sopError.value = ''
})

watch(() => reviewForm.value.planPublishDate, (value) => {
  if (value) planDateError.value = ''
})

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/topic/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        keyword: keyword.value.trim() || undefined,
        topicStatus: statusFilter.value || undefined,
      },
    })
    rows.value = data.data.list
    total.value = data.data.total
  } catch (e) {
    error.value = formatBiz(e)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void loadList()
}

async function loadBoard() {
  const next: Record<string, BoardCol> = {}
  for (const item of STATUS_OPTIONS) {
    next[item.value] = { rows: [], total: 0, loading: true, error: '' }
  }
  board.value = next
  await Promise.all(
    STATUS_OPTIONS.map(async (item) => {
      try {
        const { data } = await http.get('/content/topic/list', {
          params: { pageNo: 1, pageSize: 20, topicStatus: item.value },
        })
        board.value[item.value] = {
          rows: data.data.list || [],
          total: data.data.total || 0,
          loading: false,
          error: '',
        }
      } catch (e) {
        board.value[item.value] = { rows: [], total: 0, loading: false, error: formatBiz(e) }
      }
    }),
  )
}

function showList() {
  view.value = 'list'
  void loadList()
}

function showBoard() {
  view.value = 'board'
  void loadBoard()
}

async function refreshCurrent() {
  if (view.value === 'board') await loadBoard()
  else await loadList()
}

function openCreate() {
  form.value = { title: '', description: '', sourceType: 'ORIGINAL' }
  createError.value = ''
  createOpen.value = true
}

async function saveTopic() {
  saving.value = true
  createError.value = ''
  try {
    await http.post('/content/topic', {
      title: form.value.title,
      description: form.value.description,
      sourceType: form.value.sourceType,
    })
    createOpen.value = false
    await refreshCurrent()
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
  clearApproveFieldErrors()
  reviewOpen.value = true
  try {
    const { data } = await http.get('/content/sop/list', { params: { pageNo: 1, pageSize: 100, status: 'ENABLED' } })
    sops.value = data.data.list
  } catch (e) {
    sops.value = []
    reviewError.value = formatBiz(e)
  }
}

async function submitReview(action: 'APPROVE_PROJECT' | 'REJECT') {
  if (!reviewRow.value) return
  reviewing.value = true
  reviewError.value = ''
  if (action === 'APPROVE_PROJECT') markMissingApproveFields()
  else clearApproveFieldErrors()
  try {
    await http.put(`/content/topic/${reviewRow.value.id}/review`, {
      action,
      planPublishDate: reviewForm.value.planPublishDate || undefined,
      sopId: reviewForm.value.sopId ? Number(reviewForm.value.sopId) : undefined,
      reviewOpinion: reviewForm.value.reviewOpinion || undefined,
    })
    reviewOpen.value = false
    clearApproveFieldErrors()
    await refreshCurrent()
  } catch (e) {
    const code = bizCode(e)
    reviewError.value = formatBiz(e)
    if (code === 1052) markMissingApproveFields()
    else if (code === 1051) {
      sopError.value = 'SOP 不存在或未启用'
      planDateError.value = ''
    }
  } finally {
    reviewing.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.topic-board {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.topic-col {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  min-height: 220px;
  padding: 10px 10px 12px;
}
.topic-col header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;
}
.topic-col .count {
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 9px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text2);
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}
.topic-col .empty {
  padding: 28px 8px;
}
.topic-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  margin-top: 8px;
}
.topic-card .meta {
  margin: 4px 0 8px;
  font-size: 12px;
  color: var(--text2);
}
@media (max-width: 960px) {
  .topic-board {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
