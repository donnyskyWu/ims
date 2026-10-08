<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>培训统计看板</h1>
        <div class="sub">TRAIN-003 · 完成率汇总 · 02 TRAIN</div>
      </div>
      <router-link class="btn btn-sec btn-sm" to="/ims/train/task">学习任务</router-link>
    </div>
    <p class="hint"><code>/train/stat/summary</code> + 任务明细 · BR-102 完成率</p>
    <div class="g3" style="margin: 12px 0">
      <div class="card stat"><span class="l">任务数</span><div class="n">{{ summary.taskCount }}</div></div>
      <div class="card stat"><span class="l">进行中</span><div class="n">{{ summary.inProgress }}</div></div>
      <div class="card stat"><span class="l">平均完成率</span><div class="n">{{ summary.avgRate }}%</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>应完成</th>
              <th>完成率</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ row.taskName }}</td>
              <td class="num">{{ row.assignedCount }}</td>
              <td class="num">{{ row.finishRate }}%</td>
              <td>{{ row.status }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="4"><div class="empty"><div class="et">{{ error || '暂无任务' }}</div></div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Row = { id: number; taskName: string; assignedCount: number; finishRate: number; status: string }

const rows = ref<Row[]>([])
const error = ref('')

const summary = ref({ taskCount: 0, inProgress: 0, avgRate: 0 })

onMounted(async () => {
  try {
    const sum = await http.get('/train/stat/summary')
    if (sum.data.code === 0) {
      summary.value = {
        taskCount: sum.data.data.taskCount,
        inProgress: sum.data.data.inProgress,
        avgRate: sum.data.data.avgFinishRate,
      }
    }
    const res = await http.get('/train/task/list', { params: { pageNo: 1, pageSize: 50 } })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    error.value = '网络错误'
  }
})
</script>
