<script setup lang="ts">
defineProps<{
  label: string
  required?: boolean
  error?: string
}>()
</script>

<template>
  <label class="ims-field">
    <span>{{ label }}<i v-if="required" class="req">*</i></span>
    <slot />
    <p v-if="error" class="ims-field-error" data-testid="field-error">{{ error }}</p>
  </label>
</template>
