<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>学习中心</h1>
        <div class="sub">TRAIN-002 · 任务 #{{ taskId }} · 学习执行</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="router.push('/ims/train/task')">返回任务列表</button>
      </div>
    </div>

    <p v-if="loadError" class="hint" style="color: var(--red)">{{ loadError }}</p>
    <div v-else-if="task" class="g2">
      <div class="card head">
        <div style="font-weight: 600; font-size: 16px">{{ task.taskName }}</div>
        <div class="meta">编号 {{ task.taskNo }} · 截止 {{ task.deadline }} · {{ task.confirmType }}</div>
        <div class="meta">
          总进度 <strong>{{ progressPct }}%</strong>
          · 确认状态
          <span :class="confirmStatus === 'CONFIRMED' ? 'ok' : 'pending'">{{ confirmStatusLabel }}</span>
        </div>
      </div>

      <div class="card" style="padding: 12px">
        <div style="font-weight: 600; margin-bottom: 8px">资料清单</div>
        <ul v-if="materials.length" class="mat-list">
          <li v-for="m in materials" :key="m.id">
            <span>{{ m.title }}</span>
            <span class="mono">{{ materialPct(m.id) }}%</span>
          </li>
        </ul>
        <div v-else class="empty"><div class="et">无关联资料</div></div>

        <div v-if="materials.length && confirmStatus !== 'CONFIRMED'" class="acts" style="margin-top: 16px; flex-wrap: wrap; gap: 8px">
          <button class="btn btn-sec btn-sm" type="button" :disabled="busy" @click="markCurrentMaterialDone">
            标记当前资料已学完
          </button>
          <button
            class="btn btn-pri btn-sm"
            type="button"
            :disabled="busy || !allMaterialsDone"
            :title="allMaterialsDone ? '' : '请先完成全部资料学习'"
            @click="confirmComplete"
          >
            完成确认
          </button>
        </div>
        <p v-if="actionError" class="hint" style="color: var(--red); margin-top: 8px">{{ actionError }}</p>
        <p v-if="confirmStatus === 'CONFIRMED'" class="hint ok-banner">学习已完成 · CONFIRMED</p>
      </div>
    </div>
    <div v-else class="empty"><div class="et">加载中…</div></div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'
import { useUserStore } from '../../stores/user'

type TaskRow = {
  id: number
  taskNo: string
  taskName: string
  materialIds: number[]
  deadline: string
  confirmType: string
}

type MatRow = { id: number; title: string; materialType: string }

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.taskId))
const task = ref<TaskRow | null>(null)
const materials = ref<MatRow[]>([])
const materialProgress = ref<Record<number, number>>({})
const progressPct = ref(0)
const confirmStatus = ref<'NOT_CONFIRMED' | 'CONFIRMED'>('NOT_CONFIRMED')
const loadError = ref('')
const actionError = ref('')
const busy = ref(false)
const activeMaterialId = ref(0)

const confirmStatusLabel = computed(() =>
  confirmStatus.value === 'CONFIRMED' ? '已确认' : '未确认',
)

const allMaterialsDone = computed(() => {
  if (!task.value?.materialIds?.length) return false
  return task.value.materialIds.every((id) => (materialProgress.value[id] ?? 0) >= 100)
})

function materialPct(id: number) {
  return materialProgress.value[id] ?? 0
}

function parseMatProgress(raw: Record<string, number> | undefined) {
  const out: Record<number, number> = {}
  if (!raw) return out
  for (const [k, v] of Object.entries(raw)) {
    out[Number(k)] = Number(v)
  }
  return out
}

async function loadTaskAndProgress() {
  loadError.value = ''
  const listRes = await http.get('/train/task/list', { params: { pageNo: 1, pageSize: 100 } })
  if (listRes.data.code !== 0) {
    loadError.value = listRes.data.msg || '任务加载失败'
    return
  }
  const found = (listRes.data.data.list || []).find((r: TaskRow) => r.id === taskId.value)
  if (!found) {
    loadError.value = '任务不存在或无权查看'
    return
  }
  task.value = found
  activeMaterialId.value = found.materialIds[0] ?? 0

  const matRes = await http.get('/train/material/list', {
    params: { status: 'PUBLISHED', pageNo: 1, pageSize: 100 },
  })
  if (matRes.data.code === 0) {
    const ids = new Set(found.materialIds)
    materials.value = (matRes.data.data.list || []).filter((m: MatRow) => ids.has(m.id))
  }

  const userStore = useUserStore()
  const uid = Number(userStore.profile?.userId || 0)
  const recParams: Record<string, number> = { taskId: taskId.value, pageNo: 1, pageSize: 1 }
  if (uid > 0) recParams.userId = uid
  const recRes = await http.get('/train/task/records', { params: recParams })
  if (recRes.data.code === 0 && recRes.data.data.list?.length) {
    const rec = recRes.data.data.list[0]
    materialProgress.value = parseMatProgress(rec.materialProgress)
    progressPct.value = rec.progress ?? 0
    confirmStatus.value = rec.confirmStatus === 'CONFIRMED' ? 'CONFIRMED' : 'NOT_CONFIRMED'
  }
}

async function markCurrentMaterialDone() {
  if (!task.value || !activeMaterialId.value) return
  actionError.value = ''
  busy.value = true
  try {
    const res = await http.put(`/train/task/${taskId.value}/progress`, {
      materialId: activeMaterialId.value,
      currentPage: 1,
      totalPages: 1,
      watchedSeconds: 60,
      heartbeatAt: new Date().toISOString(),
    })
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '进度上报失败'
      return
    }
    const data = res.data.data
    materialProgress.value = parseMatProgress(data.materialProgress)
    progressPct.value = data.progress ?? progressPct.value
  } catch {
    actionError.value = '网络错误'
  } finally {
    busy.value = false
  }
}

async function confirmComplete() {
  actionError.value = ''
  busy.value = true
  try {
    const res = await http.post(`/train/task/${taskId.value}/confirm`, {})
    if (res.data.code !== 0) {
      actionError.value = res.data.msg || '确认失败'
      return
    }
    confirmStatus.value = 'CONFIRMED'
    progressPct.value = 100
  } catch {
    actionError.value = '网络错误'
  } finally {
    busy.value = false
  }
}

onMounted(loadTaskAndProgress)
</script>

<style scoped>
.g2 {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.head {
  padding: 16px;
}
.meta {
  font-size: 13px;
  color: var(--text2);
  margin-top: 6px;
}
.mat-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 14px;
}
.mat-list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border, #eee);
}
.ok {
  color: var(--green);
  font-weight: 600;
}
.pending {
  color: var(--orange, #e6a700);
}
.ok-banner {
  margin-top: 12px;
  color: var(--green);
  font-weight: 600;
}
</style>
