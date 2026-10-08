<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>作品监测</h1>
        <div class="sub">IP 主题/行业 · oa_external_account/work · 18 MON</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/int/work')">内部作品</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/comp/work')">竞品作品</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      内部作品/账号 → <b>内部分析</b>；外部竞品 → <b>竞品分析</b>；本页仅 IP 主题/行业聚合（UX-M7）。
    </p>
    <div class="cattabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="cattab"
        :class="{ on: dimension === tab.value }"
        @click="switchDimension(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.keyword" :placeholder="dimension === 'IP_THEME' ? 'IP 主题' : '行业'" style="width: 150px" />
      <select v-model="filters.platformType" style="width: 108px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="XIAOHONGSHU">小红书</option>
      </select>
      <input v-model.number="filters.ipGroupId" type="number" placeholder="IP 组 id" style="width: 108px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">聚合行数</span><div class="n">{{ total }}</div></div>
      <div class="card stat"><span class="l">维度</span><div class="n" style="font-size: 14px">{{ dimensionLabel }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ dimension === 'IP_THEME' ? 'IP 主题' : '行业' }}</th>
              <th>外部账号数</th>
              <th>作品数</th>
              <th>爆款数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="4"><div class="empty"><div class="et">{{ error || '暂无监测数据' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.dimensionKey">
              <td style="font-weight: 500">{{ row.dimensionLabel }}</td>
              <td class="num">{{ row.externalAccountCount }}</td>
              <td class="num">{{ row.workCount }}</td>
              <td class="num">{{ row.hitCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()
const tabs = [
  { value: 'IP_THEME', label: 'IP 主题' },
  { value: 'INDUSTRY', label: '行业' },
]
const dimension = ref('IP_THEME')
const rows = ref<
  {
    dimensionKey: string
    dimensionLabel: string
    externalAccountCount: number
    workCount: number
    hitCount: number
  }[]
>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const filters = reactive({ platformType: '', ipGroupId: null as number | null, keyword: '' })

const dimensionLabel = computed(() => (dimension.value === 'IP_THEME' ? 'IP 主题' : '行业'))

function go(path: string) {
  router.push(path)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const path = dimension.value === 'IP_THEME' ? '/monitor/ip-theme/page' : '/monitor/industry/page'
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 20 }
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.ipGroupId) params.ipGroupId = filters.ipGroupId
    if (filters.keyword) params.keyword = filters.keyword
    const res = await http.get(path, { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      total.value = 0
      return
    }
    rows.value = res.data.data.list || []
    total.value = res.data.data.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function switchDimension(value: string) {
  dimension.value = value
  loadList()
}

function resetFilters() {
  filters.platformType = ''
  filters.ipGroupId = null
  filters.keyword = ''
  loadList()
}

onMounted(loadList)
</script>
