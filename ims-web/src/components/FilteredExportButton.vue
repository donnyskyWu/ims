<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage, http } from '../api/http'

const props = defineProps<{
  url: string
  params?: Record<string, unknown>
  testId?: string
}>()
const emit = defineEmits<{ done: [message: string]; error: [message: string] }>()
const busy = ref(false)

async function run() {
  busy.value = true
  try {
    const res = await http.get(props.url, { params: props.params })
    const data = (res.data?.data || {}) as { downloadUrl?: string; fileName?: string; message?: string }
    const downloadUrl = String(data.downloadUrl || '')
    if (!downloadUrl) throw new Error('没有下载地址')
    const fileRes = await fetch(downloadUrl, {
      headers: { Authorization: `Bearer ${localStorage.getItem('ims_access') || ''}` },
    })
    if (!fileRes.ok) throw new Error('下载失败')
    const blob = await fileRes.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = String(data.fileName || 'export.csv')
    link.click()
    URL.revokeObjectURL(link.href)
    emit('done', String(data.message || '导出已生成'))
  } catch (error) {
    emit('error', errorMessage(error))
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button class="btn btn-sec btn-sm" type="button" :data-testid="testId" :disabled="busy" @click="run">导出</button>
</template>
