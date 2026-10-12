<script setup lang="ts">
import { useRouter } from "vue-router";
import PasswordForm from "@/components/PasswordForm.vue";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/utils/toast";

const auth = useAuthStore();
const router = useRouter();

async function saved() {
  auth.pwdResetRequired = false;
  auth.persist();
  toast.success("保存成功");
  await router.replace("/");
}
</script>

<template>
  <section class="card page">
    <h1>{{ auth.pwdResetRequired ? "请先设置新密码" : "修改密码" }}</h1>
    <p v-if="auth.pwdResetRequired" class="muted">首次登录或管理员重置后，需要先修改密码才能继续使用。</p>
    <PasswordForm mode="change" @saved="saved" />
  </section>
</template>

<style scoped>
h1 { font-size: 28px; }
</style>
