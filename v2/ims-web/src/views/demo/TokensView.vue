<script setup lang="ts">
const colors = [
  ["页面背景", "--bg", "f5f5f7"],
  ["卡片", "--card", "fff"],
  ["主文字", "--text", "1d1d1f"],
  ["次文字", "--text2", "86868b"],
  ["主色", "--blue", "0071e3"],
  ["主色悬停", "--blue-h", "0077ed"],
  ["选中底", "--blue-bg", "e8f2fe"],
  ["成功", "--green", "34c759"],
  ["警告", "--orange", "ff9500"],
  ["危险", "--red", "ff3b30"],
  ["中性", "--gray", "8e8e93"],
  ["信息", "--cyan", "5ac8fa"],
  ["分类", "--purple", "af52da"],
  ["等级", "--yellow", "ffcc00"],
];
const states = [
  ["进行中", "primary"],
  ["完成", "success"],
  ["待办", "warning"],
  ["失败", "danger"],
  ["中性", "neutral"],
  ["信息", "info"],
  ["分类", "purple"],
  ["等级", "yellow"],
];
</script>

<template>
  <section class="page">
    <h1>样式</h1>
    <p class="muted">侧栏 232px，顶栏 56px，按钮高 32px，输入框高 34px，表头 11px。</p>
    <div class="swatches">
      <div v-for="item in colors" :key="item[1]" class="swatch">
        <i :style="{ background: `var(${item[1]})` }" />
        <span>{{ item[0] }}</span>
        <small>{{ item[2] }}</small>
      </div>
    </div>
    <div class="row">
      <button class="btn btn-pri" type="button">主按钮</button>
      <button class="btn btn-sec" type="button">次按钮</button>
      <button class="btn btn-txt" type="button">文字按钮</button>
      <button class="btn btn-danger-txt" type="button">危险文字</button>
      <input class="demo-input" placeholder="输入框" />
    </div>
    <table class="demo-table">
      <thead><tr><th>表头</th></tr></thead>
      <tbody><tr><td>单元格</td></tr></tbody>
    </table>
    <div class="states">
      <span v-for="item in states" :key="item[1]" class="tag" :style="{ color: `var(--st-${item[1]}-fg)`, background: `var(--st-${item[1]}-bg)` }">
        <i class="dot" />{{ item[0] }}
      </span>
    </div>
  </section>
</template>

<style scoped>
h1 { font-size: 28px; }
.swatches { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.swatch i { display: block; height: 36px; border-radius: var(--r-s); border: 1px solid var(--line); }
.row { display: flex; gap: 8px; align-items: center; margin: 16px 0; }
.demo-input { height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 10px; }
.demo-table { width: 100%; border-collapse: collapse; background: var(--card); }
.demo-table th { font-size: 11px; font-weight: 600; color: var(--text2); background: var(--table-head); text-align: left; padding: 10px 12px; }
.demo-table td { font-size: 13px; padding: 10px 12px; }
.states { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
