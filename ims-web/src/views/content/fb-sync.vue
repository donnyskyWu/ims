<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>Football 补偿队列</h1>
        <div class="sub">CONTENT-109/110 · BR-303 写失败进 outbox，IMS 保存不回滚</div>
      </div>
      <div class="acts">
        <router-link class="btn btn-sec" to="/ims/content/list">返回内容管理</router-link>
        <button class="btn btn-pri" type="button" @click="loadList">刷新</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      GET <code>/admin-api/ims/content/fb-sync/outbox/page</code> · POST
      <code>…/fb-sync/outbox/{id}/retry</code>
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <select v-model="statusFilter" style="width: 140px">
        <option value="">全部状态</option>
        <option value="PENDING">PENDING</option>
        <option value="SUCCESS">SUCCESS</option>
        <option value="FAILED">FAILED</option>
      </select>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>内容</th>
              <th>动作</th>
              <th>状态</th>
              <th>重试</th>
              <th>错误</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="7"><div class="empty"><div class="et">{{ error || '暂无补偿任务' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.contentTitle || row.contentProjectId }}</td>
              <td>{{ row.action }}</td>
              <td>{{ row.syncStatus }}</td>
              <td>{{ row.retryCount }}</td>
              <td class="mono">{{ row.lastErrorMsg || '—' }}</td>
              <td>
                <button
                  v-if="row.syncStatus === 'PENDING' || row.syncStatus === 'FAILED'"
                  class="btn btn-pri btn-sm"
                  type="button"
                  @click="retry(row.id)"
                >
                  重试
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager"><span class="pg-total">共 {{ total }} 条</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http, errorMessage } from '../../api/http'

const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const statusFilter = ref('')

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (statusFilter.value) params.syncStatus = statusFilter.value
    const { data } = await http.get('/content/fb-sync/outbox/page', { params })
    rows.value = data.data?.list || []
    total.value = data.data?.total || 0
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function retry(id: number) {
  try {
    await http.post(`/content/fb-sync/outbox/${id}/retry`)
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

loadList()
</script>
