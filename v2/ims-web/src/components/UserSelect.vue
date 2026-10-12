<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { call } from "@/api/generated/endpoints";
import { useDictStore } from "@/stores/dict";

const props = withDefaults(
  defineProps<{ status?: string; permCode?: string; deptId?: string; multiple?: boolean; placeholder?: string }>(),
  { status: "ACTIVE", multiple: false, placeholder: "请选择人员" },
);
const model = defineModel<string | string[] | null>({ default: null });
const dict = useDictStore();

interface UserRow {
  id: string;
  nickname?: string;
  mainDeptName?: string;
  status?: string;
}

function optionOf(row: UserRow, allowDisabled = false): RemoteOption {
  const status = String(row.status || "");
  const blocked = status === "FROZEN" || status === "RESIGNED";
  const statusText = blocked ? dict.label("dict_user_status", status) : "";
  const dept = row.mainDeptName ? `（${row.mainDeptName}）` : "";
  return {
    id: String(row.id),
    label: `${row.nickname || ""}${dept}${statusText && allowDisabled ? ` ${statusText}` : ""}`,
    disabled: blocked && !allowDisabled,
    reason: blocked ? statusText : "",
  };
}

async function fetchPage(keyword: string, pageNo: number) {
  const data = await call<{ list: UserRow[]; total: number }>("user_simple_admin_api_ims_system_user_simple_page_get", {
    query: { pageNo, pageSize: 20, keyword, status: props.status, deptId: props.deptId, permCode: props.permCode },
    silent: true,
  });
  const list = (data.list || []).filter((row) => {
    if (!keyword) return true;
    return String(row.nickname || "").includes(keyword);
  });
  return { list: list.map((row) => optionOf(row)), total: Number(data.total || list.length) };
}

async function fetchByIds(ids: string[]) {
  const data = await call<{ list: UserRow[] }>("user_simple_admin_api_ims_system_user_simple_page_get", {
    query: { pageNo: 1, pageSize: 50, ids: ids.join(",") },
    silent: true,
  });
  const rows = (data.list || []).filter((row) => ids.includes(String(row.id)));
  return rows.map((row) => optionOf(row, true));
}

</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" :placeholder="placeholder" :fetch="fetchPage" :fetch-by-ids="fetchByIds" />
</template>
