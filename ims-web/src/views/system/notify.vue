<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>消息通知</h1>
        <div class="sub">SYS-007 · 站内信 + 钉钉 · 同一租户、事件、业务键只送一次</div>
      </div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <select v-model="eventType" style="width: 180px">
        <option value="">全部事件</option>
        <option value="TASK_PENDING">TASK_PENDING</option>
        <option value="CONTENT_REVIEW_SUBMIT">CONTENT_REVIEW_SUBMIT</option>
        <option value="WORK_HIT">WORK_HIT</option>
      </select>
      <select v-model="channel" style="width: 120px">
        <option value="">全部渠道</option>
        <option value="站内">站内</option>
        <option value="钉钉">钉钉</option>
        <option value="站内+钉钉">站内+钉钉</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>事件类型</th>
              <th>业务键</th>
              <th>接收人</th>
              <th>渠道</th>
              <th>状态</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '没有通知' }}</div>
                  <div class="es">契约只有分页查询。重复事件不会再插一行。</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td class="mono">{{ row.eventType || '—' }}</td>
              <td>{{ row.bizKey || '—' }}</td>
              <td>{{ row.receiver || '—' }}</td>
              <td>{{ row.channel || '—' }}</td>
              <td>
                <span class="tag" :style="row.status === '已送达' ? okStyle : warnStyle">
                  <span class="dot"></span>{{ row.status || '—' }}
                </span>
              </td>
              <td class="num">{{ row.time || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
        <select class="pg-size" :value="pageSize" @change="changeSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
        <span>条/页</span>
        <span class="pg-sp"></span>
        <span class="pg-n" :class="{ dis: pageNo <= 1 }" @click="goto(pageNo - 1)">‹</span>
        <span v-for="n in pageList" :key="n" class="pg-n" :class="{ on: n === pageNo }" @click="goto(n)">{{ n }}</span>
        <span class="pg-n" :class="{ dis: pageNo >= pageCount }" @click="goto(pageNo + 1)">›</span>
      </div>
    </div>
    <p class="hint">GET /system/notify/page。契约没有补发接口，相同 tenant、eventType、bizKey 再次发布会跳过。</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal } from '../../api/read'

const okStyle = 'background:rgba(52,199,89,.12);color:#1e8e3e'
const warnStyle = 'background:rgba(255,149,0,.12);color:#c93400'
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const eventType = ref('')
const channel = ref('')
const loading = ref(false)
const error = ref('')
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pageList = computed(() => {
  const end = Math.min(pageCount.value, Math.max(pageNo.value + 2, 5))
  const start = Math.max(1, end - 4)
  const list: number[] = []
  for (let i = start; i <= Math.min(pageCount.value, start + 4); i += 1) list.push(i)
  return list
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/system/notify/page', {
      params: {
        pageNo: pageNo.value,
        pageSize: pageSize.value,
        eventType: eventType.value,
        channel: channel.value,
      },
    })
    const data = res.data?.data
    rows.value = asList(data)
    total.value = asTotal(data, rows.value.length)
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function search() {
  pageNo.value = 1
  load()
}

function reset() {
  eventType.value = ''
  channel.value = ''
  search()
}

function goto(page: number) {
  if (page < 1 || page > pageCount.value || page === pageNo.value) return
  pageNo.value = page
  load()
}

function changeSize(event: Event) {
  pageSize.value = Number((event.target as HTMLSelectElement).value)
  pageNo.value = 1
  load()
}

onMounted(load)
</script>
