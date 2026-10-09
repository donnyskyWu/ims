<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    layoutHtml?: string
    body?: string
  }>(),
  { layoutHtml: '', body: '' },
)

function sanitizeLayoutHtml(raw: string): string {
  const html = (raw || '').trim()
  if (!html || typeof DOMParser === 'undefined') return ''
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('script,iframe,object,embed,link,meta').forEach((el) => el.remove())
  doc.querySelectorAll('*').forEach((el) => {
    for (const attr of [...el.attributes]) {
      const name = attr.name.toLowerCase()
      const value = attr.value.trim().toLowerCase()
      if (name.startsWith('on') || name === 'srcdoc') {
        el.removeAttribute(attr.name)
      } else if ((name === 'href' || name === 'src') && value.startsWith('javascript:')) {
        el.removeAttribute(attr.name)
      }
    }
  })
  return doc.body.innerHTML
}

function hasVisibleLayout(html: string): boolean {
  if (!html.trim()) return false
  const text = html
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .trim()
  if (text) return true
  return /<(img|video|audio|table|svg|canvas)\b/i.test(html)
}

const safeHtml = computed(() => sanitizeLayoutHtml(props.layoutHtml || ''))
const showLayout = computed(() => hasVisibleLayout(safeHtml.value))
const bodyText = computed(() => (props.body || '').trim())
</script>

<template>
  <div class="clp" data-testid="content-layout-preview">
    <div v-if="showLayout" class="clp-html" v-html="safeHtml"></div>
    <pre v-else-if="bodyText" class="clp-text">{{ bodyText }}</pre>
    <p v-else class="hint">暂无正文</p>
  </div>
</template>

<style scoped>
.clp {
  max-width: 677px;
  border: 1px solid var(--line, #e5e5ea);
  border-radius: 8px;
  background: #fafafc;
  padding: 12px 14px;
  min-height: 96px;
}
.clp-html,
.clp-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text, #1d1d1f);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
.clp-html :deep(img),
.clp-html :deep(video) {
  max-width: 100%;
  height: auto;
}
</style>
