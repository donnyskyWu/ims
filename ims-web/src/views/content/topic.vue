<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>选题计划</h1>
        <div class="sub">选题提报与立项（CONTENT-002 · TOP-R1）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" data-testid="topic-create-open" @click="openCreate">提报选题</button>
      </div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="keyword" placeholder="标题关键词" style="width: 180px" />
      <select v-model="statusFilter" style="width: 140px">
        <option value="">全部状态</option>
        <option value="PENDING_REVIEW">待评审</option>
        <option value="APPROVED_PROJECT">已立项</option>
        <option value="REJECTED">落选</option>
        <option value="CANCELLED">已取消</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

const rows = ref<TopicRow[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const statusFilter = ref('')
const createOpen = ref(false)
const saving = ref(false)
const createError = ref('')
const form = ref({ title: '', description: '', sourceType: 'ORIGINAL' })
const reviewOpen = ref(false)
const reviewing = ref(false)
const reviewError = ref('')
const reviewRow = ref<TopicRow | null>(null)
const reviewForm = ref({ sopId: '', planPublishDate: '', reviewOpinion: '' })
const sops = ref<{ id: number; sopName: string }[]>([])

function statusLabel(status: string) {
  return STATUS_LABEL[status] || status
}

function sourceLabel(source: string) {
  return SOURCE_LABEL[source] || source
}

function formatBiz(err: unknown) {
  if (err && typeof err === 'object' && 'code' in err) {
    const body = err as { code?: number; msg?: string }
    if (body.code) return `${body.code} ${body.msg || '操作失败'}`
  }
  return errorMessage(err)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.get('/content/topic/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        keyword: keyword.value || undefined,
        topicStatus: statusFilter.value || undefined,
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

onMounted(loadList)
</script>
