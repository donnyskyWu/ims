<script setup lang="ts">
import { ref } from "vue";
import { confirm } from "./confirm";

const props = defineProps<{
  steps: { key: string; title: string; validate?: () => Promise<boolean> }[];
}>();
const current = defineModel<number>("current", { default: 0 });
const emit = defineEmits<{ finish: [] }>();
const error = ref("");

async function next() {
  const step = props.steps[current.value];
  if (step?.validate) {
    const ok = await step.validate().catch(() => false);
    if (!ok) {
      error.value = "请先完成本步必填项";
      return;
    }
  }
  error.value = "";
  if (current.value >= props.steps.length - 1) {
    emit("finish");
    return;
  }
  current.value += 1;
}

function prev() {
  error.value = "";
  if (current.value > 0) current.value -= 1;
}

async function leave() {
  await confirm({ title: "离开确认", message: "有未保存的修改，确定离开吗？" });
}

defineExpose({ leave });
</script>

<template>
  <div>
    <ol class="steps">
      <li v-for="(step, index) in steps" :key="step.key" :class="{ on: index === current }">{{ index + 1 }}. {{ step.title }}</li>
    </ol>
    <slot :name="steps[current]?.key" />
    <p v-if="error" class="ferr">{{ error }}</p>
    <div class="foot">
      <button v-if="current > 0" class="btn btn-sec" type="button" @click="prev">上一步</button>
      <button class="btn btn-pri" type="button" @click="next">{{ current >= steps.length - 1 ? "完成" : "下一步" }}</button>
    </div>
  </div>
</template>

<style scoped>
.steps { display: flex; gap: 12px; padding: 0; list-style: none; color: var(--text2); }
.steps .on { color: var(--blue); font-weight: 600; }
.foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
