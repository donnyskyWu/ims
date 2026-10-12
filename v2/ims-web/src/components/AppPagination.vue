<script setup lang="ts">
import { computed, watch } from "vue";

const pageNo = defineModel<number>("pageNo", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });
const props = defineProps<{ total: number }>();
const emit = defineEmits<{ change: [payload: { pageNo: number; pageSize: number }] }>();

const maxPage = computed(() => Math.max(1, Math.ceil(props.total / pageSize.value)));

watch(
  () => [props.total, pageNo.value, pageSize.value],
  () => {
    if (props.total === 0) return;
    if (pageNo.value > maxPage.value) {
      pageNo.value = maxPage.value;
      emit("change", { pageNo: pageNo.value, pageSize: pageSize.value });
    }
  },
);

function onSize(size: number) {
  pageSize.value = size;
  pageNo.value = 1;
  emit("change", { pageNo: 1, pageSize: size });
}

function onPage(page: number) {
  pageNo.value = page;
  emit("change", { pageNo: page, pageSize: pageSize.value });
}
</script>

<template>
  <div class="pager">
    <span>共 {{ total }} 条</span>
    <el-pagination
      v-if="total > 0"
      :current-page="pageNo"
      :page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50]"
      layout="sizes, prev, pager, next"
      background
      @size-change="onSize"
      @current-change="onPage"
    />
  </div>
</template>

<style scoped>
.pager { display: flex; justify-content: space-between; align-items: center; padding: 9px 12px; color: var(--text2); font-size: 13px; }
</style>
