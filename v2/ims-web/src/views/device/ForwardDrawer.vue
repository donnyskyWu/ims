<script setup lang="ts">
import { ref, watch } from "vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import AppTabs from "@/components/AppTabs.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import EmptyState from "@/components/EmptyState.vue";
import TraceGraph from "@/components/TraceGraph.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet } from "@/api/resource";

const open = defineModel<boolean>("open", { required: true });
const props = defineProps<{ assetId?: string; realnameId?: string }>();
const tab = ref("layer");
const detail = ref<Record<string, unknown>>({});
const trace = ref<{ nodes: { id: string; label: string; x: number; y: number }[]; edges: { from: string; to: string }[] }>({ nodes: [], edges: [] });

async function load() {
  const id = props.assetId || "0";
  const params: Record<string, unknown> = {};
  if (props.realnameId) params.realnameId = props.realnameId;
  detail.value = await resourceGet(`/asset/forward/detail/${id}`, params);
  trace.value = await resourceGet(`/asset/forward/trace/${id}`, params);
}
async function exportReport() {
  if (!props.assetId) return;
  await confirm({
    title: "导出穿透报告",
    message: "报告生成后请到消息中心领取，链接 300 秒内有效。",
    action: async () => {
      await resourceGet(`/asset/forward/export/${props.assetId}`);
      toast.success("已开始生成");
    },
  });
}
function layers() {
  return (detail.value.layers as Record<string, unknown>[]) || [];
}

watch(open, (value) => {
  if (value) void load();
});
</script>

<template>
  <DetailDrawer v-model:open="open" title="正向穿透" size="XL">
    <p>穿透耗时 {{ detail.elapsedMs || 0 }} 毫秒</p>
    <AppTabs v-model:active="tab" :items="[{ key: 'layer', label: '层级视图' }, { key: 'graph', label: '关系图' }]" />
    <template v-if="tab === 'layer'">
      <section v-for="block in layers()" :key="String(block.layer)">
        <h3>{{ block.title }}</h3>
        <EmptyState v-if="block.empty" :desc="String(block.empty)" />
        <DescriptionList v-if="block.asset" :items="[{ label: '编号', value: (block.asset as Record<string, unknown>).assetCode }, { label: '名称', value: (block.asset as Record<string, unknown>).assetName }, { label: '状态', value: (block.asset as Record<string, unknown>).statusLabel }, { label: '责任人', value: (block.asset as Record<string, unknown>).ownerName }]" />
        <p v-for="person in (block.people as Record<string, unknown>[]) || []" :key="String(person.name)">{{ person.kind }} {{ person.name }} {{ person.idNoMasked }} {{ person.stateLabel }}</p>
        <p v-if="block.costMasked">金额 ¥****</p>
        <p v-if="block.hint">{{ block.hint }}</p>
      </section>
    </template>
    <TraceGraph v-else :nodes="trace.nodes" :edges="trace.edges" />
    <template #footer>
      <button v-perm="'ims:asset:forward:export'" class="btn btn-sec" type="button" @click="exportReport">导出报告</button>
    </template>
  </DetailDrawer>
</template>
