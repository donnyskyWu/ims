<script setup lang="ts">
import { computed, provide, ref, watch } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { clearClientToken, pushFieldHandler, type BizError } from "@/api/http";
import { confirm } from "./confirm";
import { toast } from "@/utils/toast";

const open = defineModel<boolean>("open", { required: true });
const props = withDefaults(
  defineProps<{
    title: string;
    size?: "S" | "M" | "L";
    model: Record<string, unknown>;
    rules?: FormRules;
    submit: (model: Record<string, unknown>) => Promise<unknown>;
  }>(),
  { size: "M" },
);
const emit = defineEmits<{ saved: [result: unknown]; closed: [] }>();
const width = computed(() => ({ S: "480px", M: "720px", L: "880px" })[props.size]);
const formRef = ref<FormInstance>();
const dirty = ref(false);
const saving = ref(false);
const tokenKey = ref("");
provide("submitTokenKey", tokenKey);

watch(open, (value) => {
  if (!value) return;
  dirty.value = false;
  tokenKey.value = crypto.randomUUID();
});

watch(
  () => props.model,
  () => {
    if (open.value) dirty.value = true;
  },
  { deep: true },
);

let stopField: () => void = () => undefined;
watch(open, (value) => {
  stopField();
  if (!value) return;
  stopField = pushFieldHandler((errors) => {
    for (const item of errors) {
      const field = formRef.value?.fields.find((entry) => String(entry.prop) === item.field);
      if (!field) continue;
      field.validateState = "error";
      field.validateMessage = item.message;
    }
  });
});

async function save() {
  if (saving.value) return;
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    const result = await props.submit(props.model);
    toast.success("保存成功");
    clearClientToken(tokenKey.value);
    dirty.value = false;
    open.value = false;
    emit("saved", result);
  } catch (error) {
    const biz = error as BizError;
    if (biz?.code === 1219) {
      const field = formRef.value?.fields.find((entry) => String(entry.prop) === "name");
      if (field) {
        field.validateState = "error";
        field.validateMessage = biz.msg || "同一上级部门下已有同名部门";
      }
    }
  } finally {
    saving.value = false;
  }
}

async function askClose(done: () => void) {
  if (!dirty.value) {
    done();
    emit("closed");
    return;
  }
  try {
    await confirm({ title: "离开确认", message: "有未保存的修改，确定离开吗？" });
    dirty.value = false;
    done();
    emit("closed");
  } catch {
    /* 留在抽屉 */
  }
}
</script>

<template>
  <el-drawer :model-value="open" :size="width" :title="title" :before-close="askClose" @update:model-value="open = $event">
    <el-form ref="formRef" :model="model" :rules="rules" label-position="top" @submit.prevent>
      <slot />
    </el-form>
    <template #footer>
      <div class="foot">
        <button class="btn btn-sec" type="button" @click="askClose(() => (open = false))">取消</button>
        <button class="btn btn-pri" type="button" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存" }}</button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.foot { display: flex; justify-content: flex-end; gap: 8px; }
</style>
