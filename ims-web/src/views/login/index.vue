<template>
  <div class="login-screen proto-root">
    <form class="login-card" @submit.prevent="submit">
      <div class="logo" style="padding: 0 0 8px">
        <b>IMS 一体化管理系统</b>
        <small>神鱼体育</small>
      </div>
      <h1>登录</h1>
      <div class="sub">使用用户名和密码进入系统</div>
      <div class="fld">
        <label>用户名</label>
        <input v-model="username" autocomplete="username" />
      </div>
      <div class="fld">
        <label>密码</label>
        <input v-model="password" type="password" autocomplete="current-password" />
      </div>
      <p v-if="error" class="login-err">{{ error }}</p>
      <button class="btn btn-pri" type="submit" :disabled="loading">{{ loading ? '登录中…' : '登录' }}</button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../../api/http'
import { useUserStore } from '../../stores/user'

const username = ref('admin')
const password = ref('Admin@123')
const error = ref('')
const loading = ref(false)
const user = useUserStore()
const router = useRouter()

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await user.login(username.value, password.value)
    router.push('/ims/system/user')
  } catch (e: unknown) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>
