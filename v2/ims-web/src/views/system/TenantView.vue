<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AppModal from "@/components/AppModal.vue";
import Perm from "@/components/Perm.vue";
import { systemApi, type Row } from "@/api/system";
import { BizError } from "@/api/http";
import { toast } from "@/utils/toast";
import { requiredRule } from "@/components/form/rules";

const tab = ref("tenant");
const rows = ref<Row[]>([]);
const packages = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const blocked = ref("");
const drawer = ref(false);
const editing = ref<Row | null>(null);
const form = ref<Row>({});
const menuOpen = ref(false);
const menuIds = ref<string[]>([]);
const tree = ref<Row[]>([]);
const treeRef = ref<{ getCheckedKeys: (leaf?: boolean) => string[]; getHalfCheckedKeys: () => string[] }>();
const deleteOpen = ref(false);
const confirmName = ref("");
const deleteError = ref("");

const tenantColumns: TableColumn[] = [
  { key: "name", label: "租户" },
  { key: "contactName", label: "联系人" },
  { key: "packageName", label: "套餐" },
  { key: "expireTime", label: "到期", type: "time" },
  { key: "status", label: "状态", type: "status", dictType: "dict_common_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "编辑", perm: "ims:tenant:update", onClick: (row) => openTenant(row) },
      { label: "停用", perm: "ims:tenant:update", show: (row) => String(row.id) !== "1" && row.status === "ENABLED", onClick: (row) => void setTenantStatus(row, "DISABLED") },
      { label: "启用", perm: "ims:tenant:update", show: (row) => String(row.id) !== "1" && row.status !== "ENABLED", onClick: (row) => void setTenantStatus(row, "ENABLED") },
    ],
  },
];
const packageColumns: TableColumn[] = [
  { key: "packageName", label: "套餐" },
  { key: "remark", label: "备注" },
  { key: "status", label: "状态", type: "status", dictType: "dict_common_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "编辑", perm: "ims:tenant:package:update", onClick: (row) => openPackage(row) },
      { label: "菜单", perm: "ims:tenant:package:update", onClick: (row) => void openMenus(row) },
      { label: "删除", perm: "ims:tenant:package:update", danger: true, onClick: (row) => openDelete(row) },
    ],
  },
];

async function load() {
  loading.value = true;
  blocked.value = "";
  try {
    if (tab.value === "tenant") {
      const data = await systemApi.tenantPage({ pageNo: pageNo.value, pageSize: pageSize.value });
      rows.value = data.list || [];
      total.value = Number(data.total || 0);
      const packs = await systemApi.packagePage({ pageNo: 1, pageSize: 100 });
      packages.value = packs.list || [];
    } else {
      const data = await systemApi.packagePage({ pageNo: pageNo.value, pageSize: pageSize.value });
      packages.value = data.list || [];
      total.value = Number(data.total || 0);
    }
  } catch (caught) {
    const biz = caught as BizError;
    if (biz.code === 1291 || biz.code === 1008) blocked.value = biz.msg || "非平台租户不可访问";
  } finally {
    loading.value = false;
  }
}

function openTenant(row?: Row) {
  editing.value = row || null;
  form.value = row
    ? { name: row.name, contactName: row.contactName || "", expireTime: "", packageId: row.packageId ? String(row.packageId) : "", status: row.status }
    : { name: "", contactName: "", expireTime: "", packageId: "", adminUsername: "", adminNickname: "", adminMobile: "", adminPassword: "" };
  drawer.value = true;
}

function openPackage(row?: Row) {
  editing.value = row || null;
  form.value = row ? { packageName: row.packageName, remark: row.remark || "", status: row.status } : { packageName: "", remark: "", status: "ENABLED" };
  drawer.value = true;
}

async function save(model: Row) {
  if (tab.value === "tenant") {
    const saved = await systemApi.tenantSave(model, editing.value ? String(editing.value.id) : undefined);
    if (editing.value && model.packageId) await systemApi.tenantPackage(String(editing.value.id), String(model.packageId));
    return saved;
  }
  return systemApi.packageSave(model, editing.value ? String(editing.value.id) : undefined);
}

async function setTenantStatus(row: Row, status: string) {
  await systemApi.tenantSave({ status }, String(row.id));
  toast.success("已更新");
  await load();
}

async function openMenus(row: Row) {
  editing.value = row;
  if (!tree.value.length) tree.value = await systemApi.menuTree();
  menuIds.value = Array.isArray(row.menuIds) ? row.menuIds.map(String) : [];
  menuOpen.value = true;
}

async function saveMenus() {
  if (!editing.value || !treeRef.value) return;
  const ids = [...treeRef.value.getCheckedKeys(false), ...treeRef.value.getHalfCheckedKeys()];
  await systemApi.packageMenus(String(editing.value.id), ids);
  toast.success("套餐菜单已保存");
  menuOpen.value = false;
  await load();
}

function openDelete(row: Row) {
  editing.value = row;
  confirmName.value = "";
  deleteError.value = "";
  deleteOpen.value = true;
}

async function removePackage() {
  if (!editing.value) return;
  try {
    await systemApi.packageDelete(String(editing.value.id), confirmName.value);
    toast.success("删除成功");
    deleteOpen.value = false;
    await load();
  } catch (caught) {
    deleteError.value = (caught as BizError).msg || "删除失败";
  }
}

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="租户套餐" sub-title="仅平台租户可管理。过期与停用使用同一登录拦截。续费页不在本批。">
      <template #actions>
        <Perm v-if="tab === 'tenant'" code="ims:tenant:update"><button class="btn btn-pri" type="button" @click="openTenant()">新建租户</button></Perm>
        <Perm v-else code="ims:tenant:package:update"><button class="btn btn-pri" type="button" @click="openPackage()">新建套餐</button></Perm>
      </template>
    </PageHeader>
    <p v-if="blocked" class="ferr">{{ blocked }}</p>
    <AppTabs v-model:active="tab" :items="[{ key: 'tenant', label: '租户' }, { key: 'package', label: '套餐' }]" @change="pageNo = 1; load()" />
    <DataTable :columns="tab === 'tenant' ? tenantColumns : packageColumns" :data="tab === 'tenant' ? rows : packages" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑' : '新建'" :model="form" :rules="tab === 'tenant' ? { name: requiredRule('租户名称') } : { packageName: requiredRule('套餐名称') }" :submit="save" @saved="load">
      <template v-if="tab === 'tenant'">
        <el-form-item label="名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.contactName" /></el-form-item>
        <el-form-item label="到期时间"><el-input v-model="form.expireTime" placeholder="YYYY-MM-DD HH:mm:ss" /></el-form-item>
        <el-form-item v-if="editing" label="套餐">
          <el-select v-model="form.packageId" clearable>
            <el-option v-for="item in packages" :key="String(item.id)" :label="String(item.packageName)" :value="String(item.id)" />
          </el-select>
        </el-form-item>
        <template v-else>
          <el-form-item label="套餐" prop="packageId">
            <el-select v-model="form.packageId"><el-option v-for="item in packages" :key="String(item.id)" :label="String(item.packageName)" :value="String(item.id)" /></el-select>
          </el-form-item>
          <el-form-item label="管理员用户名"><el-input v-model="form.adminUsername" /></el-form-item>
          <el-form-item label="管理员姓名"><el-input v-model="form.adminNickname" /></el-form-item>
          <el-form-item label="管理员手机"><el-input v-model="form.adminMobile" /></el-form-item>
          <el-form-item label="管理员密码"><el-input v-model="form.adminPassword" type="password" show-password /></el-form-item>
        </template>
      </template>
      <template v-else>
        <el-form-item label="套餐名称" prop="packageName"><el-input v-model="form.packageName" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      </template>
    </FormDrawer>
    <AppModal v-model:open="menuOpen" title="套餐菜单" :width="520">
      <el-tree :key="String(editing?.id || '')" ref="treeRef" :data="tree" node-key="id" show-checkbox default-expand-all :default-checked-keys="menuIds" :props="{ label: 'name', children: 'children' }" />
      <template #footer>
        <button class="btn btn-sec" type="button" @click="menuOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="saveMenus">保存</button>
      </template>
    </AppModal>
    <AppModal v-model:open="deleteOpen" title="删除套餐" :width="520">
      <p>请输入套餐名称「{{ editing?.packageName }}」。仍被租户使用时不能删除。</p>
      <el-input v-model="confirmName" />
      <p v-if="deleteError" class="ferr">{{ deleteError }}</p>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="deleteOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="removePackage">删除</button>
      </template>
    </AppModal>
  </section>
</template>
