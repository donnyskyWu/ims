<template>
  <div class="page">
    <div class="pg-h">
      <div>
        <h1>{{ title }}</h1>
        <div class="sub">{{ sub }}</div>
      </div>
    </div>
    <div class="card">
      <div class="empty">
        <div class="et">建设中</div>
        <div class="es">这个菜单还没有可用接口。侧栏和页面骨架已按原型保留。</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { mods } from '../../nav/menu'

const route = useRoute()
const mod = computed(() => mods[String(route.params.modId || '')])
const title = computed(() => mod.value?.page || mod.value?.name || '建设中')
const sub = computed(() => mod.value?.desc || '菜单已保留，接口尚未提供')
</script>
