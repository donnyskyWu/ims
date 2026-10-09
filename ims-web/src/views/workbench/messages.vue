<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>消息中心</h1>
        <div class="sub">AUTH-004 · 站内与钉钉消息</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="readAll">全部已读</button>
        <router-link
          v-if="sourceModule === 'BI'"
          class="btn btn-sec btn-sm"
          data-testid="wb-back-bi"
          to="/ims/bi/report/preview"
        >返回报表预览</router-link>
        <router-link
          v-if="sourceModule === 'DC'"
          class="btn btn-sec btn-sm"
          data-testid="wb-back-dc"
          to="/ims/dc/trace"
        >返回穿透查询</router-link>
        <router-link class="btn btn-sec btn-sm" to="/ims/workbench">工作台首页</router-link>
      </div>
    </div>
    <p v-if="sourceModule" class="hint" data-testid="wb-source-filter">来源 {{ sourceModule }}</p>
    <form class="qbar" @submit.prevent="search">
      <input v-model="filters.keyword" data-testid="msg-keyword" placeholder="标题 / 摘要" style="width: 180px" />
      <select v-model="filters.read" data-testid="msg-read" style="width: 110px">
        <option value="">全部</option>
        <option value="false">未读</option>
        <option value="true">已读</option>
      </select>
      <select v-model="filters.channel" data-testid="msg-channel" style="width: 120px">
        <option value="">全部类型</option>
        <option value="IN_APP">站内</option>
        <option value="DINGTALK">钉钉</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit" data-testid="msg-search">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>类型</th>
              <th>来源</th>
              <th>已读</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!visibleRows.length">
              <td colspan="6">
                <div class="empty" :data-testid="sourceModule ? 'wb-source-empty' : 'msg-empty'">
                  <div class="et">{{ emptyText }}</div>
                  <div v-if="!sourceModule" class="es">{{ emptyHint }}</div>
                </div>
              </td>
            </tr>
            <tr v-for="row in visibleRows" v-else :key="row.id" data-testid="msg-row">
              <td>{{ row.title }}</td>
              <td><span class="tag" data-testid="msg-channel-tag">{{ channelLabel(row.channel) }}</span></td>
              <td>{{ row.sourceModule || '—' }}</td>
              <td>{{ row.read ? '是' : '否' }}</td>
              <td class="mono">{{ row.createdAt?.slice(0, 16) || '—' }}</td>
              <td>
                <button class="btn btn-txt btn-sm" type="button" @click="openDetail(row)">查看</button>
                <button v-if="!row.read" class="btn btn-txt btn-sm" type="button" @click="readOne(row.id)">标已读</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span class="pg-total">共 {{ total }} 条</span>
      </div>
    </div>
    <ProtoDrawer :open="detailOpen" title="消息详情" width="520px" @close="detailOpen = false">
      <div v-if="detail" data-testid="msg-detail">
        <div class="fld" style="margin-bottom: 10px">
          <label>类型</label>
          <div><span class="tag">{{ channelLabel(detail.channel) }}</span></div>
        </div>
        <div class="fld" style="margin-bottom: 10px">
          <label>来源</label>
          <div>{{ detail.sourceModule || '—' }}</div>
        </div>
        <div class="fld" style="margin-bottom: 10px">
          <label>标题</label>
          <div>{{ detail.title }}</div>
        </div>
        <div class="fld">
          <label>正文</label>
          <div>{{ detail.content || '—' }}</div>
        </div>
      </div>
      <template #foot>
        <button v-if="detail && !detail.read" class="btn btn-pri" type="button" @click="readOne(detail.id)">标已读</button>
        <button class="btn btn-sec" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </ProtoDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api/http'
import ProtoDrawer from '../../components/ProtoDrawer.vue'
import { notifyInboxChanged } from '../../inbox/sync'

type Row = {
  id: number
  title: string
  content?: string
  channel?: string
  sourceModule?: string
  read: boolean
  createdAt?: string
}

const route = useRoute()
const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const total = ref(0)
const filters = reactive({ read: 'false', channel: '', keyword: '' })
const detailOpen = ref(false)
const detail = ref<Row | null>(null)
const sourceModule = computed(() => {
  const raw = route.query.sourceModule
  return typeof raw === 'string' ? raw : ''
})
const visibleRows = computed(() => {
  if (!sourceModule.value) return rows.value
  return rows.value.filter((row) => (row.sourceModule || '') === sourceModule.value)
})
const emptyText = computed(() => {
  if (error.value) return error.value
  if (sourceModule.value) return `来源 ${sourceModule.value} 暂无消息`
  if (filters.channel === 'DINGTALK') return '没有钉钉消息'
  if (filters.channel === 'IN_APP') return '没有站内消息'
  if (filters.keyword.trim()) return '没有匹配的消息'
  return '暂无消息'
})
const emptyHint = computed(() => {
  if (filters.channel || filters.keyword.trim()) return '换一个类型或关键词再查。站内与钉钉分开展示。'
  return '未读消息会列在这里。'
})

function channelLabel(value?: string) {
  if (value === 'DINGTALK') return '钉钉'
  if (value === 'IN_APP') return '站内'
  return value || '站内'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 }
    if (filters.read === 'true') params.read = true
    if (filters.read === 'false') params.read = false
    if (filters.channel) params.channel = filters.channel
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    const res = await http.get('/auth/workbench/messages', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data?.list || []
    total.value = Number(res.data.data?.total || 0)
  } catch {
    error.value = '网络错误'
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  detailOpen.value = false
  load()
}

function openDetail(row: Row) {
  detail.value = row
  detailOpen.value = true
}

async function readOne(id: number) {
  await http.put(`/auth/workbench/messages/${id}/read`)
  if (detail.value?.id === id) detail.value = { ...detail.value, read: true }
  notifyInboxChanged()
  await load()
}

async function readAll() {
  await http.put('/auth/workbench/messages/read-all')
  detailOpen.value = false
  notifyInboxChanged()
  await load()
}

onMounted(load)
</script>
