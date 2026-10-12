<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import LeftTreeLayout from "@/layouts/LeftTreeLayout.vue";
import DeptTree from "@/components/DeptTree.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import AppModal from "@/components/AppModal.vue";
import Perm from "@/components/Perm.vue";
import ExportButton from "@/components/ExportButton.vue";
import DeptTreeSelect from "@/components/DeptTreeSelect.vue";
import RoleSelect from "@/components/RoleSelect.vue";
import PositionSelect from "@/components/PositionSelect.vue";
import PageHeader from "@/components/PageHeader.vue";
import { systemApi, type Row } from "@/api/system";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { lengthRule, mobileRule, requiredRule } from "@/components/form/rules";

const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const deptId = ref<string | null>(null);
const includeChildren = ref(true);
const query = ref<Row>({ username: "", nickname: "", mobile: "", status: "" });
const drawer = ref(false);
const editing = ref(false);
const form = ref<Row>({ username: "", nickname: "", mobile: "", password: "", empNo: "", deptIds: [], mainDeptId: "", roleIds: [], positionCode: "" });
const detailOpen = ref(false);
const detail = ref<Row | null>(null);
const passwordOpen = ref(false);
const plainPassword = ref("");

const fields: QueryField[] = [
  { key: "username", label: "用户名", type: "input" },
  { key: "nickname", label: "姓名", type: "input" },
  { key: "mobile", label: "手机号", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_user_status" },
];

const alive = (row: Row) => row.status !== "RESIGNED";
const columns: TableColumn[] = [
  { key: "username", label: "用户名", type: "mono" },
  { key: "nickname", label: "姓名" },
  { key: "mainDeptName", label: "主部门" },
  { key: "mobile", label: "手机", type: "masked" },
  { key: "status", label: "状态", type: "status", dictType: "dict_user_status" },
  { key: "lastLoginTime", label: "最近登录", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    width: 220,
    fixed: "right",
    actions: [
      { label: "查看", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:system:user:update", show: alive, onClick: (row) => void openEdit(row) },
      { label: "冻结", perm: "ims:system:user:update", show: (row) => row.status === "ACTIVE", onClick: (row) => void act(row, "freeze", "冻结该用户？") },
      { label: "解冻", perm: "ims:system:user:update", show: (row) => row.status === "FROZEN", onClick: (row) => void act(row, "unfreeze", "解冻该用户？") },
      { label: "离职", perm: "ims:system:user:update", show: alive, danger: true, onClick: (row) => void act(row, "resign", "办理离职后将不能登录。") },
      { label: "重置密码", perm: "ims:system:user:reset-pwd", show: alive, onClick: (row) => void resetPwd(row) },
      { label: "解锁", perm: "ims:system:user:unlock", show: (row) => Boolean(row.locked), onClick: (row) => void act(row, "unlock", "解除登录锁定？") },
      { label: "下线", perm: "ims:system:user:kick", show: (row) => row.status === "ACTIVE", onClick: (row) => void act(row, "kick", "强制下线该用户的全部会话？") },
      { label: "删除", perm: "ims:system:user:delete", danger: true, show: (row) => alive(row) && !row.lastLoginTime, onClick: (row) => void remove(row) },
    ],
  },
];

const rules = {
  username: [requiredRule("用户名"), lengthRule(4, 30, "用户名")],
  nickname: requiredRule("姓名"),
  mobile: [requiredRule("手机号"), mobileRule],
  password: requiredRule("初始密码"),
  mainDeptId: requiredRule("主部门"),
};

async function load() {
  loading.value = true;
  try {
    const data = await systemApi.userPage({
      ...query.value,
      deptId: deptId.value || "",
      includeChildren: includeChildren.value ? "true" : "false",
      pageNo: pageNo.value,
      pageSize: pageSize.value,
    });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

function onDept(id: string | null) {
  deptId.value = id;
  pageNo.value = 1;
  void load();
}

watch(includeChildren, () => {
  pageNo.value = 1;
  void load();
});

function blankForm() {
  form.value = { username: "", nickname: "", mobile: "", password: "", empNo: "", deptIds: deptId.value ? [deptId.value] : [], mainDeptId: deptId.value || "", roleIds: [], positionCode: "" };
}

function openCreate() {
  editing.value = false;
  blankForm();
  drawer.value = true;
}

async function openEdit(row: Row) {
  const data = await systemApi.userGet(String(row.id));
  editing.value = true;
  form.value = {
    id: data.id,
    username: data.username,
    nickname: data.nickname,
    mobile: "",
    empNo: data.empNo || "",
    deptIds: asIds(data.deptIds),
    mainDeptId: data.mainDeptId ? String(data.mainDeptId) : "",
    roleIds: asIds(data.roleIds),
    positionCode: data.positionCode ? String(data.positionCode) : "",
  };
  drawer.value = true;
}

function asIds(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

async function save(model: Row) {
  const body = { ...model };
  if (editing.value) delete body.password;
  if (!body.positionCode) body.positionCode = "";
  return systemApi.userSave(body, editing.value);
}

async function openDetail(row: Row) {
  detail.value = await systemApi.userGet(String(row.id));
  detailOpen.value = true;
}

async function act(row: Row, action: string, message: string) {
  try {
    await confirm({ title: "确认", message, danger: action === "resign", action: async () => { await systemApi.userAction(String(row.id), action); } });
    toast.success("已完成");
    await load();
  } catch { /* 取消 */ }
}

async function resetPwd(row: Row) {
  try {
    let password = "";
    await confirm({
      title: "重置密码",
      message: `将重置 ${String(row.nickname || row.username)} 的密码，原会话会下线。`,
      action: async () => {
        const data = await systemApi.userAction(String(row.id), "reset-password");
        password = String(data.password || "");
      },
    });
    plainPassword.value = password;
    passwordOpen.value = true;
    await load();
  } catch { /* 取消 */ }
}

async function remove(row: Row) {
  try {
    await confirm({
      title: "删除用户",
      message: "仅从未登录且无引用的用户可以删除。",
      danger: true,
      action: async () => { await systemApi.userDelete(String(row.id)); },
    });
    toast.success("删除成功");
    await load();
  } catch { /* 取消 */ }
}

const detailItems = () => {
  const row = detail.value || {};
  const roles = Array.isArray(row.roles) ? (row.roles as Row[]).map((item) => String(item.name || "")).filter(Boolean).join("、") : "";
  const depts = Array.isArray(row.deptNames) ? (row.deptNames as string[]).join("、") : "";
  return [
    { label: "用户名", value: String(row.username || "") },
    { label: "姓名", value: String(row.nickname || "") },
    { label: "主部门", value: String(row.mainDeptName || "") },
    { label: "部门", value: depts },
    { label: "角色", value: roles },
    { label: "手机", value: String(row.mobile || "") },
    { label: "钉钉", value: row.dingtalkBound ? "已绑定" : "未绑定" },
  ];
};

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="用户" sub-title="左侧部门树，右侧人员。同步只触发全量对账。" />
    <LeftTreeLayout>
      <template #tree>
        <DeptTree v-model:selected="deptId" v-model:include-children="includeChildren" @select="onDept" />
      </template>
      <template #main>
        <div class="bar">
          <label class="switch"><el-switch v-model="includeChildren" /> 含下级</label>
          <Perm code="ims:system:user:export"><ExportButton :export-api="systemApi.userExport" :params="{ ...query, deptId, includeChildren }" /></Perm>
          <Perm code="ims:system:user:create"><button class="btn btn-pri" type="button" @click="openCreate">新建用户</button></Perm>
        </div>
        <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
        <DataTable :columns="columns" :data="rows" :loading="loading" />
        <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
      </template>
    </LeftTreeLayout>
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑用户' : '新建用户'" :model="form" :rules="editing ? { nickname: rules.nickname, mainDeptId: rules.mainDeptId } : rules" :submit="save" @saved="load">
      <el-form-item label="用户名" prop="username"><el-input v-model="form.username" :disabled="editing" maxlength="30" /></el-form-item>
      <el-form-item label="姓名" prop="nickname"><el-input v-model="form.nickname" maxlength="50" /></el-form-item>
      <el-form-item label="手机号" prop="mobile"><el-input v-model="form.mobile" maxlength="11" :placeholder="editing ? '留空表示不修改' : ''" /></el-form-item>
      <el-form-item v-if="!editing" label="初始密码" prop="password"><el-input v-model="form.password" type="password" show-password /></el-form-item>
      <el-form-item label="工号"><el-input v-model="form.empNo" /></el-form-item>
      <el-form-item label="部门" prop="deptIds"><DeptTreeSelect v-model="form.deptIds as string[]" multiple /></el-form-item>
      <el-form-item label="主部门" prop="mainDeptId"><DeptTreeSelect v-model="form.mainDeptId as string" /></el-form-item>
      <el-form-item label="角色"><RoleSelect v-model="form.roleIds as string[]" multiple /></el-form-item>
      <el-form-item label="岗位"><PositionSelect v-model="form.positionCode as string" :mode="editing ? 'edit' : 'create'" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" title="用户详情">
      <DescriptionList :items="detailItems()" />
    </DetailDrawer>
    <AppModal v-model:open="passwordOpen" title="新密码" :width="360">
      <p>请复制后告知用户，关闭后不再显示。</p>
      <p class="mono">{{ plainPassword }}</p>
    </AppModal>
  </section>
</template>

<style scoped>
.bar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; margin-bottom: 8px; }
.switch { display: inline-flex; align-items: center; gap: 6px; margin-right: auto; font-size: 13px; }
.mono { font-family: ui-monospace, monospace; }
</style>
