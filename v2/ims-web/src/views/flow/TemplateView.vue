<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import Perm from "@/components/Perm.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { flowApi, type Row } from "./api";
import { blankFlow, type FlowNode } from "./designer";
import DesignerPanel from "./DesignerPanel.vue";

const router = useRouter();
const query = ref<Record<string, unknown>>({ templateName: "", businessDomain: "", status: "" });
const fields: QueryField[] = [
  { key: "templateName", label: "名称", type: "input" },
  { key: "businessDomain", label: "业务域", type: "dict", dictType: "dict_flow_domain" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_flow_tpl_status" },
];
const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const open = ref(false);
const editing = ref<string>("");
const nodes = ref<FlowNode[]>(blankFlow());
const form = ref<Row>({ templateName: "", businessDomain: "COMMON", bizType: "" });

const columns: TableColumn[] = [
  { key: "templateName", label: "模板" },
  { key: "businessDomain", label: "业务域", type: "status", dictType: "dict_flow_domain" },
  { key: "version", label: "版本", type: "number" },
  { key: "status", label: "状态", type: "status", dictType: "dict_flow_tpl_status" },
  { key: "nodeCount", label: "节点数", type: "number" },
  { key: "publishedAt", label: "发布时间", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "编辑", perm: "ims:flow:template:create", show: (row) => row.status === "DRAFT" || row.status === "PUBLISHED", onClick: (row) => void edit(row) },
      { label: "发布", perm: "ims:flow:template:publish", show: (row) => row.status === "DRAFT", onClick: (row) => void publish(String(row.id)) },
      { label: "停用", perm: "ims:flow:template:publish", show: (row) => row.status === "PUBLISHED", onClick: (row) => void disable(String(row.id)) },
      { label: "删除", perm: "ims:flow:template:delete", danger: true, show: (row) => row.status === "DRAFT", onClick: (row) => void remove(String(row.id)) },
      { label: "版本", perm: "ims:flow:template:query", onClick: (row) => void router.push(`/ims/flow/version/${row.id}`) },
    ],
  },
];

async function load() {
  const data = await flowApi.templates({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list || [];
  total.value = data.total || 0;
}

function create() {
  editing.value = "";
  nodes.value = blankFlow();
  form.value = { templateName: "", businessDomain: "COMMON", bizType: "" };
  open.value = true;
}

async function edit(row: Row) {
  editing.value = String(row.id);
  if (row.status === "PUBLISHED") {
    const draft = await flowApi.reviseTemplate(editing.value);
    nodes.value = (draft.nodes as FlowNode[]) || blankFlow();
    form.value = { templateName: draft.templateName, businessDomain: draft.businessDomain, bizType: draft.bizType };
  } else {
    nodes.value = (row.nodes as FlowNode[]) || blankFlow();
    form.value = { templateName: row.templateName, businessDomain: row.businessDomain, bizType: row.bizType };
  }
  open.value = true;
}

async function save(model: Row) {
  const body = { ...model, nodes: nodes.value };
  if (editing.value) return flowApi.updateTemplate(editing.value, body);
  return flowApi.createTemplate(body);
}

async function publish(id: string) {
  await flowApi.publishTemplate(id);
  toast.success("已发布");
  await load();
}

async function disable(id: string) {
  await flowApi.disableTemplate(id);
  toast.success("已停用");
  await load();
}

async function remove(id: string) {
  try {
    await confirm({ title: "删除草稿", message: "只删除尚未发布的草稿。", danger: true, action: async () => { await flowApi.deleteTemplate(id); } });
    await load();
  } catch {
    /* 取消 */
  }
}

onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="模板管理" sub-title="账号领用、数据上报和培训审批已预置">
      <template #actions>
        <Perm code="ims:flow:template:create"><button class="btn btn-pri" type="button" @click="create">新建模板</button></Perm>
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="() => { pageNo = 1; load(); }" @reset="load" />
    <DataTable :columns="columns" :data="rows" @retry="load" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <FormDrawer v-model:open="open" :title="editing ? '编辑模板' : '新建模板'" size="L" :model="form" :submit="save" @saved="load">
      <label>名称<input v-model="form.templateName" maxlength="128" /></label>
      <label>业务域
        <select v-model="form.businessDomain">
          <option value="ADMIN">行政</option>
          <option value="FINANCE">财务</option>
          <option value="BUSINESS">业务</option>
          <option value="COMMON">通用</option>
        </select>
      </label>
      <label>业务类型<input v-model="form.bizType" placeholder="自定义编码，请假和报销可自配" /></label>
      <DesignerPanel v-model="nodes" />
    </FormDrawer>
  </section>
</template>

<style scoped>
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
</style>
