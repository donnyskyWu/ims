<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>消息中心</h1>
        <div class="sub">AUTH-004 · GET /auth/workbench/messages</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="readAll">全部已读</button>
        <router-link class="btn btn-sec btn-sm" to="/ims/workbench">工作台首页</router-link>
      </div>
    </div>
    <form class="qbar" @submit.prevent="load">
      <select v-model="filters.read" style="width: 110px">
        <option value="">全部</option>
        <option value="false">未读</option>
        <option value="true">已读</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>来源</th>
              <th>已读</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无消息' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td>{{ row.title }}</td>
              <td>{{ row.sourceModule || '—' }}</td>
              <td>{{ row.read ? '是' : '否' }}</td>
              <td class="mono">{{ row.createdAt?.slice(0, 16) || '—' }}</td>
              <td>
                <button v-if="!row.read" class="btn btn-txt btn-sm" type="button" @click="readOne(row.id)">
                  标已读
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { http } from '../../api/http'

type Row = { id: number; title: string; sourceModule?: string; read: boolean; createdAt?: string }

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ read: 'false' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.read === 'true') params.read = true
    if (filters.read === 'false') params.read = false
    const res = await http.get('/auth/workbench/messages', { params })
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

async function readOne(id: number) {
  await http.put(`/auth/workbench/messages/${id}/read`)
  await load()
}

async function readAll() {
  await http.put('/auth/workbench/messages/read-all')
  await load()
}

onMounted(load)
</script>
