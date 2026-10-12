<script setup lang="ts">
import { watch } from "vue";
import { useRouter } from "vue-router";
import StatusTag from "@/components/StatusTag.vue";
import { formatShanghai } from "./logic";
import { readMessages, type MessageRow } from "./api";

const open = defineModel<boolean>("open", { required: true });
const props = defineProps<{ message: MessageRow | null }>();
const emit = defineEmits<{ read: [id: string] }>();
const router = useRouter();

watch(
  () => [open.value, props.message?.id, props.message?.readStatus] as const,
  ([shown, id, status]) => {
    if (!shown || !id || status !== "UNREAD") return;
    void readMessages([id]).then(() => emit("read", id));
  },
);

function viewSource() {
  const path = props.message?.route;
  if (!path) return;
  open.value = false;
  void router.push(path);
}
</script>

<template>
  <el-drawer :model-value="open" :size="520" title="消息详情" @update:model-value="open = $event">
    <template v-if="message">
      <div class="head">
        <strong>{{ message.title }}</strong>
        <StatusTag dict-type="dict_msg_type" :value="message.msgType" />
      </div>
      <p class="meta">{{ message.sourceModuleLabel }} · {{ formatShanghai(message.createTime) }}</p>
      <p class="body">{{ message.content || message.summary || "—" }}</p>
    </template>
    <template #footer>
      <button v-if="message?.route" class="btn btn-sec btn-sm" type="button" @click="viewSource">查看来源</button>
      <button class="btn btn-pri btn-sm" type="button" @click="open = false">关闭</button>
    </template>
  </el-drawer>
</template>

<style scoped>
.head { display: flex; align-items: center; gap: 8px; font-size: 16px; }
.meta { color: var(--text2); font-size: 12px; }
.body { white-space: pre-wrap; line-height: 1.6; }
</style>
