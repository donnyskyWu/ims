<script setup lang="ts">
import { onMounted, ref } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";

const content = ref("");
const dirty = ref(false);
const sending = ref(false);

async function submit() {
  if (sending.value) return;
  sending.value = true;
  try {
    await new Promise((resolve) => setTimeout(resolve, 300));
    toast.success("保存成功");
    dirty.value = false;
  } finally {
    sending.value = false;
  }
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true;
  try {
    await confirm({ title: "离开确认", message: "有未保存的修改，确定离开吗？" });
    return true;
  } catch {
    return false;
  }
});

onMounted(() => {
  window.addEventListener("beforeunload", (event) => {
    if (!dirty.value) return;
    event.preventDefault();
    event.returnValue = "";
  });
});
</script>

<template>
  <section class="fill-page">
    <h1>填报</h1>
    <textarea v-model="content" @input="dirty = true" />
    <footer>
      <button class="btn btn-pri" type="button" :disabled="sending" @click="submit">{{ sending ? "提交中…" : "提交" }}</button>
    </footer>
  </section>
</template>

<style scoped>
.fill-page { min-height: calc(100vh - 120px); padding-bottom: 72px; }
h1 { font-size: 28px; }
textarea { width: 100%; min-height: 240px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 12px; }
footer { position: fixed; left: 0; right: 0; bottom: 0; height: 56px; display: flex; justify-content: flex-end; align-items: center; padding: 0 32px; background: var(--card); border-top: 1px solid var(--line); }
</style>
