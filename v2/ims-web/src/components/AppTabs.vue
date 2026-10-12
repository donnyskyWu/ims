<script setup lang="ts">
import { watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const props = defineProps<{
  items: { key: string; label: string; count?: number | null }[];
  type?: "line" | "pill";
  syncQuery?: string;
}>();
const active = defineModel<string>("active", { required: true });
const emit = defineEmits<{ change: [key: string] }>();
const route = useRoute();
const router = useRouter();

watch(
  () => props.syncQuery && route.query[props.syncQuery],
  (value) => {
    if (!props.syncQuery) return;
    const next = typeof value === "string" ? value : "";
    if (next && next !== active.value && props.items.some((item) => item.key === next)) active.value = next;
  },
  { immediate: true },
);

function pick(key: string) {
  if (key === active.value) return;
  active.value = key;
  emit("change", key);
  if (props.syncQuery) {
    const query = { ...route.query, [props.syncQuery]: key };
    void router.replace({ query });
  }
}
</script>

<template>
  <div :class="type === 'pill' ? 'cattabs' : 'tabs'">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :class="[type === 'pill' ? 'pill' : 'tab', { on: item.key === active }]"
      @click="pick(item.key)"
    >
      {{ item.label }}
      <em v-if="item.count !== undefined && item.count !== null" class="cbadge">{{ item.count }}</em>
    </button>
  </div>
</template>

<style scoped>
.cbadge { font-style: normal; }
</style>
