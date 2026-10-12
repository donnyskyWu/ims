<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import AppModal from "@/components/AppModal.vue";
import AppTabs from "@/components/AppTabs.vue";
import Perm from "@/components/Perm.vue";
import PositionSelect from "@/components/PositionSelect.vue";
import RoleSelect from "@/components/RoleSelect.vue";
import { call } from "@/api/generated/endpoints";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";
import { requiredRule } from "@/components/form/rules";

const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const overview = ref<Record<string, unknown>>({});
const query = ref<Record<string, unknown>>({ keyword: "", positionCode: "", status: "" });
const drawer = ref(false);
const editing = ref<Record<string, unknown> | null>(null);
const form = ref<Record<string, unknown>>({ ruleName: "", positionCode: "", mainRoleId: "", extraRoleIds: [], description: "", baseVersion: 0 });
const detailOpen = ref(false);
const detail = ref<Record<string, unknown> | null>(null);
const detailTab = ref("base");
const versions = ref<Record<string, unknown>[]>([]);
const members = ref<Record<string, unknown>[]>([]);
const memberOpen = ref(false);
const deleteOpen = ref(false);
const deleteTarget = ref<Record<string, unknown> | null>(null);
const confirmText = ref("");
const previewOpen = ref(false);
const preview = ref<Record<string, unknown> | null>(null);
const statusFilter = ref("");

const cards = computed<StatItem[]>(() => [
  { title: "钉钉岗位", value: num(overview.value.positionCount), desc: `钉钉 ${num(overview.value.dingtalkCount)} / 本地 ${num(overview.value.localCount)}` },
  { title: "已供给角色", value: num(overview.value.enabledRuleCount), onClick: () => { statusFilter.value = "ENABLED"; void load(); } },
  { title: "自动创建待配置", value: num(overview.value.pendingRoleCount), onClick: () => { query.value.pending = "1"; void load(); } },
  { title: "无人员岗位", value: num(overview.value.emptyPositionCount) },
]);

const fields: QueryField[] = [{ key: "keyword", label: "规则名称", type: "input" }];
const columns: TableColumn[] = [
  { key: "ruleName", label: "规则名称" },
  { key: "positionName", label: "岗位" },
  { key: "version", label: "版本" },
  { key: "status", label: "状态", type: "status", dictType: "dict_position_rule_status" },
  { key: "appliedUserCount", label: "套用人数", type: "number" },
  { key: "updateTime", label: "更新时间", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "查看", onClick: (row) => void openDetail(row) },
      { label: "编辑", perm: "ims:auth:position-rule:update", onClick: (row) => openEdit(row) },
      { label: "停用", perm: "ims:auth:position-rule:update", onClick: (row) => void toggle(row) },
      {
        label: "删除",
        perm: "ims:auth:position-rule:delete",
        danger: true,
        disabled: (row) => Number(row.appliedUserCount || 0) > 0 || row.status === "ARCHIVED",
        hint: (row) => (Number(row.appliedUserCount || 0) > 0 ? "请先处理在用人员（调岗或刷新规则）后删除" : ""),
        onClick: (row) => openDelete(row),
      },
      { label: "成员", onClick: (row) => void openMembers(row) },
    ],
  },
];

function num(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function loadOverview() {
  overview.value = await call("position_overview_admin_api_ims_auth_position_overview_get", { silent: true });
}

async function load() {
  loading.value = true;
  try {
    const data = await call<{ list: Record<string, unknown>[]; total: number }>("position_rules_admin_api_ims_auth_position_rules_get", {
      query: { pageNo: pageNo.value, pageSize: 10, keyword: query.value.keyword, positionCode: query.value.positionCode, status: statusFilter.value, pendingConfig: query.value.pending },
      silent: true,
    });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = { ruleName: "", positionCode: "", mainRoleId: "", extraRoleIds: [], description: "", baseVersion: 0 };
  drawer.value = true;
}

function openEdit(row: Record<string, unknown>) {
  if (row.status === "ARCHIVED") return;
  editing.value = row;
  const roles = (row.roles as { roleId: string; roleType: string }[]) || [];
  form.value = {
    ruleName: row.ruleName,
    positionCode: row.positionCode,
    mainRoleId: roles.find((item) => item.roleType === "MAIN")?.roleId || "",
    extraRoleIds: roles.filter((item) => item.roleType === "EXTRA").map((item) => item.roleId),
    description: row.description || "",
    baseVersion: row.version,
  };
  drawer.value = true;
}

async function save(model: Record<string, unknown>, replaceExisting = false): Promise<unknown> {
  try {
    if (editing.value?.id) {
      return await call("position_rule_update_admin_api_ims_auth_position_rules__ident__put", {
        pathParams: { ident: String(editing.value.id) },
        body: { ...model, baseVersion: editing.value.version },
        silent: true,
      });
    }
    return await call("position_rule_create_admin_api_ims_auth_position_rules_post", {
      body: { ...model, replaceExisting },
      idempotent: true,
      tokenKey: `rule-${model.ruleName}`,
      silent: true,
    });
  } catch (caught) {
    const biz = caught as BizError;
    if (biz.code === 1281) {
      const data = biz.data as { existingRuleName?: string; existingVersion?: number; appliedUserCount?: number };
      await confirm({
        title: "替换绑定",
        message: `岗位已绑定启用规则「${data.existingRuleName || ""}」v${data.existingVersion || ""}（在用 ${data.appliedUserCount || 0} 人）。确认后原规则停用。`,
        action: async () => {
          await save(model, true);
        },
      });
      return {};
    }
    throw caught;
  }
}

async function toggle(row: Record<string, unknown>) {
  const enable = row.status !== "ENABLED";
  const path = enable
    ? "position_rule_enable_admin_api_ims_auth_position_rules__ident__enable_post"
    : "position_rule_disable_admin_api_ims_auth_position_rules__ident__disable_post";
  await confirm({
    title: enable ? "启用规则" : "停用规则",
    message: enable ? "启用后，之后入职或调岗到该岗位的人员将按本规则授予角色。" : "停用后，新入职或调岗到该岗位的人员将不会被自动授予任何角色。",
    action: async () => {
      await call(path, { pathParams: { ident: String(row.id) }, silent: true });
      toast.success("保存成功");
    },
  });
  await load();
}

function openDelete(row: Record<string, unknown>) {
  if (Number(row.appliedUserCount || 0) > 0) return;
  deleteTarget.value = row;
  confirmText.value = "";
  deleteOpen.value = true;
}

async function remove() {
  if (!deleteTarget.value) return;
  await call("position_rule_delete_admin_api_ims_auth_position_rules__ident__delete", {
    pathParams: { ident: String(deleteTarget.value.id) },
    query: { confirmText: confirmText.value },
    silent: true,
  });
  toast.success("删除成功");
  deleteOpen.value = false;
  await load();
}

async function openDetail(row: Record<string, unknown>) {
  detail.value = await call("position_rule_get_admin_api_ims_auth_position_rules__ident__get", { pathParams: { ident: String(row.id) }, inDrawer: true });
  const history = await call<{ list: Record<string, unknown>[] }>("position_rule_versions_admin_api_ims_auth_position_rules__ident__versions_get", {
    pathParams: { ident: String(row.id) },
    silent: true,
  });
  versions.value = history.list || [];
  detailOpen.value = true;
}

async function openMembers(row: Record<string, unknown>) {
  detail.value = row;
  const data = await call<{ list: Record<string, unknown>[] }>("position_rule_users_admin_api_ims_auth_position_rules__ident__users_get", {
    pathParams: { ident: String(row.id) },
    inDrawer: true,
  });
  members.value = data.list || [];
  memberOpen.value = true;
}

async function refreshAll() {
  if (!detail.value?.id) return;
  preview.value = await call("position_refresh_preview_admin_api_ims_auth_position_rules__ident__refresh_preview_post", {
    pathParams: { ident: String(detail.value.id) },
    body: { allOutdated: true },
    silent: true,
  });
  previewOpen.value = true;
}

async function confirmRefresh() {
  if (!detail.value?.id) return;
  const data = await call<{ changed: number; unchanged: number }>("position_refresh_admin_api_ims_auth_position_rules__ident__refresh_post", {
    pathParams: { ident: String(detail.value.id) },
    body: { allOutdated: true },
    idempotent: true,
    tokenKey: `refresh-${detail.value.id}`,
    silent: true,
  });
  toast.success(`已刷新 ${data.changed} 人（无变化 ${data.unchanged} 人）`);
  previewOpen.value = false;
}

onMounted(() => {
  void loadOverview();
  void load();
});
</script>

<template>
  <section>
    <PageHeader title="岗位-角色供给规则">
      <template #actions>
        <Perm code="ims:auth:position-rule:create">
          <button class="btn btn-pri" type="button" @click="openCreate">新建规则</button>
        </Perm>
      </template>
    </PageHeader>
    <StatCard :items="cards" />
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; statusFilter = ''; load()" />
    <div class="filters">
      <PositionSelect v-model="query.positionCode as string" mode="query" />
      <RoleSelect v-model="query.roleId as string" allow-inactive />
    </div>
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <p class="muted">失败关闭 · 一个岗位一条启用规则 · 岗位消失且无人员时归档</p>
    <FormDrawer v-model:open="drawer" :title="editing ? `编辑规则 v${editing.version}` : '新建规则'" size="M" :model="form" :rules="{ ruleName: requiredRule('规则名称') }" :submit="save" @saved="load">
      <label class="fld">规则名称<input v-model="form.ruleName" maxlength="64" /></label>
      <label class="fld">岗位<PositionSelect v-model="form.positionCode as string" :mode="editing ? 'edit' : 'create'" /></label>
      <label class="fld">主角色<RoleSelect v-model="form.mainRoleId as string" /></label>
      <label class="fld">附加角色<RoleSelect v-model="form.extraRoleIds as string[]" multiple /></label>
      <label class="fld">说明<textarea v-model="form.description as string" maxlength="200" /></label>
    </FormDrawer>
    <DetailDrawer v-model:open="detailOpen" :title="String(detail?.ruleName || '规则详情')" size="M" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'versions', label: '版本历史' }]">
      <AppTabs v-model:active="detailTab" :items="[{ key: 'base', label: '基本信息' }, { key: 'versions', label: '版本历史' }]" />
      <DescriptionList v-if="detail && detailTab === 'base'" :items="[
        { label: '规则名称', value: String(detail.ruleName || '') },
        { label: '岗位', value: String(detail.positionName || '') },
        { label: '版本', value: `v${detail.version || ''}` },
        { label: '套用人数', value: String(detail.appliedUserCount ?? '') },
        { label: '说明', value: String(detail.description || '') },
      ]" />
      <ul v-else>
        <li v-for="item in versions" :key="String(item.id)">v{{ item.version }} {{ item.changeType }} {{ item.operatorText }} {{ item.createTime }}</li>
      </ul>
    </DetailDrawer>
    <DetailDrawer v-model:open="memberOpen" title="套用人员" size="M">
      <Perm code="ims:auth:position-rule:refresh">
        <button class="btn btn-sec" type="button" @click="refreshAll">全部旧版本按新版本刷新</button>
      </Perm>
      <DataTable :columns="[{ key: 'nickname', label: '姓名' }, { key: 'empNo', label: '工号' }, { key: 'deptName', label: '主部门' }, { key: 'ruleVersion', label: '版本' }, { key: 'status', label: '状态', type: 'status', dictType: 'dict_common_status' }]" :data="members" />
    </DetailDrawer>
    <AppModal v-model:open="deleteOpen" title="删除规则" :width="520">
      <p>删除后不可恢复。若仍有人员以该岗位入职，系统会自动重新生成规则。请输入规则名称「{{ deleteTarget?.ruleName }}」确认删除。</p>
      <input v-model="confirmText" />
      <template #footer>
        <button class="btn btn-danger-txt" type="button" :disabled="confirmText !== deleteTarget?.ruleName" @click="remove">删除</button>
      </template>
    </AppModal>
    <AppModal v-model:open="previewOpen" title="刷新预览" :width="800">
      <p>将影响 {{ preview?.count || 0 }} 人，增加角色 {{ preview?.addTimes || 0 }} 次，移除角色 {{ preview?.removeTimes || 0 }} 次。</p>
      <template #footer>
        <button class="btn btn-pri" type="button" @click="confirmRefresh">确认刷新</button>
      </template>
    </AppModal>
  </section>
</template>

<style scoped>
section { display: flex; flex-direction: column; gap: 12px; }
.filters { display: flex; gap: 8px; }
ul { margin: 0; padding-left: 18px; }
</style>
