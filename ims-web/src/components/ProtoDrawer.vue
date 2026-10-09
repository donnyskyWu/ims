<script setup lang="ts">
import IconSvg from './IconSvg.vue'
import { useSlots } from 'vue'

withDefaults(defineProps<{ open: boolean; title: string; width?: string; zIndex?: number }>(), {
  width: '640px',
  zIndex: 100,
})
const emit = defineEmits<{ close: [] }>()
const slots = useSlots()
const closePath = 'M6 6l12 12M18 6L6 18'
</script>

<template>
  <Teleport to="body">
    <div class="mask" :class="{ on: open }" :style="{ zIndex: zIndex - 10 }" @click="emit('close')"></div>
    <aside class="drawer" :class="{ on: open }" :style="{ width, zIndex }">
      <div class="drawer-h">
        <b>{{ title }}</b>
        <span class="dr-x" @click="emit('close')"><IconSvg :d="closePath" :size="18" /></span>
      </div>
      <div class="drawer-b"><slot /></div>
      <div v-if="slots.foot || slots.footer" class="drawer-f">
        <slot name="foot"></slot>
        <slot name="footer"></slot>
      </div>
    </aside>
  </Teleport>
</template>
