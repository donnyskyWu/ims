<script setup lang="ts">
import { reactive, ref } from "vue";
import { BizError, request } from "@/api/http";

const props = defineProps<{ mode: "change" | "set" }>();
const emit = defineEmits<{ saved: [] }>();
const form = reactive({ oldPassword: "", newPassword: "" });
const error = ref("");
const saving = ref(false);

async function submit() {
  error.value = "";
  saving.value = true;
  try {
    if (props.mode === "set") {
      await request({ method: "POST", url: "/auth/password/set", data: { newPassword: form.newPassword }, silent: true });
    } else {
      await request({ method: "POST", url: "/auth/password/change", data: { oldPassword: form.oldPassword, newPassword: form.newPassword }, silent: true });
    }
    form.oldPassword = "";
    form.newPassword = "";
    emit("saved");
  } catch (caught) {
    error.value = (caught as BizError).msg || "保存失败";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <form class="pwd" @submit.prevent="submit">
    <label v-if="mode === 'change'" class="fld">原密码<input v-model="form.oldPassword" type="password" autocomplete="current-password" /></label>
    <label class="fld">新密码<input v-model="form.newPassword" type="password" autocomplete="new-password" /></label>
    <p class="muted">8 到 32 位，且同时包含字母和数字。</p>
    <p v-if="error" class="ferr">{{ error }}</p>
    <button class="btn btn-pri" type="submit" :disabled="saving">{{ saving ? "保存中…" : "保存" }}</button>
  </form>
</template>

<style scoped>
input { width: 100%; height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 10px; }
.pwd { display: grid; gap: 8px; max-width: 420px; }
</style>
