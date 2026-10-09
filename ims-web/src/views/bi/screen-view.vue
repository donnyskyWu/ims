<template>
  <div class="screen-full">
    <div class="top">
      <b>{{ title }}</b>
      <span class="sub">{{ refreshedAt }}</span>
      <router-link class="btn btn-sec btn-sm" to="/ims/bi/screen-config">退出全屏</router-link>
    </div>
    <div v-if="loading" class="empty"><div class="et">加载中</div></div>
    <div v-else-if="gate" class="empty" data-testid="bi-screen-gate"><div class="et">{{ gate }}</div></div>
    <div v-else-if="!widgets.length" class="empty" data-testid="bi-screen-view-empty">
      <div class="et">{{ emptyReason }}</div>
    </div>
    <div v-else class="grid">
      <div v-for="(w, i) in widgets" :key="i" class="tile" :class="w.type">
        <div class="k">{{ w.title }}</div>
        <div v-if="w.type === 'KPI'" class="v">{{ w.value }}<small>{{ w.unit }}</small></div>
        <div v-else class="ph">{{ w.type }} · 演示数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage, http } from '../../api/http'

const route = useRoute()
const loading = ref(true)
const title = ref('数据大屏')
const refreshedAt = ref('')
const widgets = ref<Record<string, unknown>[]>([])
const gate = ref('')
const emptyReason = ref('暂无组件')

onMounted(async () => {
  const id = route.params.id
  try {
    const res = await http.get(`/bi/screen/${id}/preview`)
    if (res.data.code === 0) {
      title.value = res.data.data.reportName
      refreshedAt.value = res.data.data.refreshedAt
      widgets.value = res.data.data.widgets || []
      emptyReason.value = String(res.data.data.emptyReason || '暂无组件')
    }
  } catch (error: unknown) {
    const msg = errorMessage(error)
    gate.value = msg === '您无权查看该报表' ? '您无权查看该报表' : msg || '大屏不存在'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.screen-full {
  min-height: calc(100vh - 48px);
  background: #0b0b0f;
  color: #f5f5f7;
  padding: 16px 20px;
}
.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.sub {
  font-size: 12px;
  opacity: 0.6;
  flex: 1;
}
.empty .et {
  color: #f5f5f7;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.tile {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 16px;
  min-height: 100px;
}
.k {
  font-size: 12px;
  opacity: 0.65;
}
.v {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
}
.ph {
  margin-top: 12px;
  opacity: 0.7;
  font-size: 13px;
}
</style>
