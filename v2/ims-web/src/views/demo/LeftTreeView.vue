<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import LeftTreeLayout from "@/layouts/LeftTreeLayout.vue";
import DeptTree from "@/components/DeptTree.vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DeptTreeSelect from "@/components/DeptTreeSelect.vue";
import EmptyState from "@/components/EmptyState.vue";
import { call } from "@/api/generated/endpoints";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { useDeptStore } from "@/stores/dept";
import { deptPath, findDept } from "@/components/dept/tree-logic";

const route = useRoute();
const router = useRouter();
const dept = useDeptStore();
const selected = ref<string | null>(typeof route.query.deptId === "string" ? route.query.deptId : null);
const includeChildren = ref(route.query.inc !== "0");
const query = ref<Record<string, unknown>>({ keyword: typeof route.query.keyword === "string" ? route.query.keyword : "", status: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(Number(route.query.pageNo || 1));
const pageSize = ref(10);
const open = ref(false);
const form = ref<Record<string, unknown>>({ username: "", nickname: "", password: "", deptIds: [] as string[], mainDeptId: "" });
const missing = ref(false);

const fields: QueryField[] = [
  { key: "keyword", label: "姓名", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_user_status" },
];
const pathText = computed(() => {
  if (!selected.value) return "全部";
  const node = findDept(dept.tree, selected.value);
  if (!node) return "全部";
  return deptPath(dept.tree, selected.value).map((item) => item.name).join(" / ");
});
const current = computed(() => findDept(dept.tree, selected.value));
const emptyText = computed(() => (current.value && current.value.memberCount > 0 && rows.value.length === 0 ? "当前统计范围内暂无人员" : ""));

const columns: TableColumn[] = [
  { key: "nickname", label: "姓名" },
  { key: "username", label: "用户名", type: "mono" },
  { key: "mainDeptName", label: "主部门" },
  { key: "deptText", label: "所属部门" },
  { key: "status", label: "状态", type: "status", dictType: "dict_user_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "调整部门", perm: "ims:system:user:update", onClick: (row) => void moveUser(row) },
      { label: "删除", perm: "ims:system:user:delete", danger: true, onClick: (row) => void removeUser(row) },
    ],
  },
];

function writeUrl() {
  const queryState: Record<string, string> = { pageNo: String(pageNo.value) };
  if (selected.value) queryState.deptId = selected.value;
  queryState.inc = includeChildren.value ? "1" : "0";
  if (query.value.keyword) queryState.keyword = String(query.value.keyword);
  void router.replace({ query: queryState });
}

async function load() {
  const data = await call<{ list: Record<string, unknown>[]; total: number }>("user_page_admin_api_ims_system_user_page_get", {
    query: {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      deptId: selected.value || undefined,
      includeChildren: includeChildren.value,
      keyword: query.value.keyword,
      status: query.value.status,
    },
    silent: true,
  });
  rows.value = (data.list || []).map((row) => ({
    ...row,
    mainDeptName: dept.nameOf(String(row.mainDeptId || "")),
    deptText: dept.nameOf(String(row.mainDeptId || "")),
  }));
  total.value = Number(data.total || 0);
  if (selected.value && !findDept(dept.tree, selected.value) && dept.loaded) {
    missing.value = true;
    toast.error("所选部门已不存在");
    selected.value = null;
  }
}

function onSelect(id: string | null) {
  selected.value = id;
  pageNo.value = 1;
  writeUrl();
  void load();
}

function openCreate() {
  const node = current.value;
  const preset = node && node.status === "ENABLED" && node.source !== "SYSTEM" ? node.id : "";
  form.value = { username: "", nickname: "", password: "", deptIds: preset ? [preset] : [], mainDeptId: preset };
  open.value = true;
}

async function save(model: Record<string, unknown>) {
  const created = await call("user_create_admin_api_ims_system_user_create_post", { body: model, silent: true });
  await dept.reload();
  pageNo.value = 1;
  await load();
  return created;
}

async function moveUser(row: Record<string, unknown>) {
  form.value = { id: row.id, deptIds: [String(row.mainDeptId || "")], mainDeptId: String(row.mainDeptId || "") };
  await confirm({
    title: "调整部门",
    message: "请在下方选择部门后确定",
    action: async () => {
      if (!form.value.mainDeptId) throw new Error("请先指定其他主部门");
      await call("update_depts_admin_api_ims_system_user_update_depts_put", {
        body: { id: row.id, deptIds: form.value.deptIds, mainDeptId: form.value.mainDeptId },
        silent: true,
      });
      await dept.reload();
      await load();
    },
  });
}

async function removeUser(row: Record<string, unknown>) {
  await confirm({
    title: "删除人员",
    message: `确定删除「${row.nickname || row.username}」？`,
    danger: true,
    action: async () => {
      await call("user_delete_admin_api_ims_system_user_delete_delete", { query: { id: row.id }, silent: true });
      await dept.reload();
      await load();
    },
  });
}

onMounted(async () => {
  await dept.load();
  if (selected.value && !findDept(dept.tree, selected.value)) {
    toast.error("所选部门已不存在");
    selected.value = null;
  }
  await load();
});

watch(includeChildren, () => {
  pageNo.value = 1;
  writeUrl();
  void load();
});
</script>

<template>
  <section>
    <PageHeader title="人员" />
    <LeftTreeLayout>
      <template #tree>
        <DeptTree v-model:selected="selected" v-model:include-children="includeChildren" @select="onSelect" />
      </template>
      <template #main>
        <p>当前：{{ pathText }}</p>
        <label v-if="selected && current?.source !== 'SYSTEM'">含下级 <button class="sw" :class="{ on: includeChildren }" type="button" @click="includeChildren = !includeChildren"><i /></button></label>
        <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
        <EmptyState v-if="missing" type="empty" desc="所选部门已不存在" />
        <DataTable :columns="columns" :data="rows" :empty-text="emptyText" />
        <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="writeUrl(); load()" />
        <button v-perm="'ims:system:user:create'" class="btn btn-pri" type="button" @click="openCreate">新建人员</button>
        <FormDrawer v-model:open="open" title="新建人员" :model="form" :submit="save">
          <el-form-item label="用户名" prop="username"><el-input v-model="form.username" /></el-form-item>
          <el-form-item label="姓名" prop="nickname"><el-input v-model="form.nickname" /></el-form-item>
          <el-form-item label="密码" prop="password"><el-input v-model="form.password" type="password" /></el-form-item>
          <el-form-item label="所属部门"><DeptTreeSelect :model-value="form.deptIds as string[]" multiple @update:model-value="form.deptIds = $event || []" /></el-form-item>
          <el-form-item label="主部门"><DeptTreeSelect v-model="form.mainDeptId as string" /></el-form-item>
        </FormDrawer>
      </template>
    </LeftTreeLayout>
  </section>
</template>
