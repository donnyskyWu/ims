<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import FilterChip from "@/components/FilterChip.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Timeline from "@/components/Timeline.vue";
import { confirm } from "@/components/confirm";
import { call } from "@/api/generated/endpoints";
import { toast } from "@/utils/toast";
import { moneyRule, requiredRule } from "@/components/form/rules";

const route = useRoute();
const router = useRouter();
const query = ref<Record<string, unknown>>({ name: "", status: "", owner: "", dept: "", code: "", mobile: "" });
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(Number(route.query.pageNo || 1));
const pageSize = ref(Number(route.query.pageSize || 10));
const loading = ref(false);
const sort = reactive({ sortField: "", sortOrder: "" });
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref<Record<string, unknown>>({ name: "", amount: "", mobile: "", rate: "" });
const detail = ref(false);
const current = ref<Record<string, unknown> | null>(null);

const fields: QueryField[] = [
  { key: "name", label: "名称", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_demo_status" },
  { key: "owner", label: "负责人", type: "user" },
  { key: "dept", label: "部门", type: "dept" },
  { key: "code", label: "编号", type: "input" },
  { key: "mobile", label: "手机号", type: "input" },
];

const columns: TableColumn[] = [
  { key: "code", label: "编号", type: "mono" },
  { key: "name", label: "名称" },
  { key: "amount", label: "金额", type: "money", sortable: true },
  { key: "status", label: "状态", type: "status", dictType: "dict_demo_status" },
  { key: "idCard", label: "证件号", type: "masked" },
  { key: "cost", label: "成本", type: "masked" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "查看", perm: "ims:demo:order:query", onClick: (row) => openDetail(row) },
      { label: "编辑", perm: "ims:demo:order:update", onClick: (row) => openEdit(row) },
      { label: "作废", perm: "ims:demo:order:update", onClick: (row) => void voidOrder(row) },
      { label: "复制", perm: "ims:demo:order:create", onClick: (row) => openCopy(row) },
      { label: "删除", perm: "ims:demo:order:delete", danger: true, onClick: (row) => void remove(row) },
    ],
  },
];

const chips = () =>
  fields
    .filter((field) => query.value[field.key])
    .map((field) => ({ key: field.key, label: `${field.label}：${query.value[field.key]}` }));

async function load() {
  loading.value = true;
  try {
    const data = await call<{ list: Record<string, unknown>[]; total: number }>("order_page_admin_api_ims_demo_order_page_get", {
      query: { pageNo: pageNo.value, pageSize: pageSize.value, ...sort, name: query.value.name, status: query.value.status },
      silent: true,
    });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

function syncPage() {
  void router.replace({ query: { ...route.query, pageNo: String(pageNo.value), pageSize: String(pageSize.value) } });
}

function openCreate() {
  editing.value = null;
  form.value = { name: "", amount: "", mobile: "", rate: "" };
  drawer.value = true;
}
function openEdit(row: Record<string, unknown>) {
  editing.value = row;
  form.value = { ...row };
  drawer.value = true;
}
function openCopy(row: Record<string, unknown>) {
  editing.value = null;
  form.value = { name: row.name, amount: row.amount };
  drawer.value = true;
}
async function save(model: Record<string, unknown>) {
  if (editing.value?.id) {
    return call("order_update_admin_api_ims_demo_order_update_put", { body: { ...model, id: editing.value.id }, silent: true });
  }
  pageNo.value = 1;
  return call("order_create_admin_api_ims_demo_order_create_post", { body: model, silent: true });
}
async function openDetail(row: Record<string, unknown>) {
  current.value = await call("order_get_admin_api_ims_demo_order_get_get", { query: { id: row.id }, inDrawer: true });
  detail.value = true;
}
async function remove(row: Record<string, unknown>) {
  await confirm({
    title: "删除",
    message: "确定删除这条记录？",
    danger: true,
    action: async () => {
      await call("order_delete_admin_api_ims_demo_order_delete_delete", { query: { id: row.id }, silent: true });
      toast.success("删除成功");
      if (rows.value.length === 1 && pageNo.value > 1) pageNo.value -= 1;
      await load();
    },
  });
}
async function voidOrder(row: Record<string, unknown>) {
  await confirm({
    title: "作废",
    message: "确定作废这条记录？",
    danger: true,
    reasonRequired: true,
    action: async () => {
      await call("order_update_admin_api_ims_demo_order_update_put", { body: { id: row.id, status: "CLOSED" }, silent: true });
      await load();
    },
  });
}

onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="列表示例">
      <template #actions>
        <button v-perm="'ims:demo:order:create'" class="btn btn-pri" type="button" @click="openCreate">新建</button>
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <FilterChip :items="chips()" closable @close="query[$event] = ''; pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" @sort-change="sort.sortField = $event.sortField; sort.sortOrder = $event.sortOrder; load()" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="syncPage(); load()" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑' : '新建'" :model="form" :rules="{ name: [requiredRule('名称')], amount: [moneyRule] }" :submit="save" @saved="load()">
      <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="金额" prop="amount"><el-input v-model="form.amount" /></el-form-item>
      <el-form-item label="手机号" prop="mobile"><el-input v-model="form.mobile" /></el-form-item>
      <el-form-item label="比例" prop="rate"><el-input v-model="form.rate" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detail" :title="String(current?.name || '详情')" status-dict="dict_demo_status" :status-value="String(current?.status || '')" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'rel', label: '关联' }, { key: 'log', label: '时间线' }]" @refresh="load()">
      <template #base>
        <DescriptionList :items="[{ label: '名称', value: current?.name }, { label: '金额', value: current?.amount, type: 'money' }, { label: '证件号', value: current?.idCard, type: 'masked' }]" />
      </template>
      <template #log>
        <Timeline :items="[{ time: String(current?.createTime || ''), title: '创建', detail: String(current?.name || '') }]" />
      </template>
    </DetailDrawer>
  </section>
</template>
