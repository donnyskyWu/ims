<script setup lang="ts">
defineProps<{
  open: boolean
  title?: string
  message: string
}>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <div v-if="open" class="ims-confirm-mask" data-testid="confirm-dialog" @click.self="emit('cancel')">
    <div class="ims-confirm" role="dialog" aria-modal="true">
      <h3>{{ title || '请确认' }}</h3>
      <p>{{ message }}</p>
      <div class="acts">
        <button class="btn btn-sec btn-sm" type="button" data-testid="confirm-cancel" @click="emit('cancel')">取消</button>
        <button class="btn btn-pri btn-sm" type="button" data-testid="confirm-ok" @click="emit('confirm')">确定</button>
      </div>
    </div>
  </div>
</template>
