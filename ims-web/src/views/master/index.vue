<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>主数据台账</h1>
        <div class="sub">MASTER · GET /master/overview · 跳转资源管理</div>
      </div>
    </div>
    <p v-if="error" class="hint">{{ error }}</p>
    <div v-else-if="loading" class="empty"><div class="et">加载中</div></div>
    <div v-else class="g3">
      <router-link v-for="b in blocks" :key="b.key" class="card il" :to="b.href" style="padding: 16px">
        <b>{{ b.label }}</b>
        <span class="num" style="display: block; margin-top: 8px; font-size: 22px">{{ b.count }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Block = { key: string; label: string; count: number; href: string }

const blocks = ref<Block[]>([])
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const res = await http.get('/master/overview')
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      return
    }
    blocks.value = res.data.data.blocks || []
  } catch {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
})
</script>
