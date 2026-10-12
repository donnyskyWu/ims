<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useDictStore } from "@/stores/dict";
import { statusVars } from "@/utils/status-color";

const props = defineProps<{ dictType: string; value: string | number | null | undefined }>();
const dict = useDictStore();

onMounted(() => {
  void dict.getDict(props.dictType);
});

const text = computed(() => dict.label(props.dictType, props.value == null ? "" : String(props.value)));
const known = computed(() => dict.items(props.dictType).some((item) => item.dictValue === String(props.value ?? "")));
const style = computed(() => statusVars(known.value ? dict.color(props.dictType, String(props.value ?? "")) : "neutral"));
const pending = computed(() => !dict.items(props.dictType).length && props.value !== null && props.value !== undefined && props.value !== "");
</script>

<template>
  <span v-if="pending" class="tag">…</span>
  <span v-else class="tag" :style="style">
    <i class="dot" />
    {{ text }}
  </span>
</template>
