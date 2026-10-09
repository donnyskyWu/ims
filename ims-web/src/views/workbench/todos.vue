<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>待办中心</h1>
        <div class="sub">AUTH-004 · GET /auth/workbench/todos</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/workbench">工作台首页</router-link>
    </div>
    <form class="qbar" @submit.prevent="load">
      <select v-model="filters.status" style="width: 110px">
        <option value="">全部状态</option>
        <option value="PENDING">待处理</option>
        <option value="DONE">已完成</option>
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
              <th>类型</th>
              <th>截止</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="5"><div class="empty"><div class="et">{{ error || '暂无待办' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id" :style="row.overdue ? 'background:#fff4f2' : ''">
              <td>{{ row.title }}</td>
              <td>{{ row.taskType }}</td>
              <td class="mono">{{ row.deadline || '—' }}</td>
              <td>{{ row.status }}</td>
              <td>
                <button
                  v-if="row.status === 'PENDING' && transferTodoPath(row)"
                  class="btn btn-pri btn-sm"
                  type="button"
                  data-testid="wb-center-acct-transfer-go"
                  @click="router.push(transferTodoPath(row))"
                >
                  去处理
                </button>
                <button
                  v-else-if="row.status === 'PENDING'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  @click="done(row.id)"
                >
                  完成
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
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

type Row = {
  id: number
  title: string
  taskType: string
  refId?: number
  content?: string
  deadline?: string
  status: string
  overdue?: boolean
}

const router = useRouter()

function platformSlug(platform: string) {
  const map: Record<string, string> = {
    DOUYIN: 'douyin',
    KUAISHOU: 'kuaishou',
    XIAOHONGSHU: 'xiaohongshu',
    WECHAT_OFFICIAL: 'wechat-official',
    WECHAT_CHANNELS: 'wechat-channels',
  }
  return map[platform.trim().toUpperCase()] || 'douyin'
}

function transferTodoPath(row: Row) {
  if (row.taskType !== 'acct_transfer' || !row.refId) return ''
  const platform = String(row.content || '').split('|')[0] || 'DOUYIN'
  return `/ims/corp/account/${platformSlug(platform)}?transferId=${row.refId}`
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ status: 'PENDING' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await http.get('/auth/workbench/todos', {
      params: { pageNo: 1, pageSize: 50, status: filters.status || undefined },
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

async function done(id: number) {
  await http.put(`/auth/workbench/todos/${id}`, { action: 'DONE' })
  await load()
}

onMounted(load)
</script>
