<script setup lang="ts">
import { ref } from "vue";
import { sceneAccept, validateFile } from "@/api/scenes";
import { uploadFile } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";

const props = withDefaults(defineProps<{ scene: string; limit?: number; accept?: string }>(), { limit: 1 });
const emit = defineEmits<{ uploaded: [payload: Record<string, unknown>] }>();
const model = defineModel<string | string[] | null>({ default: null });
const names = ref<Record<string, string>>({});
const progress = ref(0);
const error = ref("");
const input = ref<HTMLInputElement | null>(null);

function keys(): string[] {
  if (!model.value) return [];
  return Array.isArray(model.value) ? model.value : [model.value];
}

async function onChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  error.value = "";
  const message = validateFile(props.scene, file);
  if (message) {
    error.value = message;
    if (input.value) input.value.value = "";
    return;
  }
  progress.value = 8;
  const timer = window.setInterval(() => {
    progress.value = Math.min(90, progress.value + 8);
  }, 200);
  try {
    const saved = await uploadFile<Record<string, unknown>>(props.scene, file);
    progress.value = 100;
    const key = String(saved.fileKey || "");
    emit("uploaded", saved);
    names.value[key] = String(saved.originalName || saved.fileName || file.name);
    if (props.limit <= 1) model.value = key;
    else model.value = [...keys(), key];
  } catch (caught) {
    error.value = (caught as BizError).msg || "上传失败";
    progress.value = 0;
  } finally {
    window.clearInterval(timer);
    if (input.value) input.value.value = "";
  }
}

function remove(key: string) {
  const next = keys().filter((item) => item !== key);
  model.value = props.limit <= 1 ? null : next;
}
</script>

<template>
  <div>
    <input ref="input" type="file" :accept="accept || sceneAccept(scene)" @change="onChange" />
    <div v-if="progress > 0 && progress < 100" class="bar"><i :style="{ width: progress + '%' }" /></div>
    <ul>
      <li v-for="key in keys()" :key="key">
        {{ names[key] || "已上传文件" }}
        <button class="btn btn-txt" type="button" @click="remove(key)">删除</button>
        <slot name="preview" :file-key="key" />
      </li>
    </ul>
    <p v-if="error" class="ferr">{{ error }}</p>
  </div>
</template>

<style scoped>
.bar { height: 6px; background: var(--bg); border-radius: 3px; margin-top: 8px; }
.bar i { display: block; height: 100%; background: var(--blue); }
ul { list-style: none; padding: 0; }
</style>
