<script setup lang="ts">
import { ref } from "vue";
import StatCard from "@/components/StatCard.vue";
import Timeline from "@/components/Timeline.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import MoneyText from "@/components/MoneyText.vue";
import PercentText from "@/components/PercentText.vue";
import MaskedText from "@/components/MaskedText.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import FlowDesigner from "@/components/FlowDesigner.vue";
import PageHeader from "@/components/PageHeader.vue";
import PeriodPicker from "@/components/PeriodPicker.vue";

const period = ref("2026-10");
const selected = ref("");
const nodes = [
  { id: "n1", label: "开始", x: 80, y: 80 },
  { id: "n2", label: "审批", x: 240, y: 140 },
];
const failed = ref(false);
</script>

<template>
  <section class="page">
    <PageHeader title="展示" sub-title="截至 2026-10-12 10:05" />
    <PeriodPicker v-model="period" type="month" />
    <StatCard :items="[{ title: '金额', value: '1234.5', format: 'money' }, { title: '负数', value: '-20', format: 'money' }, { title: '比例', value: 5, format: 'percent' }, { title: '空', value: null }]" />
    <p><MoneyText value="1234.5" /> <MoneyText value="-20" /> <PercentText :value="5" /> <MaskedText value="138****5678" /> <MaskedText value="***" /></p>
    <DescriptionList :items="[{ label: '说明', value: '这是一段很长的说明文字，应当完整换行显示而不是被截断。' }, { label: '空值', value: '' }, { label: '时间', value: '2026-10-12T10:05:00', type: 'time' }]" />
    <Timeline :items="[{ time: '2026-10-12T10:05:00', title: '提交', operator: '张敏', detail: '补充说明' }, { time: '2026-10-11T09:00:00', title: '创建' }]" />
    <div class="charts">
      <ChartPanel type="bar" :data="[{ name: '甲', value: 4 }, { name: '乙', value: 7 }]" />
      <ChartPanel type="line" :data="[{ name: '甲', value: 2 }, { name: '乙', value: 5 }]" />
      <ChartPanel type="pie" :data="[{ name: '甲', value: 2 }, { name: '乙', value: 5 }]" />
      <ChartPanel type="funnel" :data="failed ? [] : [{ name: '甲', value: 8 }, { name: '乙', value: 3 }]" />
    </div>
    <button class="btn btn-txt" type="button" @click="failed = !failed">切换空数据</button>
    <FlowDesigner :nodes="nodes" :edges="[{ from: 'n1', to: 'n2' }]" :selected="selected" @node-click="selected = $event" />
  </section>
</template>

<style scoped>
h1 { font-size: 28px; }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
