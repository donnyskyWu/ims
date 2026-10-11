<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>会议管理</h1>
        <div class="sub">MEET-004 · 纪要登记 · 03 MEET</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" data-testid="meet-book" @click="openCreate">预约会议</button>
      </div>
    </div>
    <div class="g3" style="margin-bottom: 12px">
      <div class="card stat"><span class="l">会议总数</span><div class="n">{{ archiveStat.totalMeetings }}</div></div>
      <div class="card stat"><span class="l">已归档</span><div class="n">{{ archiveStat.archivedCount }}</div></div>
      <div class="card stat"><span class="l">留痕率 BR-116</span><div class="n">{{ archiveStat.traceRate }}%</div></div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.meetingTitle" placeholder="主题" style="width: 140px" />
      <select v-model="filters.minutesStatus" style="width: 120px">
        <option value="">全部纪要状态</option>
        <option value="REGISTERED">已登记</option>
        <option value="MINUTES_RECORDED">纪要已录</option>
        <option value="ARCHIVED">已归档</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>纪要编号</th>
              <th>主题</th>
              <th>组织者</th>
              <th>时间</th>
              <th>会议室</th>
              <th>参会</th>
              <th>纪要状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无会议' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono" style="color: var(--blue)">{{ row.minutesNo }}</td>
              <td style="font-weight: 500">{{ row.meetingTitle }}</td>
              <td>{{ row.organizerName || row.recorderName }}</td>
              <td class="mono">{{ row.meetingDate || '—' }}</td>
              <td>{{ row.meetingRoom || '—' }}</td>
              <td class="num">{{ row.attendeeCount }} 人</td>
              <td>{{ statusLabel(row.minutesStatus) }}</td>
              <td>
                <button class="btn btn-sec btn-sm" type="button" @click="openDetail(row.id)">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card meet-dialog" data-testid="meet-book-form">
        <h3 style="margin: 0 0 12px">预约会议</h3>
        <label class="fld">会议主题 *</label>
        <input v-model="form.meetingTitle" class="fld-in" data-testid="meet-title" />
        <p v-if="fieldErrors.meetingTitle" class="err">{{ fieldErrors.meetingTitle }}</p>
        <label class="fld">会议时间 *</label>
        <input v-model="form.meetingDate" class="fld-in" type="datetime-local" data-testid="meet-time" />
        <p v-if="fieldErrors.meetingDate" class="err">{{ fieldErrors.meetingDate }}</p>
        <label class="fld">参会人 *</label>
        <select v-model="form.attendeeIds" class="fld-in" multiple data-testid="meet-attendees" size="5">
          <option v-for="person in people" :key="person.userId" :value="person.userId">
            {{ person.userName }}（{{ person.username }}）
          </option>
        </select>
        <p v-if="fieldErrors.attendees" class="err">{{ fieldErrors.attendees }}</p>
        <label class="fld">记录人</label>
        <select v-model="form.recorderUserId" class="fld-in" data-testid="meet-recorder">
          <option :value="0">默认本人</option>
          <option v-for="person in people" :key="'r' + person.userId" :value="person.userId">{{ person.userName }}</option>
        </select>
        <label class="fld">时长（分钟）</label>
        <input v-model.number="form.durationMinutes" class="fld-in" type="number" min="15" max="480" data-testid="meet-duration" />
        <label class="fld">会议室</label>
        <select v-model="form.meetingRoom" class="fld-in" data-testid="meet-room">
          <option value="">不指定</option>
          <option v-for="room in rooms" :key="room" :value="room">{{ room }}</option>
        </select>
        <label class="fld">议程</label>
        <textarea v-model="form.agenda" class="fld-in" rows="3" data-testid="meet-agenda" />
        <p v-if="formError" class="err">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" data-testid="meet-submit" @click="submit">提交预约</button>
        </div>
      </div>
    </div>

    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="card" style="width: 520px; padding: 20px; max-height: 90vh; overflow: auto">
        <h3 style="margin: 0 0 8px">{{ detail.meetingTitle }}</h3>
        <p class="hint">{{ detail.minutesNo }} · {{ statusLabel(detail.minutesStatus) }}</p>
        <p><b>时间</b> {{ detail.meetingDate }}</p>
        <p><b>会议室</b> {{ detail.meetingRoom || '—' }}</p>
        <p><b>纪要</b></p>
        <pre style="white-space: pre-wrap; font-size: 13px">{{ detail.summary || '（待录入）' }}</pre>
        <div v-if="detail.actionItems?.length">
          <p><b>行动项</b></p>
          <ul>
            <li v-for="it in detail.actionItems" :key="it.itemId">{{ it.description }} → {{ it.responsibleName }}</li>
          </ul>
        </div>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button
            v-if="detail.minutesStatus !== 'ARCHIVED' && detail.minutesStatus !== 'REGISTERED'"
            class="btn btn-pri btn-sm"
            type="button"
            @click="archiveDetail"
          >
            归档
          </button>
          <button class="btn btn-sec btn-sm" type="button" @click="detail = null">关闭</button>
        </div>
      </div>
    </div>
    <div v-if="toast" class="toasts">
      <div class="toast t-success" data-testid="meet-toast">{{ toast }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { errorMessage, http } from '../../api/http'

type Row = {
  id: number
  minutesNo: string
  meetingTitle: string
  meetingDate: string
  meetingRoom?: string
  organizerName?: string
  recorderName: string
  attendeeCount: number
  minutesStatus: string
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const detail = ref<Record<string, any> | null>(null)
const archiveStat = ref({ totalMeetings: 0, archivedCount: 0, traceRate: 0 })

const filters = reactive({ meetingTitle: '', minutesStatus: '' })
const rooms = ['2F-会议室 A', '3F-大会议室', '1F-会议室 B', '线上']
const people = ref<{ userId: number; userName: string; username: string }[]>([])
const form = reactive({
  meetingTitle: '',
  meetingDate: '',
  meetingRoom: '',
  durationMinutes: 60,
  agenda: '',
  attendeeIds: [] as number[],
  recorderUserId: 0,
})
const fieldErrors = reactive({ meetingTitle: '', meetingDate: '', attendees: '' })
const toast = ref('')

function statusLabel(s: string) {
  const map: Record<string, string> = {
    REGISTERED: '已登记',
    MINUTES_RECORDED: '纪要已录',
    ARCHIVED: '已归档',
  }
  return map[s] || s
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/meet/minutes/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        meetingTitle: filters.meetingTitle || undefined,
        minutesStatus: filters.minutesStatus || undefined,
      },
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data?.list || []
  } catch (e: unknown) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

function bizDateTime(value: string) {
  if (!value) return ''
  const text = value.length === 16 ? `${value}:00` : value
  return `${text}+08:00`
}

async function loadPeople() {
  try {
    const res = await http.get('/meet/minutes/participants')
    people.value = res.data.data?.list || []
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  }
}

function openCreate() {
  formError.value = ''
  toast.value = ''
  fieldErrors.meetingTitle = ''
  fieldErrors.meetingDate = ''
  fieldErrors.attendees = ''
  form.meetingTitle = ''
  form.meetingDate = ''
  form.meetingRoom = ''
  form.durationMinutes = 60
  form.agenda = ''
  form.attendeeIds = []
  form.recorderUserId = 0
  showForm.value = true
  loadPeople()
}

function validateForm() {
  fieldErrors.meetingTitle = form.meetingTitle.trim() ? '' : '必填项，请填写'
  fieldErrors.meetingDate = form.meetingDate ? '' : '必填项，请填写'
  fieldErrors.attendees = form.attendeeIds.length ? '' : '必填项，请填写'
  return !fieldErrors.meetingTitle && !fieldErrors.meetingDate && !fieldErrors.attendees
}

async function submit() {
  formError.value = ''
  toast.value = ''
  if (!validateForm()) {
    formError.value = '必填项，请填写'
    return
  }
  const attendees = form.attendeeIds.map((userId) => {
    const person = people.value.find((item) => item.userId === userId)
    return { userId, userName: person?.userName || '' }
  })
  try {
    const res = await http.post('/meet/minutes', {
      meetingTitle: form.meetingTitle.trim(),
      meetingDate: bizDateTime(form.meetingDate),
      meetingRoom: form.meetingRoom,
      durationMinutes: form.durationMinutes || 60,
      agenda: form.agenda,
      recorderUserId: form.recorderUserId || undefined,
      attendees,
    })
    const no = res.data.data?.minutesNo || ''
    toast.value = no ? `会议已登记 · ${no}` : '会议已登记'
    showForm.value = false
    await loadList()
    await loadArchiveRate()
  } catch (e: unknown) {
    formError.value = errorMessage(e)
  }
}

async function openDetail(id: number) {
  try {
    const res = await http.get(`/meet/minutes/${id}`)
    if (res.data.code === 0) detail.value = res.data.data
  } catch {
    /* ignore */
  }
}

async function loadArchiveRate() {
  try {
    const res = await http.get('/meet/minutes/archive-rate')
    if (res.data.code === 0) {
      archiveStat.value = {
        totalMeetings: res.data.data.totalMeetings,
        archivedCount: res.data.data.archivedCount,
        traceRate: res.data.data.traceRate,
      }
    }
  } catch {
    /* ignore */
  }
}

async function archiveDetail() {
  if (!detail.value?.id) return
  const res = await http.put(`/meet/minutes/${detail.value.id}/archive`)
  if (res.data.code === 0) {
    detail.value = res.data.data
    await loadList()
    await loadArchiveRate()
  }
}

onMounted(() => {
  loadList()
  loadArchiveRate()
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px 16px;
}
.meet-dialog {
  width: min(560px, 100%);
  max-height: min(90vh, 820px);
  overflow: auto;
  padding: 20px;
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2, #6e6e73);
  margin: 10px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
.err {
  color: var(--red, #d70015);
  font-size: 12px;
  margin: 4px 0 0;
}
</style>
