<template>
  <div data-testid="content-layout-panel">
    <div class="dsec">排版</div>
    <p v-if="!contentId" class="hint">请先保存内容，再套用模板或一键排版。</p>
    <template v-else>
      <p class="hint" data-testid="content-layout-format">当前版式：{{ bodyFormat || 'PLAIN' }}</p>
      <div class="fld">
        <label>版式模板</label>
        <select v-model="templateId" data-testid="content-layout-template">
          <option value="">选择模板</option>
          <option v-for="tpl in templates" :key="tpl.id" :value="String(tpl.id)">{{ tpl.templateName }}</option>
        </select>
      </div>
      <p v-if="templatesState === 'empty'" class="hint" data-testid="content-layout-templates-empty">
        没有已启用的公推模板。到公推模板库新建并发布后再套用。
      </p>
      <p v-if="!body.trim()" class="hint" data-testid="content-layout-need-body">正文为空时不能套用模板或预览排版。</p>
      <button
        class="btn btn-sec btn-sm"
        type="button"
        data-testid="content-layout-apply-template"
        :disabled="!body.trim()"
        @click="applyTemplate"
      >
        套用模板
      </button>
      <div class="fld" style="margin-top: 10px">
        <label>一键排版（规则预设）</label>
        <select v-model="preset" data-testid="content-layout-preset">
          <option v-for="item in presets" :key="item.code" :value="item.code">{{ item.label }}</option>
        </select>
      </div>
      <div class="acts" style="margin: 8px 0">
        <button
          class="btn btn-sec btn-sm"
          type="button"
          data-testid="content-layout-preview-btn"
          :disabled="!body.trim()"
          @click="previewRule"
        >
          预览排版
        </button>
        <button
          class="btn btn-pri btn-sm"
          type="button"
          data-testid="content-layout-apply-btn"
          :disabled="!previewHtml"
          @click="applyRule"
        >
          应用排版
        </button>
      </div>
      <p v-if="error" class="hint" data-testid="content-layout-error" style="color: var(--red)">{{ error }}</p>
      <p v-else-if="fidelityNote" class="hint">{{ fidelityNote }}</p>
      <div class="layout-compare">
        <div>
          <div class="csub">排版前</div>
          <pre data-testid="content-layout-before">{{ body || '（空）' }}</pre>
        </div>
        <div>
          <div class="csub">排版后</div>
          <ContentLayoutPreview :layout-html="shownHtml" :body="''" test-id="content-layout-after" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { http, errorMessage } from '../api/http'
import ContentLayoutPreview from './ContentLayoutPreview.vue'

type TemplateRow = { id: number; templateName: string; status: string }
type Applied = {
  layoutHtml: string
  layoutJson: string
  bodyFormat: string
  layoutTemplateId: number | null
  body: string
}

const props = defineProps<{
  contentId: number | null
  body: string
  bodyFormat?: string
  layoutHtml?: string
}>()

const emit = defineEmits<{ applied: [payload: Applied] }>()

const presets = [
  { code: 'clean-read', label: '清爽阅读' },
  { code: 'marketing', label: '营销引流' },
  { code: 'decision-scan', label: '决策扫读' },
  { code: 'analysis-report', label: '分析报告' },
]

const templates = ref<TemplateRow[]>([])
const templatesState = ref<'loading' | 'ready' | 'empty' | 'error'>('loading')
const templateId = ref('')
const preset = ref('clean-read')
const previewHtml = ref('')
const error = ref('')
const fidelityNote = ref('')

const shownHtml = computed(() => previewHtml.value || props.layoutHtml || '')

watch(
  () => [props.body, preset.value, props.contentId],
  () => {
    previewHtml.value = ''
    fidelityNote.value = ''
  },
)

function bizCode(err: unknown): number | null {
  if (err && typeof err === 'object' && 'code' in err) {
    const code = (err as { code?: unknown }).code
    return typeof code === 'number' ? code : null
  }
  return null
}

async function loadTemplates() {
  templatesState.value = 'loading'
  try {
    const res = await http.get('/content/layout-template/list', {
      params: { status: 'ENABLED', pageNo: 1, pageSize: 50 },
    })
    templates.value = res.data.data?.list || []
    if (!templateId.value && templates.value.length) {
      const clean = templates.value.find((row) => row.templateName === '清爽阅读')
      templateId.value = String((clean || templates.value[0]).id)
    }
    templatesState.value = templates.value.length ? 'ready' : 'empty'
  } catch (e) {
    templates.value = []
    templatesState.value = 'error'
    error.value = errorMessage(e)
  }
}

function confirmOverwrite(): boolean {
  if ((props.bodyFormat || 'PLAIN') !== 'LAYOUT') return true
  return window.confirm('将覆盖当前版式，正文文字不会改动')
}

function emitApplied(data: {
  layoutHtml?: string
  layoutJson?: string | object
  bodyFormat?: string
  layoutTemplateId?: number | null
  body?: string
}) {
  const layoutJson = typeof data.layoutJson === 'string' ? data.layoutJson : JSON.stringify(data.layoutJson || {})
  previewHtml.value = data.layoutHtml || ''
  emit('applied', {
    layoutHtml: data.layoutHtml || '',
    layoutJson,
    bodyFormat: data.bodyFormat || 'LAYOUT',
    layoutTemplateId: data.layoutTemplateId ?? null,
    body: props.body,
  })
}

async function applyTemplate() {
  error.value = ''
  if (!props.contentId) return
  if (!props.body.trim()) return
  if (!templateId.value) {
    error.value = '请选择版式模板'
    return
  }
  if (!confirmOverwrite()) return
  try {
    const res = await http.post(`/content/${props.contentId}/typeset/apply`, {
      mode: 'TEMPLATE',
      templateId: Number(templateId.value),
      overwrite: (props.bodyFormat || 'PLAIN') === 'LAYOUT',
      body: props.body,
    })
    fidelityNote.value = '已套用模板，正文文字未改动'
    emitApplied(res.data.data || {})
  } catch (e) {
    if (bizCode(e) === 2031 && window.confirm('将覆盖当前版式，正文文字不会改动')) {
      try {
        const res = await http.post(`/content/${props.contentId}/typeset/apply`, {
          mode: 'TEMPLATE',
          templateId: Number(templateId.value),
          overwrite: true,
          body: props.body,
        })
        fidelityNote.value = '已套用模板，正文文字未改动'
        emitApplied(res.data.data || {})
        return
      } catch (err) {
        error.value = errorMessage(err)
        return
      }
    }
    error.value = errorMessage(e)
  }
}

async function previewRule() {
  error.value = ''
  fidelityNote.value = ''
  if (!props.contentId || !props.body.trim()) return
  try {
    const res = await http.post(`/content/${props.contentId}/typeset/preview`, {
      mode: 'RULE',
      preset: preset.value,
      body: props.body,
    })
    const data = res.data.data || {}
    previewHtml.value = data.layoutHtml || ''
    fidelityNote.value = data.fidelityCheck?.passed ? '预览通过保真校验，正文文字未改动' : ''
  } catch (e) {
    previewHtml.value = ''
    error.value = errorMessage(e)
  }
}

async function applyRule() {
  error.value = ''
  if (!props.contentId || !previewHtml.value) return
  if (!confirmOverwrite()) return
  try {
    const res = await http.post(`/content/${props.contentId}/typeset/apply`, {
      mode: 'RULE',
      preset: preset.value,
      overwrite: (props.bodyFormat || 'PLAIN') === 'LAYOUT',
      body: props.body,
    })
    fidelityNote.value = '已应用排版，正文文字未改动'
    emitApplied(res.data.data || {})
  } catch (e) {
    if (bizCode(e) === 2031 && window.confirm('将覆盖当前版式，正文文字不会改动')) {
      try {
        const res = await http.post(`/content/${props.contentId}/typeset/apply`, {
          mode: 'RULE',
          preset: preset.value,
          overwrite: true,
          body: props.body,
        })
        fidelityNote.value = '已应用排版，正文文字未改动'
        emitApplied(res.data.data || {})
        return
      } catch (err) {
        error.value = errorMessage(err)
        return
      }
    }
    error.value = errorMessage(e)
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.layout-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 8px;
}
.layout-compare pre,
.layout-compare :deep(.content-layout-preview) {
  margin: 0;
  min-height: 72px;
  padding: 8px;
  background: #f6f7f9;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 12px;
}
</style>
