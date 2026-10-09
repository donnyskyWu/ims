<template>
  <div class="layout-viewer" data-readonly="true" :data-testid="testId" @click="keepReadOnly">
    <div
      v-if="html"
      class="layout-viewer-html"
      :data-testid="testId === 'content-layout-preview' ? 'content-layout-html' : undefined"
      v-html="html"
    />
    <pre v-else class="layout-viewer-body" data-testid="content-layout-body">{{ plain }}</pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeLayoutHtml } from '../content/layoutHtml'

const props = withDefaults(
  defineProps<{ layoutHtml?: string; body?: string; testId?: string }>(),
  { testId: 'content-layout-preview' },
)

const html = computed(() => sanitizeLayoutHtml(props.layoutHtml))
const plain = computed(() => {
  const text = (props.body || '').trim()
  return text || '暂无正文'
})

function keepReadOnly(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest('a')) event.preventDefault()
}
</script>

<style scoped>
.layout-viewer-html,
.layout-viewer-body {
  width: 100%;
  max-width: 677px;
  box-sizing: border-box;
}
.layout-viewer-html {
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 12px 14px;
  background: #fff;
  overflow: auto;
  line-height: 1.6;
}
.layout-viewer-html :deep(img) {
  max-width: 100%;
  height: auto;
}
.layout-viewer-html :deep(.ims-layout) {
  font-size: 13px;
  line-height: 1.7;
}
.layout-viewer-html :deep(.ims-layout p) {
  margin: 0 0 8px;
}
.layout-viewer-html :deep(.ims-lead) {
  font-weight: 600;
  border-left: 3px solid #c2410c;
  padding-left: 8px;
}
.layout-viewer-html :deep(.ims-scan-line) {
  padding: 4px 0;
  border-bottom: 1px dashed #d0d0d0;
}
.layout-viewer-html :deep(.ims-analysis) {
  margin: 0 0 8px;
  padding: 6px 8px;
  background: #f4f7fb;
  border-radius: 6px;
}
.layout-viewer-body {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
}
</style>
