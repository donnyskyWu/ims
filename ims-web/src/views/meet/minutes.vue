<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>会议管理</h1>
        <div class="sub">MEET-004 · 纪要登记 · 03 MEET</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">登记会议</button>
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
      <div class="card" style="width: 440px; padding: 20px; max-height: 90vh; overflow: auto">
        <h3 style="margin: 0 0 12px">登记会议 / 录入纪要</h3>
        <label class="fld">主题</label>
        <input v-model="form.meetingTitle" class="fld-in" />
        <label class="fld">会议时间（ISO）</label>
        <input v-model="form.meetingDate" class="fld-in" placeholder="2026-10-07T16:00:00+08:00" />
        <label class="fld">会议室</label>
        <input v-model="form.meetingRoom" class="fld-in" placeholder="3F-大会议室 / 线上" />
        <label class="fld">纪要正文（留空则仅登记）</label>
        <textarea v-model="form.summary" class="fld-in" rows="4" />
        <label class="fld">参会人（逗号分隔姓名）</label>
        <input v-model="form.attendeesText" class="fld-in" placeholder="张三,李四" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submit">保存</button>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

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
const detail = ref<Record<string, unknown> | null>(null)
const archiveStat = ref({ totalMeetings: 0, archivedCount: 0, traceRate: 0 })

const filters = reactive({ meetingTitle: '', minutesStatus: '' })
const form = reactive({
  meetingTitle: '',
  meetingDate: '',
  meetingRoom: '',
  summary: '',
  attendeesText: '',
})

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
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  formError.value = ''
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const off = -now.getTimezoneOffset()
  const sign = off >= 0 ? '+' : '-'
  const oh = pad(Math.floor(Math.abs(off) / 60))
  const om = pad(Math.abs(off) % 60)
  form.meetingDate = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:00${sign}${oh}:${om}`
  form.meetingTitle = ''
  form.meetingRoom = ''
  form.summary = ''
  form.attendeesText = ''
  showForm.value = true
}

async function submit() {
  formError.value = ''
  const attendees = form.attendeesText
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((userName) => ({ userName }))
  try {
    const res = await http.post('/meet/minutes', {
      meetingTitle: form.meetingTitle,
      meetingDate: form.meetingDate,
      meetingRoom: form.meetingRoom,
      attendees,
      summary: form.summary,
    })
    if (res.data.code !== 0) {
      formError.value = res.data.msg || '保存失败'
      return
    }
    showForm.value = false
    await loadList()
  } catch {
    formError.value = '网络错误'
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
