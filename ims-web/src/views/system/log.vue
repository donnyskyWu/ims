<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>操作/登录日志</h1>
        <div class="sub">SYS-006 · 仅 IMS 新操作 · 登录成败写入登录日志</div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'operate' }" @click="switchTab('operate')">操作日志</div>
      <div class="tab" :class="{ on: tab === 'login' }" @click="switchTab('login')">登录日志</div>
    </div>
    <form class="qbar" @submit.prevent="search">
      <input v-model="keyword" placeholder="操作人 / 路径" style="width: 160px" />
      <select v-model="module" style="width: 108px">
        <option value="">全部</option>
        <option value="登录">登录</option>
        <option value="业务">业务</option>
        <option value="内容">内容</option>
        <option value="系统">系统</option>
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
              <th>时间</th>
              <th>用户</th>
              <th>动作</th>
              <th>路径</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4" style="white-space: normal"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="4" style="white-space: normal">
                <div class="empty">
                  <div class="et">{{ error || '没有日志' }}</div>
                  <div class="es">{{ emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in rows" v-else :key="String(row.id)">
              <td class="num">{{ row.time || '—' }}</td>
              <td>{{ row.user || '—' }}</td>
              <td>{{ row.action || '—' }}</td>
              <td class="mono">{{ row.path || '—' }}</td>
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
    <p class="hint">GET /system/operate-log/page · GET /system/login-log/page。契约没有导出接口。</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { http, errorMessage } from '../../api/http'
import { asList, asTotal } from '../../api/read'

const tab = ref<'operate' | 'login'>('operate')
const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const pageNo = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const module = ref('')
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
const emptyHint = computed(() =>
  tab.value === 'login' ? '登录成功和失败都会记在这里' : '已登录的新增、更新、删除会出现在这里',
)

async function load() {
  loading.value = true
  error.value = ''
  const url = tab.value === 'login' ? '/system/login-log/page' : '/system/operate-log/page'
  try {
    const res = await http.get(url, {
      params: {
        pageNo: pageNo.value,
        pageSize: pageSize.value,
        keyword: keyword.value.trim(),
        module: module.value,
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
  keyword.value = ''
  module.value = ''
  search()
}

function switchTab(next: 'operate' | 'login') {
  if (tab.value === next) return
  tab.value = next
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
