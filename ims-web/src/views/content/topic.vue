<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>选题计划</h1>
        <div class="sub">选题库：筛选、详情、待评审编辑、落选复活与排期甘特（CONTENT-002 · TOP-R1 / TOP-R3）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri" type="button" data-testid="topic-create-open" @click="openCreate">提报选题</button>
      </div>
    </div>
    <div class="tabs" data-testid="topic-view-switch">
      <button type="button" class="tab" :class="{ on: view === 'list' }" data-testid="topic-view-list" @click="view = 'list'">
        列表
      </button>
      <button type="button" class="tab" :class="{ on: view === 'board' }" data-testid="topic-view-board" @click="showBoard">
        状态看板
      </button>
      <button type="button" class="tab" :class="{ on: view === 'gantt' }" data-testid="topic-view-gantt" @click="view = 'gantt'">
        排期甘特
      </button>
    </div>
    <TopicGantt v-if="view === 'gantt'" />
    <form v-if="view === 'list'" class="qbar" @submit.prevent="loadList">
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
                <div
                  class="empty"
                  data-testid="topic-list-empty"
                  :data-filtered="listFiltered ? '1' : '0'"
                  :data-status="statusFilter || 'ALL'"
                >
                  <div class="et">{{ listEmptyTitle }}</div>
                  <div class="es">{{ listEmptyHint }}</div>
                  <button v-if="error" class="btn btn-sec btn-sm" type="button" data-testid="topic-list-retry" @click="loadList">重试</button>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.topicNo }}</td>
              <td><b :title="row.title">{{ row.title }}</b></td>
              <td>{{ sourceLabel(row.sourceType) }}</td>
              <td>{{ row.submitterName || '—' }}</td>
              <td>{{ row.planPublishDate || '—' }}</td>
              <td>{{ row.sopName || '—' }}</td>
              <td data-testid="topic-status">{{ statusLabel(row.topicStatus) }}</td>
              <td data-testid="topic-opinion-cell" :title="row.reviewOpinion || undefined">{{ row.reviewOpinion || '—' }}</td>
              <td data-testid="topic-task-gate">{{ taskGateLabel(row) }}</td>
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

    <div v-else-if="view === 'board'" class="topic-board" data-testid="topic-status-board">
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
          <div class="es">{{ statusEmptyHint[item.value] }}</div>
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

    <ProtoDrawer :open="createOpen" :title="editorMode === 'edit' ? '编辑选题' : '提报选题'" width="600px" @close="createOpen = false">
      <div class="formrow one">
        <div class="fld">
          <label>标题 *</label>
          <input
            v-model="form.title"
            maxlength="256"
            data-testid="topic-title"
            :class="{ err: !!titleError }"
            @input="titleError = ''"
          />
          <p class="hint">不超过 256 字</p>
          <p v-if="titleError" class="ferr" data-testid="topic-title-error">{{ titleError }}</p>
        </div>
        <div class="fld">
          <label>内容要求 *</label>
          <textarea
            v-model="form.description"
            maxlength="2000"
            rows="4"
            data-testid="topic-description"
            :class="{ err: !!descriptionError }"
            @input="descriptionError = ''"
          />
          <p class="hint">不超过 2000 字</p>
          <p v-if="descriptionError" class="ferr" data-testid="topic-description-error">{{ descriptionError }}</p>
        </div>
        <div class="fld">
          <label>来源类型 *</label>
          <select v-model="form.sourceType" data-testid="topic-source" @change="onSourceChange">
            <option v-for="item in sourceOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div v-if="form.sourceType === 'HOTSPOT'" class="hotspot" data-testid="topic-hotspot">
          <div class="hotspot-h">热点参考 <span>只读 · 作品监测</span></div>
          <div v-if="hotspotLoading" class="empty"><div class="et">加载中</div></div>
          <div v-else-if="hotspotError" data-testid="topic-hotspot-error">
            <p class="hint bad">{{ hotspotError }}</p>
            <button class="btn btn-sec btn-sm" type="button" data-testid="topic-hotspot-retry" @click="loadHotspot">重试</button>
          </div>
          <div v-else-if="!hotspotRows.length" class="empty" data-testid="topic-hotspot-empty">
            <div class="et">热点榜暂无数据</div>
          </div>
          <ul v-else class="hotspot-list">
            <li v-for="row in hotspotRows" :key="row.dimensionKey" data-testid="topic-hotspot-row">
              {{ row.dimensionLabel }} · 作品 {{ row.workCount }} · 爆款 {{ row.hitCount }}
            </li>
          </ul>
        </div>
        <div class="fld">
          <label>计划发布日</label>
          <input
            v-model="form.planPublishDate"
            type="date"
            data-testid="topic-edit-plan-date"
            :class="{ err: !!planEarlyError }"
            @input="planEarlyError = ''"
          />
          <p class="hint">可选。填写后，待评审选题也会出现在排期甘特。不能早于今天。</p>
          <p v-if="planEarlyError" class="ferr" data-testid="topic-plan-early-error">{{ planEarlyError }}</p>
        </div>
        <template v-if="editorMode === 'edit'">
          <div class="fld">
            <label>建议 SOP</label>
            <select v-model="form.sopId" data-testid="topic-edit-sop">
              <option value="">不挂接</option>
              <option v-for="sop in sops" :key="sop.id" :value="String(sop.id)">{{ sop.sopName }}</option>
            </select>
            <p v-if="sopLoading" class="hint">正在加载启用中的 SOP</p>
            <p v-else-if="!createError && !sops.length" class="hint" data-testid="topic-edit-sop-empty">暂无启用中的 SOP，建议项可以留空。</p>
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
          <select v-model="reviewForm.sopId" data-testid="topic-sop" :class="{ err: !!sopFieldError }" @change="onReviewSopChange">
            <option value="">请选择 SOP</option>
            <option v-for="sop in sops" :key="sop.id" :value="String(sop.id)">{{ sop.sopName }}</option>
          </select>
          <p v-if="sopFieldError" class="ferr" data-testid="topic-sop-error">{{ sopFieldError }}</p>
          <p v-if="sopLoading" class="hint">正在加载启用中的 SOP</p>
          <p v-else-if="!reviewError && !sops.length" class="hint" data-testid="topic-sop-empty">暂无启用中的 SOP。请先在 SOP 管理启用一条，再立项。</p>
        </div>
        <div class="fld">
          <label>计划发布日 *</label>
          <input
            v-model="reviewForm.planPublishDate"
            type="date"
            data-testid="topic-plan-date"
            :class="{ err: !!planFieldError }"
            @input="onReviewDateInput"
          />
          <p v-if="planDatePrefilled && !planFieldError" class="hint" data-testid="topic-plan-prefill">已带出提报时的计划发布日，立项前请确认。</p>
          <p v-if="planFieldError" class="ferr" data-testid="topic-plan-date-error">{{ planFieldError }}</p>
        </div>
        <div class="fld">
          <label>评审意见</label>
          <textarea v-model="reviewForm.reviewOpinion" maxlength="512" rows="3" data-testid="topic-opinion" placeholder="落选时必填" />
          <p class="hint">不超过 512 字。</p>
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
        <p class="hint">不超过 512 字。</p>
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
import { computed, onMounted, ref } from 'vue'
import { errorMessage, http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import TopicGantt from './topic-gantt.vue'

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
const statusEmptyHint: Record<string, string> = {
  PENDING_REVIEW: '提报后会出现在这一列',
  APPROVED_PROJECT: '评审立项并通过后会出现在这一列',
  REJECTED: '落选归档后会出现在这一列',
  CANCELLED: '取消后的选题会出现在这一列',
}

type BoardCol = { rows: TopicRow[]; total: number; loading: boolean; error: string }

const view = ref<'list' | 'gantt' | 'board'>('list')
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
const board = ref<Record<string, BoardCol>>({})
const createOpen = ref(false)
const editorMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const saving = ref(false)
const createError = ref('')
const form = ref({ title: '', description: '', sourceType: 'ORIGINAL', planPublishDate: '', sopId: '' })
const titleError = ref('')
const descriptionError = ref('')
const planEarlyError = ref('')
const reviewOpen = ref(false)
const reviewing = ref(false)
const reviewError = ref('')
const reviewRow = ref<TopicRow | null>(null)
const reviewForm = ref({ sopId: '', planPublishDate: '', reviewOpinion: '' })
const sopFieldError = ref('')
const planFieldError = ref('')
const planDatePrefilled = computed(() => {
  const saved = (reviewRow.value?.planPublishDate || '').trim()
  return Boolean(saved) && reviewForm.value.planPublishDate === saved
})
const sops = ref<{ id: number; sopName: string }[]>([])
const sopLoading = ref(false)
const hotspotRows = ref<{ dimensionKey: string; dimensionLabel: string; workCount: number; hitCount: number }[]>([])
const hotspotLoading = ref(false)
const hotspotError = ref('')
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

function taskGateLabel(row: TopicRow) {
  if (row.canCreateTask) return '可出任务'
  if (row.topicStatus === 'REJECTED') return '落选不可出任务'
  if (row.topicStatus === 'CANCELLED') return '已取消不可出任务'
  return '未立项不可出任务'
}

const listFiltered = computed(() =>
  Boolean(
    topicNo.value.trim()
    || keyword.value.trim()
    || sourceFilter.value
    || statusFilter.value
    || submitterFilter.value,
  ),
)

const listEmptyTitle = computed(() => {
  if (error.value) return error.value
  const active = [
    topicNo.value.trim(),
    keyword.value.trim(),
    sourceFilter.value,
    statusFilter.value,
    submitterFilter.value,
  ].filter(Boolean).length
  if (active === 0) return '暂无选题'
  if (active > 1) return '暂无符合当前筛选的选题'
  if (topicNo.value.trim()) return '没有符合编号的选题'
  if (keyword.value.trim()) return '没有符合关键词的选题'
  if (sourceFilter.value) return `暂无${sourceLabel(sourceFilter.value)}来源的选题`
  if (statusFilter.value) return `暂无${statusLabel(statusFilter.value)}选题`
  return '该提报人暂无选题'
})

const listEmptyHint = computed(() => {
  if (error.value) return '列表加载失败，可重试'
  if (!listFiltered.value) return '点击「提报选题」后进入待评审'
  const bits: string[] = []
  if (topicNo.value.trim()) bits.push(`编号 ${topicNo.value.trim()}（需完整匹配）`)
  if (keyword.value.trim()) bits.push(`关键词 ${keyword.value.trim()}`)
  if (sourceFilter.value) bits.push(`来源 ${sourceLabel(sourceFilter.value)}`)
  if (statusFilter.value) bits.push(`状态 ${statusLabel(statusFilter.value)}`)
  if (submitterFilter.value) {
    const user = submitters.value.find((item) => item.id === submitterFilter.value)
    bits.push(`提报人 ${user?.label || '已选'}`)
  }
  return `当前筛选：${bits.join('、')}。可调整条件，或点重置查看全部`
})

function todayText() {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

function planDateTooEarly(value: string) {
  const text = value.trim()
  return Boolean(text) && text < todayText()
}

function resetFormErrors() {
  titleError.value = ''
  descriptionError.value = ''
  planEarlyError.value = ''
}

function onReviewSopChange() {
  if (reviewForm.value.sopId) sopFieldError.value = ''
}

function onReviewDateInput() {
  if (!reviewForm.value.planPublishDate) return
  if (!planDateTooEarly(reviewForm.value.planPublishDate)) planFieldError.value = ''
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

function boardCol(status: string): BoardCol {
  return board.value[status] || { rows: [], total: 0, loading: true, error: '' }
}

async function loadBoard() {
  const next: Record<string, BoardCol> = {}
  for (const item of statusOptions) {
    next[item.value] = { rows: [], total: 0, loading: true, error: '' }
  }
  board.value = next
  await Promise.all(
    statusOptions.map(async (item) => {
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

function showBoard() {
  view.value = 'board'
  void loadBoard()
}

async function refreshTopics() {
  if (view.value === 'board') await loadBoard()
  else await loadList()
}

function openCreate() {
  editorMode.value = 'create'
  editingId.value = null
  form.value = { title: '', description: '', sourceType: 'ORIGINAL', planPublishDate: '', sopId: '' }
  createError.value = ''
  resetFormErrors()
  resetHotspot()
  createOpen.value = true
}

function resetHotspot() {
  hotspotRows.value = []
  hotspotError.value = ''
  hotspotLoading.value = false
}

async function loadHotspot() {
  hotspotLoading.value = true
  hotspotError.value = ''
  try {
    const { data } = await http.get('/monitor/ip-theme/page', { params: { pageNo: 1, pageSize: 5 } })
    hotspotRows.value = data.data?.list || []
  } catch (e) {
    hotspotRows.value = []
    hotspotError.value = formatBiz(e)
  } finally {
    hotspotLoading.value = false
  }
}

function onSourceChange() {
  if (form.value.sourceType === 'HOTSPOT') {
    loadHotspot()
    return
  }
  resetHotspot()
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
  resetFormErrors()
  sops.value = []
  sopLoading.value = true
  createOpen.value = true
  onSourceChange()
  try {
    await loadSops()
  } catch (e) {
    sops.value = []
    createError.value = formatBiz(e)
  } finally {
    sopLoading.value = false
  }
}

async function saveTopic() {
  resetFormErrors()
  createError.value = ''
  const title = form.value.title.trim()
  const description = form.value.description.trim()
  if (!title) titleError.value = '请填写选题标题'
  if (!description) descriptionError.value = '请填写内容要求'
  if (planDateTooEarly(form.value.planPublishDate)) planEarlyError.value = '计划发布日不能早于今天'
  if (titleError.value || descriptionError.value || planEarlyError.value) return
  saving.value = true
  const payload = {
    title,
    description,
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
        planPublishDate: payload.planPublishDate,
      })
    }
    createOpen.value = false
    await refreshTopics()
  } catch (e) {
    createError.value = formatBiz(e)
  } finally {
    saving.value = false
  }
}

async function openReview(row: TopicRow) {
  reviewRow.value = row
  reviewForm.value = { sopId: '', planPublishDate: row.planPublishDate || '', reviewOpinion: '' }
  reviewError.value = ''
  sopFieldError.value = ''
  planFieldError.value = ''
  sops.value = []
  sopLoading.value = true
  reviewOpen.value = true
  try {
    await loadSops()
  } catch (e) {
    sops.value = []
    reviewError.value = formatBiz(e)
  } finally {
    sopLoading.value = false
  }
}

async function submitReview(action: 'APPROVE_PROJECT' | 'REJECT') {
  if (!reviewRow.value) return
  if (action === 'REJECT' && !reviewForm.value.reviewOpinion.trim()) {
    reviewError.value = '请填写落选意见'
    return
  }
  if (action === 'APPROVE_PROJECT') {
    sopFieldError.value = reviewForm.value.sopId ? '' : '请选择挂接 SOP'
    if (!reviewForm.value.planPublishDate) planFieldError.value = '请填写计划发布日'
    else if (planDateTooEarly(reviewForm.value.planPublishDate)) {
      planFieldError.value = '计划发布日不能早于今天'
      return
    } else planFieldError.value = ''
  }
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
    await refreshTopics()
  } catch (e) {
    reviewError.value = formatBiz(e)
    if (reviewError.value.startsWith('1051')) sopFieldError.value = 'SOP 不存在或未启用'
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
    await refreshTopics()
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
  if (!cancelOpinion.value.trim()) {
    cancelError.value = '请填写取消原因'
    return
  }
  cancelling.value = true
  cancelError.value = ''
  try {
    await http.put(`/content/topic/${cancelRow.value.id}/review`, {
      action: 'CANCEL',
      reviewOpinion: cancelOpinion.value,
    })
    cancelRow.value = null
    await refreshTopics()
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
.tabs button.tab {
  border: none;
  background: transparent;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.hotspot {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  background: #f7f8fa;
}
.hotspot-h {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.hotspot-h span {
  font-weight: 400;
  color: var(--text2);
  font-size: 12px;
}
.hotspot-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
}
.hotspot-list li + li {
  margin-top: 4px;
}
.empty .btn { margin-top: 8px; }
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
.topic-col .empty { padding: 28px 8px; }
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
  .topic-board { grid-template-columns: 1fr 1fr; }
}
</style>
