<template>
  <p v-if="loading" class="hint">正文加载中</p>
  <template v-else-if="showHtml">
    <p class="hint" data-layout-mode="html">只读版式（含图片预览）</p>
    <div ref="host" class="layout-viewer" data-layout-viewer contenteditable="false" />
  </template>
  <template v-else-if="plainText">
    <p class="hint" data-layout-mode="plain">只读纯文本</p>
    <pre class="layout-plain" data-layout-plain>{{ plainText }}</pre>
  </template>
  <p v-else class="hint" data-layout-mode="empty">暂无正文</p>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { hasVisibleLayout, renderLayoutHtml } from '../content/layoutViewer'

const props = defineProps<{ html?: string; plain?: string; loading?: boolean }>()
const host = ref<HTMLElement | null>(null)
const blobUrls: string[] = []

const showHtml = computed(() => !props.loading && hasVisibleLayout(props.html || ''))
const plainText = computed(() => (props.plain || '').trim())

function revokeBlobs() {
  while (blobUrls.length) {
    const url = blobUrls.pop()
    if (url) URL.revokeObjectURL(url)
  }
}

/** #110 写入的 layout_html 使用 /admin-api 文件地址，img 不会带 Bearer。 */
async function hydrateAuthedImages() {
  const root = host.value
  if (!root) return
  const token = localStorage.getItem('ims_access')
  const imgs = [...root.querySelectorAll('img')]
  await Promise.all(
    imgs.map(async (img) => {
      const src = img.getAttribute('src') || ''
      if (!src.startsWith('/admin-api/')) return
      const res = await fetch(src, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      blobUrls.push(url)
      img.src = url
    }),
  )
}

async function paint() {
  revokeBlobs()
  await nextTick()
  if (host.value && showHtml.value) {
    renderLayoutHtml(host.value, props.html || '')
    await hydrateAuthedImages()
  }
}

watch(() => [props.html, props.loading, showHtml.value], paint)
onMounted(paint)
onBeforeUnmount(revokeBlobs)
</script>

<style scoped>
.layout-viewer,
.layout-plain {
  width: 677px;
  max-width: 100%;
  box-sizing: border-box;
  margin: 8px 0 0;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fafafc;
  color: var(--text);
  font-size: 14px;
  line-height: 1.65;
  overflow: auto;
}
.layout-viewer {
  min-height: 72px;
}
.layout-viewer :deep(img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 8px 0;
}
.layout-viewer :deep(a) {
  pointer-events: none;
  color: inherit;
  text-decoration: none;
}
.layout-plain {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
</style>
