<script setup lang="ts">
import { ref } from "vue";
import { call } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";

const result = ref("");
const drawer = ref(false);
const detail = ref(false);
const model = ref<Record<string, unknown>>({ name: "", amount: "" });

async function run(code?: number) {
  try {
    if (!code) {
      const data = await call("message_unread_count_admin_api_ims_message_unread_count_get");
      result.value = JSON.stringify(data);
      return;
    }
    await call("demo_error_admin_api_ims_demo_error_get", { query: { code }, inDrawer: detail.value });
  } catch (caught) {
    result.value = (caught as BizError).msg;
  }
}

async function emptyForm() {
  drawer.value = true;
}

async function save(payload: Record<string, unknown>) {
  return call("order_create_admin_api_ims_demo_order_create_post", { body: payload, silent: true });
}

async function timeout() {
  try {
    await call("order_echo_admin_api_ims_demo_order_echo_post", {
      body: { name: "超时", testDelayMs: 5000 },
      timeout: 800,
      tokenKey: "timeout-demo",
    });
  } catch (caught) {
    result.value = (caught as BizError).msg;
  }
}
</script>

<template>
  <section class="page">
    <h1>请求</h1>
    <div class="row">
      <button class="btn btn-pri" type="button" @click="run()">成功请求</button>
      <button class="btn btn-sec" type="button" @click="emptyForm">提交空表单</button>
      <button class="btn btn-sec" type="button" @click="run(1001)">表单校验错误</button>
      <button class="btn btn-sec" type="button" @click="run(1008)">无权限操作</button>
      <button class="btn btn-sec" type="button" @click="run(1002)">登录失效</button>
      <button class="btn btn-sec" type="button" @click="run(1003)">其他设备登录</button>
      <button class="btn btn-sec" type="button" @click="detail = true">打开详情</button>
      <button class="btn btn-sec" type="button" @click="run(1504)">资源不可用</button>
      <button class="btn btn-sec" type="button" @click="run(5007)">系统异常</button>
      <button class="btn btn-sec" type="button" @click="timeout">超时</button>
    </div>
    <p>{{ result }}</p>
    <FormDrawer v-model:open="drawer" title="新建" :model="model" :submit="save">
      <div class="fld"><label>名称</label><el-input v-model="model.name" /></div>
      <div class="fld"><label>金额</label><el-input v-model="model.amount" /></div>
    </FormDrawer>
    <DetailDrawer v-model:open="detail" title="详情">
      <p>详情内容</p>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.row { display: flex; flex-wrap: wrap; gap: 8px; }
h1 { font-size: 28px; }
</style>
