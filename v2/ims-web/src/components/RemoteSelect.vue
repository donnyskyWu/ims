<script setup lang="ts">
import { computed, ref, watch } from "vue";

export interface RemoteOption {
  id: string;
  label: string;
  disabled?: boolean;
  reason?: string;
  missing?: boolean;
  extra?: string;
}

const props = withDefaults(
  defineProps<{
    multiple?: boolean;
    fetch: (keyword: string, pageNo: number) => Promise<{ list: RemoteOption[]; total: number }>;
    fetchByIds?: (ids: string[]) => Promise<RemoteOption[]>;
    placeholder?: string;
  }>(),
  { multiple: false, placeholder: "请选择" },
);
const model = defineModel<string | string[] | null>({ default: null });
const options = ref<RemoteOption[]>([]);
const keyword = ref("");
const pageNo = ref(1);
const total = ref(0);
const loading = ref(false);
let timer = 0;

const selectedIds = computed(() => {
  if (Array.isArray(model.value)) return model.value.filter(Boolean);
  return model.value ? [model.value] : [];
});

async function load(reset = false) {
  if (reset) {
    pageNo.value = 1;
    options.value = [];
  }
  loading.value = true;
  try {
    const result = await props.fetch(keyword.value.trim(), pageNo.value);
    total.value = result.total;
    const incoming = result.list.filter((item) => !options.value.some((old) => old.id === item.id));
    options.value = reset ? result.list : [...options.value, ...incoming];
  } finally {
    loading.value = false;
  }
}

async function hydrate() {
  const missing = selectedIds.value.filter((id) => !options.value.some((item) => item.id === id));
  if (!missing.length || !props.fetchByIds) return;
  const rows = await props.fetchByIds(missing);
  const found = new Set(rows.map((item) => item.id));
  const ghosts = missing
    .filter((id) => !found.has(id))
    .map((id) => ({ id, label: "（已不可用）", missing: true, disabled: true }));
  options.value = [...rows, ...ghosts, ...options.value.filter((item) => !missing.includes(item.id))];
}

watch(selectedIds, () => void hydrate(), { immediate: true });

function onFilter(value: string) {
  keyword.value = value;
  window.clearTimeout(timer);
  timer = window.setTimeout(() => void load(true), 300);
}

function onScroll(event: Event) {
  const target = event.target as HTMLElement;
  if (loading.value || options.value.length >= total.value) return;
  if (target.scrollTop + target.clientHeight >= target.scrollHeight - 8) {
    pageNo.value += 1;
    void load(false);
  }
}

</script>

<template>
  <el-select
    :model-value="model"
    :multiple="multiple"
    :placeholder="placeholder"
    filterable
    remote
    clearable
    :remote-method="onFilter"
    :loading="loading"
    collapse-tags
    :max-collapse-tags="3"
    @update:model-value="model = $event"
    @visible-change="(open: boolean) => open && load(true)"
  >
    <template #default>
      <div class="panel" @scroll="onScroll">
        <el-option
          v-for="item in options"
          :key="item.id"
          :label="item.label"
          :value="item.id"
          :disabled="item.disabled"
        >
          <el-tooltip v-if="item.disabled && item.reason" :content="item.reason" placement="right">
            <span class="disabled">{{ item.label }}</span>
          </el-tooltip>
          <span v-else :class="{ warn: item.extra }">{{ item.label }}<em v-if="item.extra">{{ item.extra }}</em></span>
        </el-option>
      </div>
    </template>
  </el-select>
</template>

<style scoped>
.panel { max-height: 240px; overflow: auto; }
.disabled { color: var(--text2); }
.warn { color: inherit; }
em { margin-left: 6px; color: var(--red); font-style: normal; }
</style>
