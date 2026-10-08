<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>竞品库</h1>
        <div class="sub">V3 COMP-003 · BR-202 审核入库 · /ims/comp/library · 18a COMP</div>
      </div>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/comp/work')">竞品作品监测</button>
        <button class="btn btn-sec btn-sm" type="button" @click="go('/ims/comp/account')">竞品账号监测</button>
        <button class="btn btn-sec btn-sm" type="button" disabled>导出对比</button>
        <button class="btn btn-pri btn-sm" type="button" @click="openCreate">新增竞品</button>
      </div>
    </div>
    <p class="hint" style="margin-bottom: 8px">
      V3 COMP-003 · API <code>/admin-api/ims/comp/asset/*</code>（与 M7 comp-analysis 监测 BFF 分离 · 走查 #9）。
    </p>
    <form class="qbar" @submit.prevent="loadList">
      <input v-model="filters.compName" placeholder="竞品名称" style="width: 140px" />
      <select v-model="filters.platform" style="width: 120px">
        <option value="">全部平台</option>
        <option value="DOUYIN">抖音</option>
        <option value="KUAISHOU">快手</option>
        <option value="XIAOHONGSHU">小红书</option>
        <option value="WECHAT_CHANNELS">视频号</option>
      </select>
      <span class="sp"></span>
      <button class="btn btn-pri btn-sm" type="submit">查询</button>
      <button class="btn btn-sec btn-sm" type="button" @click="resetFilters">重置</button>
    </form>
    <div v-if="loading" class="empty" style="margin-top: 24px"><div class="et">加载中</div></div>
    <div v-else-if="error" class="empty" style="margin-top: 24px"><div class="et">{{ error }}</div></div>
    <div v-else-if="!rows.length" class="empty" style="margin-top: 24px"><div class="et">暂无竞品档案</div></div>
    <div v-else class="comp-grid">
      <div v-for="row in rows" :key="row.id" class="card hov">
        <div class="rowline" style="margin-bottom: 10px">
          <span class="av" style="background: linear-gradient(135deg, #0071e3, #5ac8fa)">{{ row.avatarInitial }}</span>
          <div style="min-width: 0">
            <b style="font-size: 14px; display: block; line-height: 1.3">{{ row.compName }}</b>
            <span style="font-size: 11.5px; color: var(--text2)">{{ platformLabel(row.platform) }} · 竞品</span>
          </div>
        </div>
        <div class="kv" style="grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 0">
          <div>
            <div class="k">粉丝数</div>
            <div class="v" style="font-size: 14px">{{ formatFans(row.followerCount) }}</div>
          </div>
          <div>
            <div class="k">近30天作品</div>
            <div class="v" style="font-size: 14px">{{ row.works30d }}</div>
          </div>
          <div>
            <div class="k">互动率</div>
            <div class="v" style="font-size: 14px; color: var(--blue)">{{ row.engagementRate }}%</div>
          </div>
        </div>
        <div class="rowline" style="margin-top: 12px; justify-content: space-between">
          <span style="font-size: 11.5px; color: var(--text2)">
            {{ row.featuredWorksIncluded ? '代表作品已收录' : '待关联监测账号' }}
          </span>
          <span style="font-size: 11px; color: var(--text2)">{{ row.assetNo }}</span>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="drawer-mask" @click.self="showCreate = false">
      <div class="drawer">
        <h3>新增竞品</h3>
        <form class="form-stack" @submit.prevent="submitCreate">
          <label>竞品名称<input v-model="createForm.compName" required /></label>
          <label>
            平台
            <select v-model="createForm.platform" required>
              <option value="DOUYIN">抖音</option>
              <option value="KUAISHOU">快手</option>
              <option value="XIAOHONGSHU">小红书</option>
              <option value="WECHAT_CHANNELS">视频号</option>
            </select>
          </label>
          <label>监测账号标识（可选）<input v-model="createForm.compAccountId" placeholder="与 COLLECT 外部账号一致" /></label>
          <div class="rowline" style="gap: 8px; margin-top: 12px">
            <button class="btn btn-pri btn-sm" type="submit" :disabled="creating">保存</button>
            <button class="btn btn-sec btn-sm" type="button" @click="showCreate = false">取消</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/http'

const router = useRouter()
type Row = {
  id: string
  assetNo: string
  compName: string
  platform: string
  avatarInitial: string
  followerCount: number
  works30d: number
  engagementRate: number
  featuredWorksIncluded: boolean
}

const rows = ref<Row[]>([])
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const creating = ref(false)
const filters = reactive({ compName: '', platform: '' })
const createForm = reactive({ compName: '', platform: 'DOUYIN', compAccountId: '' })

const platformLabels: Record<string, string> = {
  DOUYIN: '抖音',
  KUAISHOU: '快手',
  XIAOHONGSHU: '小红书',
  WECHAT_CHANNELS: '视频号',
}

function platformLabel(code: string) {
  return platformLabels[code] || code
}

function go(path: string) {
  router.push(path)
}

function formatFans(n: number) {
  if (n >= 10_000) return `${(n / 10_000).toFixed(n >= 1_000_000 ? 0 : 1)} 万`
  return String(n)
}

async function loadList() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { pageNo: 1, pageSize: 24 }
    if (filters.compName) params.compName = filters.compName
    if (filters.platform) params.platform = filters.platform
    const res = await http.get('/comp/asset/list', { params })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      rows.value = []
      return
    }
    rows.value = res.data.data.list || []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.compName = ''
  filters.platform = ''
  loadList()
}

function openCreate() {
  createForm.compName = ''
  createForm.platform = 'DOUYIN'
  createForm.compAccountId = ''
  showCreate.value = true
}

async function submitCreate() {
  creating.value = true
  try {
    const res = await http.post('/comp/asset', {
      compName: createForm.compName,
      platform: createForm.platform,
      compAccountId: createForm.compAccountId,
    })
    if (res.data.code !== 0) {
      error.value = res.data.msg || '创建失败'
      return
    }
    showCreate.value = false
    await loadList()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '网络错误'
  } finally {
    creating.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.comp-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 12px;
}
@media (max-width: 1200px) {
  .comp-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
