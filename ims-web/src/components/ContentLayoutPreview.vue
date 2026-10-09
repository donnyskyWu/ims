<template>
  <div class="layout-viewer" data-testid="content-layout-preview" @click="keepReadOnly">
    <div
      v-if="html"
      class="layout-viewer-html"
      data-testid="content-layout-html"
      v-html="html"
    />
    <pre v-else class="layout-viewer-body" data-testid="content-layout-body">{{ plain }}</pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeLayoutHtml } from '../content/layoutHtml'

const props = defineProps<{ layoutHtml?: string; body?: string }>()

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
.layout-viewer-body {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
}
</style>
