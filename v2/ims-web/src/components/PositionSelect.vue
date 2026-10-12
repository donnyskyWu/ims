<script setup lang="ts">
import DictSelect from "./DictSelect.vue";

withDefaults(defineProps<{ mode?: "create" | "edit" | "query" }>(), { mode: "create" });
const model = defineModel<string | null>({ default: "" });
</script>

<template>
  <DictSelect v-model="model" dict-type="dict_position" :mode="mode" />
</template>
