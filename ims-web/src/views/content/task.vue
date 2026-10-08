<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>我的任务</h1>
        <div class="sub">任务分页 · 执行 / 完成（CONTENT-103 · ADR-079）</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="loadList">刷新</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 10px">
      契约：<code>/admin-api/ims/content/task/page</code> · 执行页隐藏路由
      <code>/ims/content/task/:id/execute</code>
    </p>
    <div class="tabs">
      <div class="tab" :class="{ on: onlyMine }" @click="onlyMine = true; loadList()">我的任务</div>
      <div class="tab" :class="{ on: !onlyMine }" @click="onlyMine = false; loadList()">全部任务</div>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model.number="ipGroupId" type="number" placeholder="IP 组 id" style="width: 100px" />
      <input v-model="statusKw" placeholder="状态" style="width: 120px" />
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>任务号</th>
              <th>节点</th>
              <th>IP 组</th>
              <th>赛事</th>
              <th>执行人</th>
              <th>状态</th>
              <th>关联内容</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="8"><div class="empty"><div class="et">{{ error || '暂无任务' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td class="mono">{{ row.id }}</td>
              <td>{{ row.nodeName }}</td>
              <td>{{ row.ipGroupName || row.ipGroupId }}</td>
              <td>{{ row.competitionName || '—' }}</td>
              <td>{{ row.assigneeName }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.linkedContent?.status || '—' }}</td>
              <td>
                <button class="btn btn-pri btn-sm" type="button" @click="goExecute(row.id)">执行</button>
                <button
                  v-if="row.status === 'IN_PROGRESS' || row.status === 'PENDING'"
                  class="btn btn-sec btn-sm"
                  type="button"
                  style="margin-left: 6px"
                  @click="quickComplete(row)"
                >
                  完成
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
import { useRouter } from 'vue-router'
import { http, errorMessage } from '../../api/http'

const router = useRouter()
const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const onlyMine = ref(true)
const ipGroupId = ref<number | undefined>()
const statusKw = ref('')

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = {
      pageNo: 1,
      pageSize: 50,
      onlyMine: onlyMine.value,
    }
    if (ipGroupId.value) params.ipGroupId = ipGroupId.value
    if (statusKw.value.trim()) params.status = statusKw.value.trim()
    const { data } = await http.get('/content/task/page', { params })
    rows.value = data.data?.list || []
    total.value = data.data?.total || 0
  } catch (e) {
    error.value = errorMessage(e)
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function goExecute(id: number) {
  router.push(`/ims/content/task/${id}/execute`)
}

async function quickComplete(row: any) {
  const deliverables =
    row.nodeType === 'CONTENT_GENERATION' ? undefined : window.prompt('工作说明（必填）', '') || ''
  if (row.nodeType !== 'CONTENT_GENERATION' && !String(deliverables).trim()) {
    window.alert('非内容生成节点须填写工作说明')
    return
  }
  try {
    await http.put(`/content/task/${row.id}/complete`, {
      deliverables: deliverables || undefined,
    })
    await loadList()
  } catch (e) {
    window.alert(errorMessage(e))
  }
}

loadList()
</script>
