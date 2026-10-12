<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/api/generated/endpoints";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";

const form = reactive({ oldPassword: "", newPassword: "" });
const error = ref("");
const auth = useAuthStore();
const router = useRouter();

async function submit() {
  error.value = "";
  try {
    await call("change_password_admin_api_ims_auth_change_password_post", { body: { ...form }, silent: true });
    auth.pwdResetRequired = false;
    auth.persist();
    toast.success("保存成功");
    await router.replace("/");
  } catch (caught) {
    error.value = (caught as BizError).msg || "修改失败";
  }
}
</script>

<template>
  <form class="card page" @submit.prevent="submit">
    <h1>{{ auth.pwdResetRequired ? "请先设置新密码" : "修改密码" }}</h1>
    <p v-if="auth.pwdResetRequired" class="muted">首次登录或管理员重置后，需要先修改密码才能继续使用。</p>
    <label class="fld">原密码<input v-model="form.oldPassword" type="password" /></label>
    <label class="fld">新密码<input v-model="form.newPassword" type="password" /></label>
    <p class="muted">8 到 32 位，且同时包含字母和数字。</p>
    <p v-if="error" class="ferr">{{ error }}</p>
    <button class="btn btn-pri" type="submit">保存</button>
  </form>
</template>

<style scoped>
h1 { font-size: 28px; }
input { width: 100%; height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 10px; }
</style>
