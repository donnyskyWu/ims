<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>待我审阅</h1>
        <div class="sub">MEET-002 · 一级 24h 超时标红 · 二级审阅完成后状态 READ</div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: level === 1 }" @click="level = 1; loadQueue()">一级审阅</div>
      <div class="tab" :class="{ on: level === 2 }" @click="level = 2; loadQueue()">二级审阅</div>
    </div>
    <form class="qbar" @submit.prevent="loadQueue">
      <input v-model="filters.dateFrom" type="date" style="width: 140px" />
      <input v-model="filters.dateTo" type="date" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">刷新</button>
      <button class="btn btn-sec btn-sm" type="button" data-testid="review-batch" :disabled="!selected.length" @click="openBatch">
        批量已读
      </button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th style="width: 36px"></th>
              <th>日期</th>
              <th>提交人</th>
              <th>等待(h)</th>
              <th>超时</th>
              <th>今日完成</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无待审' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td><input type="checkbox" :checked="selected.includes(row.id)" @change="toggle(row.id)" /></td>
              <td class="num">{{ row.reportDate }}</td>
              <td>{{ row.userName }}</td>
              <td class="num">{{ row.waitingHours }}</td>
              <td><span v-if="row.isTimeout" class="tag tag-warn">超时</span><span v-else>—</span></td>
              <td style="max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ row.contentDone }}</td>
              <td><button class="btn btn-pri btn-sm" type="button" @click="openReview(row)">审阅</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="drawerOpen" class="drawer-mask" @click.self="drawerOpen = false">
      <div class="drawer on" data-testid="daily-review-drawer" style="width: min(720px, 100vw)">
        <div class="drawer-h">
          <b>审阅 · {{ active?.userName }} · {{ active?.reportDate }}</b>
          <button type="button" class="btn btn-sec btn-sm" @click="drawerOpen = false">关闭</button>
        </div>
        <div v-if="active" class="drawer-b">
          <p data-testid="review-submitter"><strong>提交人</strong> {{ active.userName || '—' }}</p>
          <p data-testid="review-completeness"><strong>字段完成度</strong> {{ active.fieldCompleteness ?? '—' }}%</p>
          <p><strong>今日完成</strong><br />{{ active.contentDone }}</p>
          <p><strong>明日计划</strong><br />{{ active.contentPlan }}</p>
          <p><strong>问题与风险</strong><br />{{ active.contentIssue }}</p>
          <label class="rowline" style="margin-top: 12px">
            <span style="min-width: 72px">点评</span>
            <textarea v-model="comment" rows="3" style="flex: 1" placeholder="可选" />
          </label>
          <div v-if="followOpen" class="card" style="padding: 12px; margin-top: 12px" data-testid="review-follow">
            <label class="fld">描述 *</label>
            <input v-model="follow.description" class="fld-in" data-testid="review-follow-desc" />
            <label class="fld">责任人 *</label>
            <select v-model="follow.responsibleUserId" class="fld-in" data-testid="review-follow-owner">
              <option :value="0">请选择</option>
              <option v-for="person in people" :key="person.userId" :value="person.userId">{{ person.userName }}</option>
            </select>
            <label class="fld">期限 *</label>
            <input v-model="follow.dueDate" class="fld-in" type="date" data-testid="review-follow-due" />
            <p v-if="followError" class="err">{{ followError }}</p>
          </div>
          <div class="acts" style="margin-top: 16px; gap: 8px; flex-wrap: wrap">
            <button class="btn btn-pri btn-sm" type="button" :disabled="submitting" @click="submit('READ')">已读</button>
            <button class="btn btn-sec btn-sm" type="button" :disabled="submitting" @click="submit('COMMENT')">点评</button>
            <button class="btn btn-sec btn-sm" type="button" data-testid="review-follow-btn" :disabled="submitting" @click="submitFollow">
              标记跟进
            </button>
          </div>
          <p v-if="actionError" class="err">{{ actionError }}</p>
        </div>
      </div>
    </div>
    <div v-if="batchOpen" class="modal-mask" data-testid="review-batch-dialog">
      <div class="card" style="width: min(420px, 92vw); padding: 16px">
        <h3 style="margin: 0 0 8px">批量已读</h3>
        <p>将把 {{ selectedRows.length }} 份标为已读：{{ selectedNames }}</p>
        <p v-if="actionError" class="err">{{ actionError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="batchOpen = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="review-batch-ok" :disabled="submitting" @click="confirmBatch">确认</button>
        </div>
      </div>
    </div>
    <div v-if="toast" class="toasts">
      <div class="toast t-success">{{ toast }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type QueueRow = {
  id: number
  reportDate: string
  userName: string
  fieldCompleteness?: number
  contentDone: string
  contentPlan: string
  contentIssue: string
  reviewLevel: number
  waitingHours: number
  isTimeout: boolean
}

const rows = ref<QueueRow[]>([])
const loading = ref(false)
const error = ref('')
const level = ref(1)
const filters = reactive({ dateFrom: '', dateTo: '' })
const drawerOpen = ref(false)
const active = ref<QueueRow | null>(null)
const comment = ref('')
const submitting = ref(false)
const selected = ref<number[]>([])
const batchOpen = ref(false)
const followOpen = ref(false)
const followError = ref('')
const actionError = ref('')
const toast = ref('')
const people = ref<{ userId: number; userName: string }[]>([])
const follow = reactive({ description: '', responsibleUserId: 0, dueDate: '' })
const selectedRows = computed(() => rows.value.filter((row) => selected.value.includes(row.id)))
const selectedNames = computed(() => selectedRows.value.map((row) => row.userName).join('、'))

async function loadQueue() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20, reviewLevel: level.value }
    if (filters.dateFrom) params.dateFrom = filters.dateFrom
    if (filters.dateTo) params.dateTo = filters.dateTo
    const res = await http.get('/meet/review/queue', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function openReview(row: QueueRow) {
  active.value = row
  comment.value = ''
  followOpen.value = false
  followError.value = ''
  actionError.value = ''
  follow.description = ''
  follow.responsibleUserId = 0
  follow.dueDate = ''
  drawerOpen.value = true
  loadPeople()
}

function toggle(id: number) {
  selected.value = selected.value.includes(id) ? selected.value.filter((item) => item !== id) : [...selected.value, id]
}

function openBatch() {
  actionError.value = ''
  batchOpen.value = true
}

async function loadPeople() {
  if (people.value.length) return
  try {
    const res = await http.get('/meet/minutes/participants')
    people.value = res.data.data?.list || []
  } catch (e: unknown) {
    actionError.value = errorMessage(e)
  }
}

async function submit(action: string, extra: Record<string, unknown> = {}) {
  if (!active.value) return
  submitting.value = true
  actionError.value = ''
  try {
    await http.put(`/meet/review/${active.value.id}`, {
      reviewLevel: level.value,
      action,
      comment: comment.value,
      ...extra,
    })
    drawerOpen.value = false
    selected.value = selected.value.filter((id) => id !== active.value?.id)
    toast.value = action === 'MARK_FOLLOW_UP' ? '已标记跟进' : action === 'COMMENT' ? '点评已提交' : '已读'
    await loadQueue()
  } catch (e: unknown) {
    actionError.value = errorMessage(e)
  } finally {
    submitting.value = false
  }
}

async function submitFollow() {
  followError.value = ''
  followOpen.value = true
  if (!follow.description.trim() || !follow.responsibleUserId || !follow.dueDate) {
    followError.value = '必填项，请填写'
    return
  }
  await submit('MARK_FOLLOW_UP', {
    followUpItems: [
      {
        description: follow.description.trim(),
        responsibleUserId: follow.responsibleUserId,
        dueDate: follow.dueDate,
      },
    ],
  })
}

async function confirmBatch() {
  submitting.value = true
  actionError.value = ''
  const targets = [...selectedRows.value]
  try {
    for (const row of targets) {
      await http.put(`/meet/review/${row.id}`, { reviewLevel: level.value, action: 'READ' })
    }
    toast.value = `已批量已读 ${targets.length} 份`
    selected.value = []
    batchOpen.value = false
    await loadQueue()
  } catch (e: unknown) {
    actionError.value = errorMessage(e)
  } finally {
    submitting.value = false
  }
}

onMounted(loadQueue)
</script>

<style scoped>
.drawer-mask,
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
}
.drawer-mask {
  display: block;
}
.fld {
  display: block;
  font-size: 12px;
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.err {
  color: #d70015;
  font-size: 12px;
}
</style>
