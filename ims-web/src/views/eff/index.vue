<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>组织人效</h1>
        <div class="sub">EFF · 页内 Tab 归属/盘点/看板 · /ims/eff</div>
      </div>
      <div v-if="tab === 'relation'" class="acts">
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">建立归属</button>
      </div>
    </div>

    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'relation' }" @click="switchTab('relation')">归属关系</div>
      <div class="tab" :class="{ on: tab === 'inventory' }" @click="switchTab('inventory')">人效盘点</div>
      <div class="tab" :class="{ on: tab === 'board' }" @click="switchTab('board')">人效看板</div>
    </div>

    <div v-if="coverage && tab === 'relation'" class="g4" style="margin: 12px 0">
      <div class="card stat">
        <span class="l">在职人数</span>
        <div class="n">{{ coverage.enabledUserCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">已覆盖主归属</span>
        <div class="n">{{ coverage.coveredUserCount }}</div>
      </div>
      <div class="card stat">
        <span class="l">覆盖率</span>
        <div class="n">{{ coverage.coverageRate }}%</div>
        <div class="d">{{ coverage.canPublish ? '可发布盘点' : '未达 100%' }}</div>
      </div>
    </div>

    <template v-if="tab === 'relation'">
      <form class="qbar" @submit.prevent="loadRelations">
        <input v-model.number="filters.userId" type="number" placeholder="用户 ID" style="width: 100px" />
        <select v-model="filters.relationType" style="width: 110px">
          <option value="">全部类型</option>
          <option value="PRIMARY">主归属</option>
          <option value="PART_TIME">兼职</option>
        </select>
        <span class="sp"></span>
        <button class="btn btn-pri btn-sm" type="submit">查询</button>
      </form>
      <div class="tbl-block">
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>用户</th>
                <th>类型</th>
                <th>归属目标</th>
                <th>分摊%</th>
                <th>生效自</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading"><td colspan="6"><div class="empty"><div class="et">加载中</div></div></td></tr>
              <tr v-else-if="!relations.length"><td colspan="6"><div class="empty"><div class="et">暂无归属</div></div></td></tr>
              <tr v-for="row in relations" v-else :key="row.id">
                <td>{{ row.userName || row.userId }}</td>
                <td>{{ row.relationType }}</td>
                <td>{{ row.targetName }}</td>
                <td class="num">{{ row.shareRatio }}%</td>
                <td>{{ row.effectiveFrom }}</td>
                <td>{{ row.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <template v-else-if="tab === 'inventory'">
      <div v-if="inventory" class="g4" style="margin-top: 12px">
        <div class="card stat"><span class="l">周期</span><div class="n mono">{{ inventory.period }}</div></div>
        <div class="card stat"><span class="l">覆盖率</span><div class="n">{{ inventory.coverageRate }}%</div></div>
        <div class="card stat"><span class="l">状态</span><div class="n">{{ inventory.status }}</div></div>
        <div class="card stat"><span class="l">可发布</span><div class="n">{{ inventory.canPublish ? '是' : '否' }}</div></div>
      </div>
      <div class="card hint" style="padding: 16px; margin-top: 12px">{{ inventory?.note || '加载中…' }}</div>
    </template>

    <template v-else>
      <div v-if="board" class="g4" style="margin-top: 12px">
        <div class="card stat"><span class="l">人均 GMV</span><div class="n">¥{{ (board.avgGmvPerCap / 10000).toFixed(1) }} 万</div></div>
        <div class="card stat"><span class="l">人均场次/月</span><div class="n">{{ board.avgSessionsPerMonth }}</div></div>
        <div class="card stat"><span class="l">人均作品/月</span><div class="n">{{ board.avgWorksPerMonth }}</div></div>
        <div class="card stat"><span class="l">产能利用率</span><div class="n">{{ board.capacityUtilization }}%</div><div class="d">分摊&gt;100% {{ board.overShareUserCount }} 人</div></div>
      </div>
    </template>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="card" style="width: 420px; padding: 20px">
        <h3 style="margin: 0 0 12px">建立归属</h3>
        <label class="fld">用户 ID</label>
        <input v-model.number="form.userId" class="fld-in" type="number" />
        <label class="fld">类型</label>
        <select v-model="form.relationType" class="fld-in">
          <option value="PRIMARY">主归属</option>
          <option value="PART_TIME">兼职</option>
        </select>
        <label class="fld">目标名称</label>
        <input v-model="form.targetName" class="fld-in" />
        <label class="fld">分摊比例</label>
        <input v-model.number="form.shareRatio" class="fld-in" type="number" />
        <p v-if="formError" class="hint" style="color: var(--red)">{{ formError }}</p>
        <div class="acts" style="margin-top: 12px; justify-content: flex-end">
          <button class="btn btn-sec btn-sm" type="button" @click="showForm = false">取消</button>
          <button class="btn btn-pri btn-sm" type="button" @click="submitCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '../../api/http'

type Relation = {
  id: number
  userId: number
  userName: string
  relationType: string
  targetName: string
  shareRatio: number
  effectiveFrom: string
  status: string
}

const route = useRoute()
const router = useRouter()
const tab = ref('board')
const relations = ref<Relation[]>([])
const loading = ref(false)
const coverage = ref<{ enabledUserCount: number; coveredUserCount: number; coverageRate: number; canPublish: boolean } | null>(null)
const board = ref<Record<string, number> | null>(null)
const inventory = ref<{
  period: string
  coverageRate: number
  status: string
  canPublish: boolean
  note: string
} | null>(null)
const showForm = ref(false)
const formError = ref('')
const filters = reactive({ userId: undefined as number | undefined, relationType: '' })
const form = reactive({
  userId: 1,
  relationType: 'PRIMARY',
  targetName: '默认 IP 组',
  targetId: 1,
  shareRatio: 100,
})

function tabFromRoute() {
  const q = String(route.query.tab || '')
  if (q === 'relation' || route.path.includes('relation')) return 'relation'
  if (q === 'inventory') return 'inventory'
  return 'board'
}

function switchTab(name: string) {
  tab.value = name
  router.replace({ path: '/ims/eff', query: name === 'board' ? {} : { tab: name } })
  if (name === 'relation') loadRelations()
  if (name === 'board') loadBoard()
  if (name === 'inventory') loadInventory()
}

async function loadCoverage() {
  const res = await http.get('/eff/relation/coverage')
  if (res.data.code === 0) coverage.value = res.data.data
}

async function loadRelations() {
  loading.value = true
  try {
    const res = await http.get('/eff/relation/list', {
      params: {
        pageNo: 1,
        pageSize: 20,
        userId: filters.userId || undefined,
        relationType: filters.relationType || undefined,
      },
    })
    if (res.data.code === 0) relations.value = res.data.data.list || []
  } finally {
    loading.value = false
  }
}

async function loadBoard() {
  const res = await http.get('/eff/metrics/board')
  if (res.data.code === 0) board.value = res.data.data
}

async function loadInventory() {
  const res = await http.get('/eff/inventory/snapshot')
  if (res.data.code === 0) inventory.value = res.data.data
}

function openCreate() {
  formError.value = ''
  showForm.value = true
}

async function submitCreate() {
  formError.value = ''
  const res = await http.post('/eff/relation', {
    userId: form.userId,
    relationType: form.relationType,
    targetType: 'IP_GROUP',
    targetId: form.targetId,
    targetName: form.targetName,
    shareRatio: form.shareRatio,
  })
  if (res.data.code !== 0) {
    formError.value = res.data.msg || '保存失败'
    return
  }
  showForm.value = false
  await loadCoverage()
  await loadRelations()
}

watch(
  () => route.fullPath,
  () => {
    tab.value = tabFromRoute()
  },
  { immediate: true }
)

onMounted(async () => {
  tab.value = tabFromRoute()
  await loadCoverage()
  if (tab.value === 'relation') await loadRelations()
  else if (tab.value === 'inventory') await loadInventory()
  else await loadBoard()
})
</script>
