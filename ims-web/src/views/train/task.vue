<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>学习任务管理</h1>
        <div class="sub">TRAIN-002 · 资料多选 · DURATION/QUIZ · 02 TRAIN</div>
      </div>
      <div class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">下达学习任务</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      从已发布资料多选关联；按人指派；完成率 = 已完成人次 / 应完成人次（BR-102）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.taskName" placeholder="任务名称" style="width: 140px" />
      <select v-model="filters.status" style="width: 100px">
        <option value="">全部状态</option>
        <option value="IN_PROGRESS">进行中</option>
        <option value="FINISHED">已结束</option>
      </select>
      <select v-model="filters.confirmType" style="width: 110px">
        <option value="">确认方式</option>
        <option value="DURATION">学时达标</option>
        <option value="QUIZ">自测问卷</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
    </form>

    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>编号</th>
              <th>任务名称</th>
              <th>资料数</th>
              <th>应完成</th>
              <th>完成率</th>
              <th>确认方式</th>
              <th>截止时间</th>
              <th>状态</th>
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
              <td class="mono">{{ row.taskNo }}</td>
              <td style="font-weight: 500">{{ row.taskName }}</td>
              <td class="num">{{ row.materialCount }}</td>
              <td class="num">{{ row.assignedCount }}</td>
              <td :style="{ color: finishColor(row.finishRate) }">{{ row.finishRate }}%</td>
              <td>{{ row.confirmType }}</td>
              <td class="mono">{{ row.deadline }}</td>
              <td>{{ row.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px; max-height: 90vh; overflow: auto">
        <h3 style="margin: 0 0 12px">下达学习任务</h3>
        <label class="fld">任务名称</label>
        <input v-model="form.taskName" class="fld-in" />
        <label class="fld">资料 ID（逗号分隔）</label>
        <input v-model="form.materialIdsText" class="fld-in" placeholder="如 1,2" />
        <label class="fld">指派用户 ID（逗号）</label>
        <input v-model="form.userIdsText" class="fld-in" placeholder="如 1" />
        <label class="fld">截止时间 ISO</label>
        <input v-model="form.deadline" class="fld-in" placeholder="2026-12-31T18:00:00+08:00" />
        <label class="fld">确认方式</label>
        <select v-model="form.confirmType" class="fld-in">
          <option value="DURATION">DURATION</option>
          <option value="QUIZ">QUIZ</option>
        </select>
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submit">保存</button>
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
  taskNo: string
  taskName: string
  materialCount: number
  assignedCount: number
  finishRate: number
  confirmType: string
  deadline: string
  status: string
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ taskName: '', status: '', confirmType: '' })
const form = reactive({
  taskName: '',
  materialIdsText: '',
  userIdsText: '1',
  deadline: '2026-12-31T18:00:00+08:00',
  confirmType: 'DURATION',
})

function finishColor(rate: number) {
  if (rate >= 90) return 'var(--green)'
  if (rate >= 70) return 'var(--orange, #e6a700)'
  return 'var(--red)'
}

function parseIds(text: string): number[] {
  return text
    .split(/[,，\s]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n > 0)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 30 }
    if (filters.taskName) params.taskName = filters.taskName
    if (filters.status) params.status = filters.status
    if (filters.confirmType) params.confirmType = filters.confirmType
    const res = await http.get('/train/task/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch {
    error.value = '网络错误'
    rows.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.taskName = ''
  form.materialIdsText = ''
  form.userIdsText = '1'
  form.deadline = '2026-12-31T18:00:00+08:00'
  form.confirmType = 'DURATION'
  formError.value = ''
  showForm.value = true
}

async function submit() {
  formError.value = ''
  const materialIds = parseIds(form.materialIdsText)
  const userIds = parseIds(form.userIdsText)
  if (!form.taskName.trim() || !materialIds.length || !userIds.length) {
    formError.value = '名称、资料与用户必填'
    return
  }
  const res = await http.post('/train/task', {
    taskName: form.taskName.trim(),
    materialIds,
    assignScope: 'BY_USER',
    assignTargetUserIds: userIds,
    deadline: form.deadline,
    confirmType: form.confirmType,
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || `失败 (${res.data.code})`
    return
  }
  showForm.value = false
  await loadList()
}

onMounted(loadList)
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
}
.fld {
  display: block;
  font-size: 12px;
  color: var(--text2);
  margin: 8px 0 4px;
}
.fld-in {
  width: 100%;
  box-sizing: border-box;
}
</style>
