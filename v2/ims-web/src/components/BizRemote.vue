<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { pageOf, type MasterRow } from "@/demo/master-data";

const props = withDefaults(
  defineProps<{
    rows: MasterRow[];
    multiple?: boolean;
    placeholder?: string;
    accountId?: string;
    platform?: string;
    status?: string;
    ipGroupId?: string;
    showCertWarning?: boolean;
    tree?: boolean;
  }>(),
  { multiple: false, placeholder: "请选择", showCertWarning: false, tree: false },
);
const model = defineModel<string | string[] | null>({ default: null });

function flat(rows: MasterRow[], parent = ""): MasterRow[] {
  return rows.flatMap((row) => {
    const current = { ...row, parentLabel: parent || row.parentLabel };
    return [current, ...flat(row.children || [], row.label)];
  });
}

function toOption(row: MasterRow): RemoteOption {
  const path = props.tree && row.parentLabel ? `${row.parentLabel} / ${row.label}` : row.label;
  return {
    id: row.id,
    label: path,
    extra: props.showCertWarning && row.certExpired ? "证件已过期" : "",
  };
}

function fetch(keyword: string, pageNo: number) {
  let rows = props.tree ? flat(props.rows) : props.rows;
  if (props.accountId) rows = rows.filter((row) => row.accountId === props.accountId);
  if (props.platform) rows = rows.filter((row) => row.platform === props.platform);
  if (props.status) rows = rows.filter((row) => row.status === props.status);
  if (props.ipGroupId) rows = rows.filter((row) => row.ipGroupId === props.ipGroupId);
  const page = pageOf(rows, keyword, pageNo);
  return Promise.resolve({ list: page.list.map(toOption), total: page.total });
}

function fetchByIds(ids: string[]) {
  const rows = (props.tree ? flat(props.rows) : props.rows).filter((row) => ids.includes(row.id));
  return Promise.resolve(rows.map(toOption));
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" :placeholder="placeholder" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
