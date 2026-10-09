<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>主数据台账</h1>
        <div class="sub">公司 / 实名人 / 手机 / 卡 / 证件 · 点卡片进入台账</div>
        <div v-if="updatedAt" class="sub" data-testid="master-overview-updated">更新于 {{ updatedAt }}（北京时间）</div>
      </div>
    </div>
    <p v-if="error" class="hint">{{ error }}</p>
    <div v-else-if="loading" class="empty"><div class="et">加载中</div></div>
    <div v-else-if="!blocks.length" class="empty" data-testid="master-overview-empty">
      <div class="et">暂无主数据汇总</div>
      <div class="es">台账块没有返回。刷新后再看公司、实名人和账号。</div>
    </div>
    <div v-else class="g3">
      <router-link v-for="b in blocks" :key="b.key" class="card il hov" :to="b.href" style="padding: 16px">
        <b>{{ b.label }}</b>
        <span class="num" style="display: block; margin-top: 8px; font-size: 22px">{{ b.count }}</span>
        <span class="csub" style="display: block; margin-top: 6px">{{ hintOf(b.key) }}</span>
        <span v-if="b.count === 0" class="es" data-testid="master-zero" style="display: block; margin-top: 4px">暂无记录，仍可进入台账</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { http } from '../../api/http'

type Block = { key: string; label: string; count: number; href: string }

const hints: Record<string, string> = {
  company: '公司主体与公众号容量',
  realname: '实名人台账',
  sim: '手机卡',
  certificate: '证件档案',
  phone: '工作手机',
  platformAccount: '平台账号',
}

const blocks = ref<Block[]>([])
const loading = ref(false)
const error = ref('')
const updatedAt = ref('')

function hintOf(key: string) {
  return hints[key] || '进入对应台账'
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await http.get('/master/overview')
    if (res.data.code !== 0) {
      error.value = res.data.msg || '加载失败'
      return
    }
    const data = res.data.data || {}
    blocks.value = data.blocks || []
    updatedAt.value = String(data.updatedAt || '')
  } catch {
    error.value = '网络错误'
  } finally {
    loading.value = false
  }
})
</script>
