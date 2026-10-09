<template>
  <ProtoDrawer :open="open" title="AI 文案" width="560px" :z-index="140" @close="emit('close')">
    <p class="hint">选择模型并输入提示。生成结果仅预览，采纳后写入正文，不会自动排版。</p>
    <div class="formrow one">
      <div class="fld">
        <label>模型</label>
        <select v-model="modelId">
          <option v-if="!models.length" value="">加载中</option>
          <option v-for="row in models" :key="row.id" :value="row.id">
            {{ row.modelName }}（{{ row.vendor || '模型' }}）
          </option>
        </select>
      </div>
      <div class="fld">
        <label>{{ roundCount >= 2 ? '本次修改要求' : '提示' }}</label>
        <textarea v-model="prompt" rows="4" placeholder="写一段赛后复盘，或描述要续写的修改" />
      </div>
    </div>
    <p v-if="error" class="hint" style="color: var(--red)">{{ error }}</p>
    <div v-if="preview" class="fld">
      <label>预览 · 第 {{ roundCount }} 轮</label>
      <pre class="ai-copy-preview">{{ preview }}</pre>
    </div>
    <template #footer>
      <button class="btn btn-sec" type="button" @click="emit('close')">关闭</button>
      <button v-if="error" class="btn btn-sec" type="button" :disabled="generating" @click="retry">重试</button>
      <button v-if="preview" class="btn btn-sec" type="button" :disabled="generating" @click="run(true)">续写</button>
      <button class="btn btn-sec" type="button" :disabled="generating || !modelId" @click="run(false)">生成</button>
      <button class="btn btn-pri" type="button" :disabled="!preview" @click="adopt">采纳</button>
    </template>
  </ProtoDrawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { http, errorMessage } from '../api/http'
import ProtoDrawer from './ProtoDrawer.vue'

type ModelRow = { id: string; modelName: string; vendor?: string; status?: string }
type Turn = { role: string; content: string }

const props = defineProps<{ open: boolean; contentId?: number | null }>()
const emit = defineEmits<{
  close: []
  adopt: [payload: { markdown: string; targetField: string }]
}>()

const models = ref<ModelRow[]>([])
const modelId = ref('')
const prompt = ref('')
const preview = ref('')
const error = ref('')
const generating = ref(false)
const roundCount = ref(1)
const history = ref<Turn[]>([])
const targetField = ref('body')
const lastContinue = ref(false)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    prompt.value = ''
    preview.value = ''
    error.value = ''
    roundCount.value = 1
    history.value = []
    targetField.value = 'body'
    void loadModels()
  },
)

async function loadModels() {
  try {
    const { data } = await http.get('/content/ai-content/models')
    models.value = data.data || []
    if (!models.value.some((row) => row.id === modelId.value)) {
      modelId.value = models.value[0]?.id || ''
    }
  } catch (e) {
    error.value = errorMessage(e)
    models.value = []
  }
}

async function run(continueRound: boolean) {
  const text = prompt.value.trim()
  if (!modelId.value) {
    error.value = '请选择模型'
    return
  }
  if (!continueRound && !text) {
    error.value = '请输入提示'
    return
  }
  if (continueRound && !preview.value) {
    error.value = '请先生成正文'
    return
  }
  const nextRound = continueRound ? Math.min(10, Math.max(roundCount.value, 1) + 1) : 1
  lastContinue.value = continueRound
  generating.value = true
  error.value = ''
  try {
    const { data } = await http.post('/content/ai-content/generate', {
      modelId: modelId.value,
      prompt: text || '请在现有正文上续写一段。',
      contentId: props.contentId || undefined,
      roundCount: nextRound,
      currentBody: continueRound ? preview.value : '',
      history: continueRound ? history.value : [],
    })
    const markdown = String(data.data?.markdown || '')
    preview.value = markdown
    roundCount.value = Number(data.data?.roundCount || nextRound)
    targetField.value = String(data.data?.targetField || 'body')
    const prior = continueRound ? history.value : []
    history.value = [
      ...prior,
      { role: 'user', content: text || '请在现有正文上续写一段。' },
      { role: 'assistant', content: markdown },
    ].slice(-6)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    generating.value = false
  }
}

function retry() {
  void run(lastContinue.value)
}

function adopt() {
  if (!preview.value) return
  emit('adopt', { markdown: preview.value, targetField: targetField.value })
}
</script>

<style scoped>
.ai-copy-preview {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  max-height: 280px;
  overflow: auto;
  background: #f6f8fa;
  border: 1px solid var(--line);
  border-radius: var(--r-s);
  padding: 10px 12px;
  font-size: 12.5px;
  line-height: 1.55;
}
</style>
