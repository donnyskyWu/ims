<template>
  <div class="content-layout-preview" :data-testid="testId">
    <div v-if="layoutHtml" class="content-layout-html" v-html="layoutHtml" />
    <pre v-else class="content-layout-plain">{{ body || '暂无正文' }}</pre>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    layoutHtml?: string
    body?: string
    testId?: string
  }>(),
  { layoutHtml: '', body: '', testId: 'content-layout-preview' },
)
</script>

<style scoped>
.content-layout-plain {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
}
.content-layout-html :deep(.ims-layout) {
  font-size: 13px;
  line-height: 1.7;
  color: #1d1d1f;
}
.content-layout-html :deep(.ims-layout p) {
  margin: 0 0 8px;
}
.content-layout-html :deep(.ims-lead) {
  font-weight: 600;
  border-left: 3px solid #c2410c;
  padding-left: 8px;
}
.content-layout-html :deep(.ims-scan-line) {
  padding: 4px 0;
  border-bottom: 1px dashed #d0d0d0;
}
.content-layout-html :deep(.ims-analysis) {
  margin: 0 0 8px;
  padding: 6px 8px;
  background: #f4f7fb;
  border-radius: 6px;
}
</style>
