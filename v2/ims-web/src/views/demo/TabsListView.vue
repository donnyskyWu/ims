<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import StatCard from "@/components/StatCard.vue";
import AppTabs from "@/components/AppTabs.vue";
import DataTable from "@/components/DataTable.vue";

const tab = ref("all");
const queries = ref<Record<string, string>>({ all: "", open: "" });
</script>

<template>
  <section class="page">
    <PageHeader title="页签列表" />
    <StatCard
      :items="[
        { title: '订单', value: 12, ratio: 5, onClick: () => (tab = 'all') },
        { title: '完成', value: 3, ratio: -2 },
        { title: '空值', value: null },
        { title: '金额', value: '20', format: 'money' },
      ]"
    />
    <AppTabs v-model:active="tab" sync-query="tab" :items="[{ key: 'all', label: '全部', count: 12 }, { key: 'open', label: '进行中', count: 0 }]" @change="queries[tab] = queries[tab]" />
    <label class="fld">名称<input v-model="queries[tab]" /></label>
    <DataTable :columns="[{ key: 'name', label: '名称' }]" :data="queries[tab] ? [{ id: '1', name: queries[tab] }] : []" />
  </section>
</template>

<style scoped>
input { height: 30px; border: 1px solid var(--line2); border-radius: var(--control-r); }
</style>
