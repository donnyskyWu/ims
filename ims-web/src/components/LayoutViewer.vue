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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { hasVisibleLayout, renderLayoutHtml } from '../content/layoutViewer'

const props = defineProps<{ html?: string; plain?: string; loading?: boolean }>()
const host = ref<HTMLElement | null>(null)

const showHtml = computed(() => !props.loading && hasVisibleLayout(props.html || ''))
const plainText = computed(() => (props.plain || '').trim())

async function paint() {
  await nextTick()
  if (host.value && showHtml.value) renderLayoutHtml(host.value, props.html || '')
}

watch(() => [props.html, props.loading, showHtml.value], paint)
onMounted(paint)
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
