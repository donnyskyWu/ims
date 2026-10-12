<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import DrillPath from "@/components/DrillPath.vue";
import Perm from "@/components/Perm.vue";

const line = ref("all");
const pill = ref("all");
const path = [
  { label: "第一层" },
  { label: "第二层" },
  { label: "第三层" },
  { label: "第四层" },
  { label: "第五层" },
  { label: "第六层" },
  { label: "第七层" },
];
const shown = ref(path);
</script>

<template>
  <section class="page">
    <PageHeader title="布局示例" sub-title="页头、页签与路径" />
    <AppTabs v-model:active="line" sync-query="tab" :items="[{ key: 'all', label: '全部', count: 0 }, { key: 'open', label: '进行中', count: 2 }]" />
    <AppTabs v-model:active="pill" type="pill" :items="[{ key: 'all', label: '全部', count: 3 }, { key: 'mine', label: '我的', count: 0 }]" />
    <DrillPath :path="shown" @jump="shown = path.slice(0, $event + 1)" />
    <div>
      <Perm code="ims:demo:order:create"><button class="btn btn-pri" type="button">新建</button></Perm>
      <Perm code="ims:demo:order:delete" action="d"><button class="btn btn-danger-txt" type="button">删除</button></Perm>
    </div>
  </section>
</template>
