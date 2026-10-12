<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import Perm from "@/components/Perm.vue";
import StatusTag from "@/components/StatusTag.vue";
import { systemApi, type Row } from "@/api/system";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { requiredRule } from "@/components/form/rules";

const types = ref<Row[]>([]);
const values = ref<Row[]>([]);
const current = ref("");
const typeOpen = ref(false);
const typeEditing = ref<Row | null>(null);
const typeForm = ref<Row>({ dictType: "", name: "", remark: "" });
const valueOpen = ref(false);
const valueEditing = ref(false);
const valueForm = ref<Row>({ dictType: "", dictValue: "", dictLabel: "", colorType: "neutral", sort: 0, remark: "" });
const colors = ["primary", "success", "warning", "danger", "info", "neutral", "purple", "cyan", "yellow"];

const columns: TableColumn[] = [
  { key: "dictLabel", label: "名称" },
  { key: "dictValue", label: "值", type: "mono" },
  { key: "colorType", label: "颜色" },
  { key: "status", label: "状态", type: "status", dictType: "dict_common_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "编辑", perm: "ims:system:dict:update", onClick: (row) => openValue(row) },
      { label: "删除", perm: "ims:system:dict:delete", danger: true, show: (row) => !row.isBuiltin, onClick: (row) => void removeValue(row) },
    ],
  },
];

async function loadTypes() {
  types.value = await systemApi.dictTypes();
  if (!current.value && types.value.length) await pick(String(types.value[0].dictType || ""));
}

async function pick(dictType: string) {
  current.value = dictType;
  values.value = await systemApi.dictValues(dictType);
}

function openType(row?: Row) {
  typeEditing.value = row || null;
  typeForm.value = row ? { id: row.id, name: row.name, remark: row.remark || "", status: row.status } : { dictType: "", name: "" };
  typeOpen.value = true;
}

async function saveType(model: Row) {
  if (typeEditing.value) return systemApi.dictTypeUpdate(model);
  return systemApi.dictTypeCreate(model);
}

async function removeType(row: Row) {
  try {
    await confirm({ title: "删除字典", message: "仅没有字典值的类型可以删除。", danger: true, action: async () => { await systemApi.dictTypeDelete(String(row.id)); } });
    if (current.value === row.dictType) current.value = "";
    await loadTypes();
  } catch { /* 取消 */ }
}

function openValue(row?: Row) {
  valueEditing.value = Boolean(row);
  valueForm.value = row
    ? { id: row.id, dictType: current.value, dictValue: row.dictValue, dictLabel: row.dictLabel, colorType: row.colorType || "neutral", sort: row.sort || 0, remark: row.remark || "", status: row.status }
    : { dictType: current.value, dictValue: "", dictLabel: "", colorType: "neutral", sort: 0, remark: "" };
  valueOpen.value = true;
}

async function saveValue(model: Row) {
  return systemApi.dictValueSave({ ...model, dictType: current.value }, valueEditing.value);
}

async function removeValue(row: Row) {
  try {
    await confirm({ title: "删除字典值", message: "内置值不能删除。", danger: true, action: async () => { await systemApi.dictValueDelete(String(row.id)); } });
    toast.success("删除成功");
    await pick(current.value);
  } catch { /* 取消 */ }
}

onMounted(() => { void loadTypes(); });
</script>

<template>
  <section>
    <PageHeader title="字典">
      <template #actions>
        <Perm code="ims:system:dict:create"><button class="btn btn-pri" type="button" @click="openType()">新建字典</button></Perm>
      </template>
    </PageHeader>
    <div class="split">
      <aside>
        <button v-for="item in types" :key="String(item.id)" type="button" :class="{ on: item.dictType === current }" @click="pick(String(item.dictType))">
          {{ item.name }}
          <Perm code="ims:system:dict:update"><em @click.stop="openType(item)">改</em></Perm>
          <Perm code="ims:system:dict:delete"><em @click.stop="removeType(item)">删</em></Perm>
        </button>
      </aside>
      <div>
        <div class="bar">
          <StatusTag dict-type="dict_common_status" :value="String(types.find((item) => item.dictType === current)?.status || '')" />
          <Perm code="ims:system:dict:create"><button class="btn btn-sec" type="button" :disabled="!current" @click="openValue()">新增字典值</button></Perm>
        </div>
        <DataTable :columns="columns" :data="values" />
      </div>
    </div>
    <FormDrawer v-model:open="typeOpen" :title="typeEditing ? '编辑字典' : '新建字典'" :model="typeForm" :rules="typeEditing ? { name: requiredRule('名称') } : { name: requiredRule('名称'), dictType: requiredRule('类型编码') }" :submit="saveType" @saved="loadTypes">
      <el-form-item v-if="!typeEditing" label="类型编码" prop="dictType"><el-input v-model="typeForm.dictType" placeholder="dict_ 开头" /></el-form-item>
      <el-form-item label="名称" prop="name"><el-input v-model="typeForm.name" /></el-form-item>
      <el-form-item v-if="typeEditing" label="备注"><el-input v-model="typeForm.remark" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="valueOpen" :title="valueEditing ? '编辑字典值' : '新增字典值'" :model="valueForm" :rules="{ dictLabel: requiredRule('名称'), dictValue: requiredRule('值') }" :submit="saveValue" @saved="pick(current)">
      <el-form-item label="名称" prop="dictLabel"><el-input v-model="valueForm.dictLabel" /></el-form-item>
      <el-form-item label="值" prop="dictValue"><el-input v-model="valueForm.dictValue" :disabled="Boolean(valueForm.isBuiltin)" /></el-form-item>
      <el-form-item label="颜色">
        <el-select v-model="valueForm.colorType"><el-option v-for="item in colors" :key="item" :label="item" :value="item" /></el-select>
      </el-form-item>
      <el-form-item label="排序"><el-input v-model="valueForm.sort" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="valueForm.remark" /></el-form-item>
    </FormDrawer>
  </section>
</template>

<style scoped>
.split { display: flex; gap: 16px; }
aside { width: 240px; display: flex; flex-direction: column; gap: 4px; }
aside button { text-align: left; }
aside button.on { font-weight: 700; }
.bar { display: flex; justify-content: space-between; margin-bottom: 8px; }
</style>
