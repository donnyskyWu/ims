<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { BarChart, FunnelChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import EmptyState from "./EmptyState.vue";

echarts.use([BarChart, LineChart, PieChart, FunnelChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const props = withDefaults(
  defineProps<{ type: "bar" | "line" | "pie" | "funnel"; data: { name: string; value: number }[]; height?: number }>(),
  { height: 300 },
);
const host = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function colors(): string[] {
  const style = getComputedStyle(document.documentElement);
  return ["--blue", "--green", "--orange", "--purple", "--cyan", "--yellow", "--red", "--gray"].map((token) => style.getPropertyValue(token).trim());
}

function render() {
  if (!host.value || !props.data.length) {
    chart?.dispose();
    chart = null;
    return;
  }
  chart = chart || echarts.init(host.value);
  const palette = colors();
  const option =
    props.type === "pie" || props.type === "funnel"
      ? { color: palette, series: [{ type: props.type, data: props.data }] }
      : {
          color: palette,
          xAxis: { type: "category", data: props.data.map((item) => item.name) },
          yAxis: { type: "value" },
          series: [{ type: props.type, data: props.data.map((item) => item.value) }],
        };
  chart.setOption(option);
}

function onResize() {
  chart?.resize();
}

onMounted(() => {
  render();
  window.addEventListener("resize", onResize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
  chart?.dispose();
});
watch(() => [props.data, props.type], render, { deep: true });
</script>

<template>
  <EmptyState v-if="!data.length" />
  <div v-else ref="host" :style="{ height: height + 'px' }" />
</template>
