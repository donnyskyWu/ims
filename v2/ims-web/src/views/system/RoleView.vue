<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import AppModal from "@/components/AppModal.vue";
import AppTabs from "@/components/AppTabs.vue";
import Perm from "@/components/Perm.vue";
import UserSelect from "@/components/UserSelect.vue";
import PositionSelect from "@/components/PositionSelect.vue";
import { systemApi, type Row } from "@/api/system";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";
import { requiredRule } from "@/components/form/rules";

interface MenuNode {
  id: string;
  name: string;
  permCode: string;
  type: string;
  children: MenuNode[];
}

const router = useRouter();
const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const query = ref<Row>({ keyword: "", status: "" });
const drawer = ref(false);
const editing = ref<Row | null>(null);
const form = ref<Row>({ name: "", roleKey: "", remark: "", dataScope: "SELF" });
const configOpen = ref(false);
const current = ref<Row | null>(null);
const tab = ref("menu");
const tree = ref<MenuNode[]>([]);
const checked = ref<string[]>([]);
const treeRef = ref<{ getCheckedKeys: (leaf?: boolean) => string[]; getHalfCheckedKeys: () => string[] }>();
const perms = ref<Row[]>([]);
const members = ref<Row[]>([]);
const memberId = ref<string | null>(null);
const previewUser = ref<string | null>(null);
const preview = ref<Row | null>(null);
const deleteOpen = ref(false);
const confirmName = ref("");
const deleteError = ref("");
const positionCode = ref("");
const scopes = [
  { label: "全部数据", value: "ALL" },
  { label: "本部门", value: "DEPT" },
  { label: "本组", value: "IP_GROUP" },
  { label: "仅本人", value: "SELF" },
];
const fields: QueryField[] = [
  { key: "keyword", label: "名称或编码", type: "input" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_role_status" },
];

const columns: TableColumn[] = [
  { key: "name", label: "角色" },
  { key: "roleKey", label: "编码", type: "mono" },
  { key: "permSummary", label: "权限" },
  { key: "dataScopeText", label: "数据范围" },
  { key: "memberCount", label: "成员", type: "number" },
  { key: "status", label: "状态", type: "status", dictType: "dict_role_status" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    width: 220,
    actions: [
      { label: "配置", perm: "ims:system:role:update", onClick: (row) => void openConfig(row) },
      { label: "编辑", perm: "ims:system:role:update", onClick: (row) => openEdit(row) },
      { label: "停用", perm: "ims:system:role:update", show: (row) => row.status === "ENABLED", onClick: (row) => void setStatus(row, "DISABLED") },
      { label: "启用", perm: "ims:system:role:update", show: (row) => row.status !== "ENABLED", onClick: (row) => void setStatus(row, "ENABLED") },
      { label: "删除", perm: "ims:system:role:delete", danger: true, onClick: (row) => openDelete(row) },
    ],
  },
];

const positionText = computed(() => {
  const names = current.value?.positionNames;
  return Array.isArray(names) && names.length ? names.map(String).join("、") : "未关联";
});

function nodes(raw: unknown): MenuNode[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const row = item as Row;
    return {
      id: String(row.id),
      name: String(row.name || ""),
      permCode: String(row.permCode || ""),
      type: String(row.type || ""),
      children: nodes(row.children),
    };
  });
}

function flatten(list: MenuNode[]): MenuNode[] {
  return list.flatMap((item) => [item, ...flatten(item.children)]);
}

async function load() {
  loading.value = true;
  try {
    const data = await systemApi.rolePage({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { name: "", roleKey: "", remark: "", dataScope: "SELF" };
  drawer.value = true;
}

function openEdit(row: Row) {
  editing.value = row;
  form.value = { id: row.id, name: row.name, roleKey: row.roleKey, remark: row.remark || "", dataScope: row.dataScope || "SELF" };
  drawer.value = true;
}

async function save(model: Row) {
  const saved = await systemApi.roleSave(model, Boolean(editing.value));
  if (model.dataScope) await systemApi.roleScope(String(saved.id || model.id), String(model.dataScope));
  return saved;
}

async function openConfig(row: Row) {
  current.value = row;
  tab.value = "menu";
  if (!tree.value.length) tree.value = nodes(await systemApi.menuTree());
  checked.value = Array.isArray(row.menuIds) ? row.menuIds.map(String) : [];
  const saved = new Map((Array.isArray(row.permDetails) ? (row.permDetails as Row[]) : []).map((item) => [String(item.permCode), item]));
  perms.value = flatten(tree.value)
    .filter((item) => item.permCode)
    .map((item) => {
      const hit = saved.get(item.permCode);
      return { permCode: item.permCode, name: item.name, r: Boolean(hit?.r), w: Boolean(hit?.w), d: Boolean(hit?.d) };
    });
  members.value = await systemApi.roleMembers(String(row.id));
  preview.value = null;
  configOpen.value = true;
}

async function saveMenus() {
  if (!current.value || !treeRef.value) return;
  const menuIds = [...treeRef.value.getCheckedKeys(false), ...treeRef.value.getHalfCheckedKeys()];
  await systemApi.roleMenus(String(current.value.id), menuIds);
  toast.success("菜单已保存");
  await load();
}

function touchPerm(row: Row, key: "w" | "d") {
  row[key] = !row[key];
  if (row[key]) row.r = true;
}

async function savePerms() {
  if (!current.value) return;
  const details = perms.value
    .filter((item) => item.r || item.w || item.d)
    .map((item) => ({ permCode: item.permCode, r: Boolean(item.r), w: Boolean(item.w), d: Boolean(item.d) }));
  await systemApi.rolePerms(String(current.value.id), details);
  toast.success("功能点已保存");
  await load();
}

async function addMember() {
  if (!current.value || !memberId.value) return;
  await systemApi.roleMemberAdd(String(current.value.id), memberId.value);
  members.value = await systemApi.roleMembers(String(current.value.id));
  memberId.value = null;
}

async function removeMember(row: Row) {
  if (!current.value) return;
  await systemApi.roleMemberRemove(String(current.value.id), String(row.userId));
  members.value = await systemApi.roleMembers(String(current.value.id));
}

async function runPreview() {
  if (!current.value || !previewUser.value) return;
  preview.value = await systemApi.rolePreview(String(current.value.id), previewUser.value);
}

async function setStatus(row: Row, status: string) {
  await systemApi.roleStatus(String(row.id), status);
  await load();
}

function openDelete(row: Row) {
  current.value = row;
  confirmName.value = "";
  deleteError.value = "";
  deleteOpen.value = true;
}

async function removeRole() {
  if (!current.value) return;
  deleteError.value = "";
  try {
    await systemApi.roleDelete(String(current.value.id), confirmName.value);
    toast.success("删除成功");
    deleteOpen.value = false;
    await load();
  } catch (caught) {
    deleteError.value = (caught as BizError).msg || "删除失败";
  }
}

async function fromPosition() {
  if (!positionCode.value) return;
  const data = await systemApi.roleFromPosition(positionCode.value);
  toast.success(String(data.hint || (data.existed ? "该岗位已有角色" : "已生成待配置角色")));
  await load();
}

function names(value: unknown): string {
  if (!Array.isArray(value)) return "";
  return value.map((item) => String((item as Row).name || (item as Row).permCode || "")).filter(Boolean).join("、");
}

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="角色" sub-title="钉钉岗位只读，请到岗位-角色供给规则维护。">
      <template #actions>
        <Perm code="ims:system:role:create"><button class="btn btn-pri" type="button" @click="openCreate">新建角色</button></Perm>
      </template>
    </PageHeader>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <div class="from">
      <PositionSelect v-model="positionCode" mode="query" />
      <Perm code="ims:system:role:create"><button class="btn btn-sec" type="button" @click="fromPosition">从岗位生成</button></Perm>
      <button class="btn btn-txt" type="button" @click="router.push('/ims/auth/position')">去岗位规则</button>
    </div>
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑角色' : '新建角色'" :model="form" :rules="{ name: requiredRule('角色名称'), roleKey: requiredRule('角色编码') }" :submit="save" @saved="load">
      <el-form-item label="名称" prop="name"><el-input v-model="form.name" maxlength="50" /></el-form-item>
      <el-form-item label="编码" prop="roleKey"><el-input v-model="form.roleKey" maxlength="64" /></el-form-item>
      <el-form-item label="数据范围">
        <el-select v-model="form.dataScope"><el-option v-for="item in scopes" :key="item.value" :label="item.label" :value="item.value" /></el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" maxlength="255" /></el-form-item>
      <p class="muted">钉钉岗位不能在此修改。{{ editing ? '保存后仍请到岗位规则维护。' : '' }}</p>
    </FormDrawer>
    <DetailDrawer v-model:open="configOpen" :title="String(current?.name || '角色配置')" size="L">
      <p class="hint">钉钉岗位：{{ positionText }}。{{ current?.positionHint || "请到岗位-角色供给规则维护" }}</p>
      <AppTabs v-model:active="tab" :items="[{ key: 'menu', label: '菜单' }, { key: 'perm', label: '功能点' }, { key: 'member', label: '成员' }, { key: 'preview', label: '预览' }]" />
      <div v-if="tab === 'menu'">
        <el-tree :key="String(current?.id || '')" ref="treeRef" :data="tree" node-key="id" show-checkbox default-expand-all :default-checked-keys="checked" :props="{ label: 'name', children: 'children' }" />
        <Perm code="ims:system:role:update"><button class="btn btn-pri" type="button" @click="saveMenus">保存菜单</button></Perm>
      </div>
      <div v-else-if="tab === 'perm'">
        <table class="grid">
          <thead><tr><th>功能</th><th>读</th><th>写</th><th>删</th></tr></thead>
          <tbody>
            <tr v-for="item in perms" :key="String(item.permCode)">
              <td>{{ item.name }}</td>
              <td><el-checkbox v-model="item.r" /></td>
              <td><el-checkbox :model-value="Boolean(item.w)" @change="touchPerm(item, 'w')" /></td>
              <td><el-checkbox :model-value="Boolean(item.d)" @change="touchPerm(item, 'd')" /></td>
            </tr>
          </tbody>
        </table>
        <Perm code="ims:system:role:grant"><button class="btn btn-pri" type="button" @click="savePerms">保存功能点</button></Perm>
      </div>
      <div v-else-if="tab === 'member'">
        <div class="from">
          <UserSelect v-model="memberId" />
          <Perm code="ims:system:role:update"><button class="btn btn-sec" type="button" @click="addMember">添加</button></Perm>
        </div>
        <ul>
          <li v-for="item in members" :key="String(item.userId)">
            {{ item.nickname }}（{{ item.username }}）{{ item.sourceText }}
            <span v-if="item.manualRemoved">已移除</span>
            <Perm code="ims:system:role:update"><button v-if="!item.manualRemoved" class="btn btn-txt" type="button" @click="removeMember(item)">移除</button></Perm>
          </li>
        </ul>
      </div>
      <div v-else>
        <div class="from">
          <UserSelect v-model="previewUser" />
          <button class="btn btn-sec" type="button" @click="runPreview">对比</button>
        </div>
        <template v-if="preview">
          <p>将增加</p>
          <p>{{ names(preview.added) || "无" }}</p>
          <p>将减少</p>
          <p>{{ names(preview.removed) || "无" }}</p>
        </template>
      </div>
    </DetailDrawer>
    <AppModal v-model:open="deleteOpen" title="删除角色" :width="520">
      <p>请输入角色名称「{{ current?.name }}」以确认删除。</p>
      <el-input v-model="confirmName" />
      <p v-if="deleteError" class="ferr">{{ deleteError }}</p>
      <template #footer>
        <button class="btn btn-sec" type="button" @click="deleteOpen = false">取消</button>
        <button class="btn btn-pri" type="button" @click="removeRole">删除</button>
      </template>
    </AppModal>
  </section>
</template>

<style scoped>
.from { display: flex; gap: 8px; align-items: center; margin: 8px 0; }
.hint { color: var(--text2); font-size: 13px; }
.grid { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.grid td, .grid th { border-bottom: 1px solid var(--line); text-align: left; padding: 4px 8px; }
</style>
