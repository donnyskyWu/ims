<script setup lang="ts">
import { ref, watch } from "vue";
import { pushDrawerHandler } from "@/api/http";
import StatusTag from "./StatusTag.vue";
import AppTabs from "./AppTabs.vue";

const open = defineModel<boolean>("open", { required: true });
const props = withDefaults(
  defineProps<{
    title: string;
    size?: "S" | "M" | "L" | "XL" | "F";
    statusDict?: string;
    statusValue?: string;
    tabs?: { key: string; label: string }[];
    load?: () => Promise<void>;
  }>(),
  { size: "M", tabs: () => [] },
);
const emit = defineEmits<{ closed: []; refresh: [] }>();
const width = { S: "480px", M: "720px", L: "880px", XL: "90%", F: "100%" } as const;
const tab = ref(props.tabs[0]?.key || "");

watch(open, (value) => {
  if (!value) return;
  tab.value = props.tabs[0]?.key || "";
  void props.load?.();
});

let stop: () => void = () => undefined;
watch(open, (value) => {
  stop();
  if (!value) return;
  stop = pushDrawerHandler(() => {
    open.value = false;
    emit("refresh");
    emit("closed");
  });
});
</script>

<template>
  <el-drawer :model-value="open" :size="width[size]" :title="title" @update:model-value="open = $event" @close="emit('closed')">
    <template #header>
      <div class="head">
        <strong>{{ title }}</strong>
        <StatusTag v-if="statusDict" :dict-type="statusDict" :value="statusValue" />
      </div>
    </template>
    <AppTabs v-if="tabs.length" v-model:active="tab" :items="tabs" />
    <div class="body">
      <slot :name="tab || 'default'" />
      <slot />
    </div>
    <template #footer>
      <div class="foot"><slot name="footer" /></div>
    </template>
  </el-drawer>
</template>

<style scoped>
.head { display: flex; align-items: center; gap: 8px; font-size: 16px; }
.foot { display: flex; justify-content: flex-end; gap: 8px; }
.body { padding-top: 12px; }
</style>
