<script setup lang="ts">
const dev = !import.meta.env.PROD;
const links = import.meta.env.PROD ? [] : [
  ["样式", "/demo/tokens"],
  ["请求", "/demo/request"],
  ["布局", "/demo/layout"],
  ["列表示例", "/demo/list"],
  ["页签列表", "/demo/tabs-list"],
  ["表单", "/demo/form"],
  ["选择器", "/demo/selectors"],
  ["文件", "/demo/files"],
  ["展示", "/demo/display"],
  ["部门树", "/demo/dept-tree"],
  ["左树右表", "/demo/left-tree-right-table"],
  ["工作台", "/demo/workbench"],
  ["填报", "/demo/fill"],
];
</script>

<template>
  <section class="page">
    <h1>工作台</h1>
    <p class="muted">请从左侧菜单进入功能。</p>
    <nav v-if="dev" class="links">
      <router-link v-for="item in links" :key="item[1]" :to="item[1]">{{ item[0] }}</router-link>
    </nav>
  </section>
</template>

<style scoped>
h1 { font-size: 28px; font-weight: 700; }
.links { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
