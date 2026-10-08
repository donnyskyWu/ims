<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>内部账号</h1>
        <div class="sub">Tab：全部/高粉/低粉 · oa_internal_account · 18b INT</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/collect/threshold')">阈值规则</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/corp/account/douyin')">平台账号</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/int/work')">内部作品</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      高粉默认粉丝 ≥10w · 低粉 &lt;1000 · 阈值只读引用 COLLECT FANS 规则。
    </p>
    <div class="cattabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="cattab"
        :class="{ on: segment === tab.value }"
        @click="switchSegment(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>
    <form class="qbar" @submit.prevent="loadList">
      <select v-model="filters.platformType" style="width: 110px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="WECHAT_CHANNELS">视频号</option>
      </select>
      <input v-model.number="filters.ipGroupId" type="number" placeholder="IP 组 id" style="width: 110px" />
      <input v-model="filters.keyword" placeholder="账号名称" style="width: 140px" />
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div class="g4" style="margin: 12px 0">
      <div class="card stat"><span class="l">当前 Tab 账号</span><div class="n">{{ total }}</div></div>
      <div class="card stat"><span class="l">segment</span><div class="n" style="font-size: 14px">{{ segment }}</div></div>
    </div>
    <div class="tbl-block">
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>账号名称</th>
              <th>平台</th>
              <th>IP 组</th>
              <th>粉丝数</th>
              <th>作品数</th>
              <th>标签</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6"><div class="empty"><div class="et">加载中</div></div></td>
            </tr>
            <tr v-else-if="!rows.length">
              <td colspan="6"><div class="empty"><div class="et">{{ error || '暂无内部账号' }}</div></div></td>
            </tr>
            <tr v-for="row in rows" v-else :key="row.id">
              <td style="font-weight: 500">{{ row.accountName }}</td>
              <td>{{ row.platformType }}</td>
              <td>{{ row.ipGroupName || '—' }}</td>
              <td class="num">{{ formatFans(row.followerCount) }}</td>
              <td class="num">{{ row.contentCount }}</td>
              <td>
                <span v-if="row.isHighFans" class="tag" style="background: rgba(255, 149, 0, 0.12); color: #c46a00">高粉</span>
                <span
                  v-else-if="row.isLowFans"
                  class="tag"
                  style="background: rgba(142, 142, 147, 0.12); color: #6d6d72"
                >低粉</span>
                <span v-else class="tag" style="background: rgba(52, 199, 89, 0.12); color: #1e8e3e">正常</span>
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

const router = useRouter()
const tabs = [
  { value: 'ALL', label: '全部' },
  { value: 'HIGH_FANS', label: '高粉' },
  { value: 'LOW_FANS', label: '低粉' },
]
const segment = ref('ALL')
const rows = ref<
  {
    id: string
    accountName: string
    platformType: string
    ipGroupName: string
    followerCount: number
    contentCount: number
    isHighFans: boolean
    isLowFans: boolean
  }[]
>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const filters = reactive({ platformType: '', ipGroupId: null as number | null, keyword: '' })

function go(path: string) {
  router.push(path)
}

function formatFans(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(1)}w`
  return String(n)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {
      segment: segment.value,
      pageNo: 1,
      pageSize: 20,
    }
    if (filters.platformType) params.platformType = filters.platformType
    if (filters.ipGroupId) params.ipGroupId = filters.ipGroupId
    if (filters.keyword) params.keyword = filters.keyword
    const res = await http.get('/int-analysis/account/page', { params })
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

function switchSegment(value: string) {
  segment.value = value
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
