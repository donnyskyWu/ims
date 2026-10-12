<script setup lang="ts">
import { ref } from "vue";
import { registerConfirm, type ConfirmOptions, type ConfirmResult } from "./confirm";
import { BizError } from "@/api/http";

const visible = ref(false);
const options = ref<ConfirmOptions | null>(null);
const reason = ref("");
const loading = ref(false);
const error = ref("");
let resolveFn: ((value: ConfirmResult) => void) | null = null;
let rejectFn: ((reason?: unknown) => void) | null = null;

function open(next: ConfirmOptions) {
  options.value = next;
  reason.value = "";
  error.value = "";
  loading.value = false;
  visible.value = true;
  return new Promise<ConfirmResult>((resolve, reject) => {
    resolveFn = resolve;
    rejectFn = reject;
  });
}

registerConfirm(open);

function cancel() {
  if (loading.value) return;
  visible.value = false;
  rejectFn?.(new Error("cancel"));
}

async function ok() {
  if (options.value?.reasonRequired && !reason.value.trim()) return;
  loading.value = true;
  error.value = "";
  try {
    if (options.value?.action) await options.value.action(reason.value.trim() || undefined);
    visible.value = false;
    resolveFn?.({ reason: reason.value.trim() || undefined });
  } catch (caught) {
    const biz = caught as BizError;
    error.value = biz?.msg || "操作失败";
  } finally {
    loading.value = false;
  }
}

defineExpose({ open });
</script>

<template>
  <el-dialog :model-value="visible" :title="options?.title || ''" width="420" :close-on-click-modal="false" @close="cancel">
    <p>{{ options?.message }}</p>
    <label v-if="options?.reasonRequired" class="fld">
      <span>{{ options?.reasonLabel || "原因" }}</span>
      <textarea v-model="reason" :maxlength="options?.reasonMax || 200" />
    </label>
    <p v-if="error" class="ferr">{{ error }}</p>
    <template #footer>
      <button class="btn btn-sec" type="button" @click="cancel">取消</button>
      <button class="btn" :class="options?.danger ? 'btn-danger' : 'btn-pri'" type="button" :disabled="loading || (options?.reasonRequired && !reason.trim())" @click="ok">
        {{ loading ? "处理中…" : options?.okText || "确定" }}
      </button>
    </template>
  </el-dialog>
</template>

<style scoped>
.btn-danger { background: var(--red); color: var(--on-primary); }
textarea { width: 100%; min-height: 70px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 8px; }
</style>
