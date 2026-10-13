<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import LeftTreeLayout from "@/layouts/LeftTreeLayout.vue";
import EmptyState from "@/components/EmptyState.vue";
import StatusTag from "@/components/StatusTag.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import IpGroupSelect from "@/components/IpGroupSelect.vue";
import AuthorSelect from "@/components/AuthorSelect.vue";
import StatCard from "@/components/StatCard.vue";
import ExportButton from "@/components/ExportButton.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import { useAuthStore } from "@/stores/auth";
import { flattenGroups, nodeText, type GroupNode } from "./logic";

const route = useRoute();
const auth = useAuthStore();
const view = ref(route.name === "ip-group-author" ? "author" : "ops");
const keyword = ref("");
const tree = ref<GroupNode[]>([]);
const selectedId = ref("");
const detailTab = ref("base");
const members = ref<Record<string, unknown>[]>([]);
const accounts = ref<Record<string, unknown>[]>([]);
const accountHint = ref("");
const accountReadOnly = ref(false);
const anchors = ref<Record<string, unknown>[]>([]);
const anchorHint = ref("");
const anchorReadOnly = ref(false);
const stats = ref<Record<string, unknown> | null>(null);
const groupOpen = ref(false);
const groupForm = ref<Record<string, unknown>>({});
const memberOpen = ref(false);
const memberForm = ref<Record<string, unknown>>({});
const editingMember = ref<Record<string, unknown> | null>(null);
const bindOpen = ref(false);
const bindForm = ref<Record<string, unknown>>({ accountIds: [] as string[] });
const anchorOpen = ref(false);
const anchorForm = ref<Record<string, unknown>>({ authorId: "", anchorType: "", isPrimary: false });

const authorQuery = ref<Record<string, unknown>>({ keyword: "", authorType: "", status: "" });
const authorGroupId = ref("");
const authorUserId = ref("");
const authorRows = ref<Record<string, unknown>[]>([]);
const authorTotal = ref(0);
const authorPageNo = ref(1);
const authorPageSize = ref(20);
const authorOpen = ref(false);
const authorForm = ref<Record<string, unknown>>({});
const editingAuthor = ref<Record<string, unknown> | null>(null);
const authorDetailOpen = ref(false);
const authorCurrent = ref<Record<string, unknown> | null>(null);

const pageTabs = computed(() => {
  const items = [{ key: "ops", label: "IP 组运营" }];
  if (auth.permCodes.includes("ims:ip-group:author:query")) items.push({ key: "author", label: "作者管理" });
  return items;
});
const flat = computed(() => flattenGroups(tree.value, keyword.value));
const selected = computed(() => flat.value.find((item) => item.id === selectedId.value) || findNode(tree.value, selectedId.value));
const writable = computed(() => !!selected.value && !selected.value.readonly);
const bigParents = computed(() => flattenGroups(tree.value).filter((item) => item.groupType === "BIG" && item.status !== "DISABLED"));
const authorFields: QueryField[] = [
  { key: "keyword", label: "作者名", type: "input" },
  { key: "authorType", label: "类型", type: "dict", dictType: "dict_author_type" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_author_status" },
];

const memberColumns: TableColumn[] = [
  { key: "userName", label: "姓名" },
  { key: "positionLabel", label: "岗位" },
  { key: "relationLabel", label: "主/兼" },
  { key: "leaderText", label: "是否组长" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "修改", perm: "ims:ip-group:member", show: () => writable.value, onClick: (row) => openMember(row) },
      { label: "移除", perm: "ims:ip-group:member", danger: true, show: () => writable.value, onClick: (row) => void removeMember(row) },
    ],
  },
];
const accountColumns: TableColumn[] = [
  { key: "accountNo", label: "账号编号", type: "mono" },
  { key: "nickname", label: "昵称" },
  { key: "platformLabel", label: "平台" },
  { key: "status", label: "状态", type: "status", dictType: "dict_account_status" },
  { key: "ownerName", label: "责任人" },
  { key: "authorName", label: "作者" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      {
        label: "解绑",
        perm: "ims:ip-group:account",
        danger: true,
        show: () => writable.value && !accountReadOnly.value,
        onClick: (row) => void unbind(row),
      },
    ],
  },
];
const anchorColumns: TableColumn[] = [
  { key: "authorName", label: "作者名" },
  { key: "authorTypeLabel", label: "类型" },
  { key: "primaryText", label: "是否主作者" },
  { key: "userName", label: "绑定用户" },
  { key: "primaryAccountName", label: "主推号" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      {
        label: "设为主作者",
        perm: "ims:ip-group:anchor",
        show: (row) => writable.value && !anchorReadOnly.value && !row.isPrimary,
        onClick: (row) => void makePrimary(row),
      },
      {
        label: "移除",
        perm: "ims:ip-group:anchor",
        danger: true,
        show: () => writable.value && !anchorReadOnly.value,
        onClick: (row) => void removeAnchor(row),
      },
    ],
  },
];
const authorColumns: TableColumn[] = [
  { key: "authorNo", label: "作者编号", type: "mono" },
  { key: "authorName", label: "作者名" },
  { key: "authorTypeLabel", label: "类型" },
  { key: "ipGroupText", label: "归属 IP 组" },
  { key: "userName", label: "绑定用户" },
  { key: "primaryAccountName", label: "主推号" },
  { key: "status", label: "状态", type: "status", dictType: "dict_author_status" },
  { key: "updateTime", label: "更新时间", type: "time" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", onClick: (row) => void openAuthorDetail(row) },
      { label: "编辑", perm: "ims:ip-group:author:update", onClick: (row) => openAuthor(row) },
      { label: "删除", perm: "ims:ip-group:author:delete", danger: true, onClick: (row) => void removeAuthor(row) },
    ],
  },
];

const baseItems = computed(() => {
  const row = selected.value;
  if (!row) return [];
  return [
    { label: "组名", value: row.groupName },
    { label: "类型", value: row.groupType === "SMALL" ? "小组" : "大组" },
    { label: "上级", value: row.parentName || "—" },
    { label: "组长", value: row.leaderName || "—" },
    { label: "等级", value: row.level ? `${row.level}级` : "—" },
    { label: "状态", value: row.status, type: "status" as const, dictType: "dict_ip_group_status" },
    { label: "排序", value: row.sortOrder ?? 0 },
    { label: "备注", value: row.remark || "—" },
    { label: "创建时间", value: row.createTime, type: "time" as const },
    { label: "更新时间", value: row.updateTime, type: "time" as const },
  ];
});
const statItems = computed(() => {
  const row = stats.value || {};
  return [
    { title: "成员数", value: Number(row.memberCount || 0) },
    { title: "账号数", value: Number(row.accountCount || 0) },
    { title: "作者数", value: Number(row.authorCount || 0) },
    { title: "粉丝数", value: Number(row.fans || 0), desc: String(row.mockLabel || "") },
    { title: "作品数", value: Number(row.works || 0), desc: String(row.mockLabel || "") },
    { title: "内部内容", value: Number(row.innerContents || 0), desc: String(row.mockLabel || "") },
    { title: "ROI", value: String(row.roi || "0"), desc: String(row.mockLabel || "") },
    { title: "成本 / 营收", value: `${row.cost || "0"} / ${row.revenue || "0"}`, desc: String(row.mockLabel || "") },
  ];
});

function textOf(value: unknown): string {
  return value == null ? "" : String(value);
}

function single(value: string | string[] | null): string {
  if (Array.isArray(value)) return value[0] || "";
  return value || "";
}

function listOf(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (value == null || value === "") return [];
  return [String(value)];
}

function findNode(nodes: GroupNode[], id: string): GroupNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findNode(node.children || [], id);
    if (child) return child;
  }
  return null;
}

function explain(error: unknown): string {
  const biz = error as BizError;
  const data = biz?.data as { fieldErrors?: { message?: string }[] } | undefined;
  const field = data?.fieldErrors?.[0]?.message;
  if (biz?.code === 1223) return `${biz.msg}。请到关联作者页设置主作者`;
  return field || biz?.msg || "操作失败";
}

async function guard<T>(work: () => Promise<T>): Promise<T> {
  try {
    return await work();
  } catch (error) {
    toast.error(explain(error));
    throw error;
  }
}

function treeUrl() {
  const text = auth.dataScopeText || "";
  if (!text.includes("全部数据") && text.includes("本组")) return "/ip-group/accessible-tree";
  return "/ip-group/tree";
}

async function loadTree() {
  const data = await resourceGet<{ list: GroupNode[] }>(treeUrl());
  tree.value = data.list || [];
  if (selectedId.value && !findNode(tree.value, selectedId.value)) selectedId.value = "";
}

function pick(id: string) {
  selectedId.value = id;
  detailTab.value = "base";
  void loadPane();
}

async function loadPane() {
  if (!selectedId.value) return;
  const id = selectedId.value;
  if (detailTab.value === "member") {
    const data = await resourceGet<{ list: Record<string, unknown>[] }>(`/ip-group/${id}/members`);
    members.value = (data.list || []).map((row) => ({ ...row, leaderText: row.isLeader ? "是" : "否" }));
  }
  if (detailTab.value === "account") {
    const data = await resourceGet<{ list: Record<string, unknown>[]; readOnly?: boolean; hint?: string }>(`/ip-group/${id}/accounts`);
    accounts.value = data.list || [];
    accountReadOnly.value = !!data.readOnly;
    accountHint.value = data.hint || "";
  }
  if (detailTab.value === "anchor") {
    const data = await resourceGet<{ list: Record<string, unknown>[]; readOnly?: boolean; hint?: string }>(`/ip-group/${id}/anchors`);
    anchors.value = (data.list || []).map((row) => ({ ...row, primaryText: row.isPrimary ? "是" : "否" }));
    anchorReadOnly.value = !!data.readOnly;
    anchorHint.value = data.hint || "";
  }
  if (detailTab.value === "stats") stats.value = await resourceGet(`/ip-group/${id}/stats`);
}

function openBig() {
  groupForm.value = { groupName: "", groupType: "BIG", parentId: "", leaderUserId: "", level: "", sortOrder: 0, remark: "" };
  groupOpen.value = true;
}

function openSmall() {
  const parent = selected.value?.groupType === "BIG" ? selected.value.id : selected.value?.parentId || "";
  groupForm.value = { groupName: "", groupType: "SMALL", parentId: parent, leaderUserId: "", level: "", sortOrder: 0, remark: "" };
  groupOpen.value = true;
}

function openEditGroup() {
  const row = selected.value;
  if (!row) return;
  groupForm.value = {
    id: row.id,
    groupName: row.groupName,
    groupType: row.groupType,
    parentId: row.parentId || "",
    leaderUserId: row.leaderUserId ? String(row.leaderUserId) : "",
    level: row.level || "",
    sortOrder: row.sortOrder ?? 0,
    remark: row.remark || "",
    status: row.status || "ENABLED",
  };
  groupOpen.value = true;
}

async function saveGroup(model: Record<string, unknown>) {
  const body = { ...model };
  if (!body.leaderUserId) body.leaderUserId = null;
  if (!body.level) body.level = null;
  if (body.groupType === "BIG") body.parentId = null;
  const saved = await guard(() =>
    resourceSend<GroupNode>(body.id ? "PUT" : "POST", body.id ? "/ip-group/update" : "/ip-group/create", body, body.id ? undefined : `ipg-${Date.now()}`),
  );
  await loadTree();
  if (saved?.id) pick(String(saved.id));
  return saved;
}

async function toggleGroup() {
  const row = selected.value;
  if (!row) return;
  const status = row.status === "DISABLED" ? "ENABLED" : "DISABLED";
  await guard(() => resourceSend("PUT", "/ip-group/update", { id: row.id, status }));
  toast.success(status === "DISABLED" ? "已停用" : "已启用");
  await loadTree();
}

async function askRemoveGroup() {
  const row = selected.value;
  if (!row) return;
  await confirm({
    title: "删除 IP 组",
    message: `确定删除「${row.groupName}」？组内仍有成员、账号、关联作者或子组时不可删除。`,
    danger: true,
    action: async () => {
      await guard(() => resourceSend("DELETE", `/ip-group/delete?id=${row.id}`));
      selectedId.value = "";
      await loadTree();
    },
  });
}

function openMember(row?: Record<string, unknown>) {
  editingMember.value = row || null;
  memberForm.value = row
    ? { userId: String(row.userId || ""), position: row.position || "", relationType: row.relationType || "PRIMARY", isLeader: !!row.isLeader }
    : { userId: "", position: "", relationType: "PRIMARY", isLeader: false };
  memberOpen.value = true;
}

async function saveMember(model: Record<string, unknown>) {
  const id = selectedId.value;
  const saved = await guard(() => {
    if (editingMember.value?.id) return resourceSend("PUT", `/ip-group/${id}/members/${editingMember.value.id}`, model);
    return resourceSend("POST", `/ip-group/${id}/members`, model, `mem-${Date.now()}`);
  });
  await loadTree();
  await loadPane();
  return saved;
}

async function removeMember(row: Record<string, unknown>) {
  await confirm({
    title: "移除成员",
    message: `确定移除「${row.userName}」？`,
    danger: true,
    action: async () => {
      const data = await guard(() => resourceSend<{ leaderCleared?: boolean; message?: string }>("DELETE", `/ip-group/${selectedId.value}/members/${row.id}`));
      if (data.leaderCleared || data.message) toast.success(data.message || "请重新指定组长");
      await loadTree();
      await loadPane();
    },
  });
}

function openBind() {
  bindForm.value = { accountIds: [] };
  bindOpen.value = true;
}

async function saveBind(model: Record<string, unknown>) {
  const saved = await guard(() => resourceSend("POST", `/ip-group/${selectedId.value}/accounts`, { accountIds: model.accountIds }, `bind-${Date.now()}`));
  await loadTree();
  await loadPane();
  return saved;
}

async function unbind(row: Record<string, unknown>) {
  await confirm({
    title: "解绑账号",
    message: `确定解绑「${row.nickname || row.accountNo}」？`,
    action: async () => {
      const data = await guard(() =>
        resourceSend<{ message?: string }>("DELETE", `/ip-group/${selectedId.value}/accounts/${row.id}`),
      );
      toast.success(data.message || "作者引用仍保留，可在账号详情调整");
      await loadTree();
      await loadPane();
    },
  });
}

function openAnchor() {
  anchorForm.value = { authorId: "", anchorType: "", isPrimary: false };
  anchorOpen.value = true;
}

async function saveAnchor(model: Record<string, unknown>) {
  const saved = await guard(() =>
    resourceSend(
      "POST",
      `/ip-group/${selectedId.value}/anchors`,
      { authorId: model.authorId, anchorType: model.anchorType || undefined, isPrimary: !!model.isPrimary },
      `anc-${Date.now()}`,
    ),
  );
  await loadTree();
  await loadPane();
  return saved;
}

async function makePrimary(row: Record<string, unknown>) {
  await guard(() => resourceSend("PUT", `/ip-group/${selectedId.value}/anchors/${row.id}/primary`, {}));
  toast.success("已设为主作者");
  await loadPane();
}

async function removeAnchor(row: Record<string, unknown>) {
  await confirm({
    title: "移除关联作者",
    message: `确定移除「${row.authorName}」？`,
    danger: true,
    action: async () => {
      const data = await guard(() =>
        resourceSend<{ message?: string; needPrimary?: boolean }>("DELETE", `/ip-group/${selectedId.value}/anchors/${row.id}`),
      );
      if (data.needPrimary) toast.success("请重新指定主作者");
      else if (data.message) toast.success(data.message);
      await loadTree();
      await loadPane();
    },
  });
}

async function loadAuthors() {
  const data = await resourcePage<Record<string, unknown>>("/ip-group/author/page", {
    pageNo: authorPageNo.value,
    pageSize: authorPageSize.value,
    ...authorQuery.value,
    ipGroupId: authorGroupId.value || undefined,
    userId: authorUserId.value || undefined,
  });
  authorRows.value = data.list;
  authorTotal.value = data.total;
}

function openAuthor(row?: Record<string, unknown>) {
  editingAuthor.value = row || null;
  authorForm.value = row
    ? {
        authorName: row.authorName || "",
        authorType: row.authorType || "",
        ipGroupId: row.ipGroupId ? String(row.ipGroupId) : "",
        userId: row.userId ? String(row.userId) : "",
        primaryAccountId: row.primaryAccountId ? String(row.primaryAccountId) : "",
        remark: row.remark || "",
        status: row.status || "ENABLED",
      }
    : { authorName: "", authorType: "", ipGroupId: "", userId: "", primaryAccountId: "", remark: "" };
  authorOpen.value = true;
}

function onAuthorGroup(value: string | string[] | null) {
  const next = Array.isArray(value) ? value[0] || "" : value || "";
  if (next !== authorForm.value.ipGroupId) authorForm.value.primaryAccountId = "";
  authorForm.value.ipGroupId = next;
}

async function saveAuthor(model: Record<string, unknown>) {
  const body: Record<string, unknown> = { ...model };
  if (!body.userId) body.userId = null;
  if (!body.ipGroupId) {
    body.ipGroupId = null;
    body.primaryAccountId = null;
  }
  if (!body.primaryAccountId) body.primaryAccountId = null;
  const saved = await guard(() => {
    if (editingAuthor.value?.id) return resourceSend("PUT", `/ip-group/author/${editingAuthor.value.id}`, body);
    return resourceSend("POST", "/ip-group/author", body, `au-${Date.now()}`);
  });
  await loadAuthors();
  return saved;
}

async function openAuthorDetail(row: Record<string, unknown>) {
  authorCurrent.value = await resourceGet(`/ip-group/author/${row.id}`);
  authorDetailOpen.value = true;
}

async function toggleAuthor() {
  if (!authorCurrent.value) return;
  const status = authorCurrent.value.status === "DISABLED" ? "ENABLED" : "DISABLED";
  authorCurrent.value = await guard(() => resourceSend("PUT", `/ip-group/author/${authorCurrent.value?.id}/status`, { status }));
  await loadAuthors();
}

async function removeAuthor(row: Record<string, unknown>) {
  await confirm({
    title: "删除作者",
    message: `确定删除「${row.authorName}」？`,
    danger: true,
    action: async () => {
      await guard(() => resourceSend("DELETE", `/ip-group/author/${row.id}`));
      authorDetailOpen.value = false;
      await loadAuthors();
    },
  });
}

watch(detailTab, () => void loadPane());
watch(
  () => route.name,
  (name) => {
    if (name === "ip-group-author") view.value = "author";
  },
);
onMounted(async () => {
  await loadTree();
  if (view.value === "author") await loadAuthors();
});
watch(view, (value) => {
  if (value === "author") void loadAuthors();
});
</script>

<template>
  <section>
    <PageHeader title="IP 组" sub-title="日常运营 / IP 组">
      <template #actions>
        <template v-if="view === 'author'">
          <button v-perm="'ims:ip-group:author:create'" class="btn btn-pri" type="button" @click="openAuthor()">新建作者</button>
          <ExportButton v-perm="'ims:ip-group:author:export'" :params="{ ...authorQuery, ipGroupId: authorGroupId, userId: authorUserId }" :export-api="() => resourceGet('/ip-group/author/export', { ...authorQuery, ipGroupId: authorGroupId || undefined, userId: authorUserId || undefined })" />
        </template>
      </template>
    </PageHeader>
    <AppTabs v-model:active="view" :items="pageTabs" />
    <LeftTreeLayout v-if="view === 'ops'">
      <template #tree>
        <div class="tree-head">
          <strong>IP 组结构</strong>
          <button v-perm="'ims:ip-group:create'" class="btn btn-txt" type="button" @click="openBig">+ 新建大组</button>
        </div>
        <el-input v-model="keyword" placeholder="搜索组名" clearable />
        <EmptyState v-if="!tree.length" desc="暂无 IP 组" />
        <EmptyState v-else-if="keyword && !flat.length" desc="无匹配的 IP 组" />
        <button
          v-for="node in flat"
          :key="node.id"
          class="tree-btn"
          :class="{ on: node.id === selectedId, muted: node.status === 'DISABLED' }"
          :style="{ paddingLeft: `${8 + node.depth * 16}px` }"
          type="button"
          @click="pick(node.id)"
        >
          <span :class="{ hit: node.hit }">{{ nodeText(node) }}</span>
          <StatusTag v-if="node.status === 'DISABLED'" dict-type="dict_ip_group_status" :value="node.status" />
          <em v-if="node.readonly">只读</em>
        </button>
      </template>
      <template #main>
        <EmptyState v-if="!selected" desc="请从左侧选择 IP 组" />
        <template v-else>
          <header class="detail-head">
            <StatusTag dict-type="dict_ip_group_type" :value="selected.groupType || ''" />
            <h2>{{ selected.groupName }}</h2>
            <p>组长 {{ selected.leaderName || "—" }} · 上级 {{ selected.parentName || "—" }} · 创建于 {{ selected.createTime || "—" }}</p>
            <button v-if="writable && selected.groupType === 'BIG'" v-perm="'ims:ip-group:create'" class="btn btn-sec" type="button" @click="openSmall">+ 新建小组</button>
            <button v-if="writable" v-perm="'ims:ip-group:update'" class="btn btn-sec" type="button" @click="openEditGroup">编辑</button>
            <button v-if="writable" v-perm="'ims:ip-group:update'" class="btn btn-sec" type="button" @click="toggleGroup">{{ selected.status === "DISABLED" ? "启用" : "停用" }}</button>
            <button v-if="writable" v-perm="'ims:ip-group:delete'" class="btn btn-sec" type="button" @click="askRemoveGroup">删除</button>
          </header>
          <AppTabs v-model:active="detailTab" :items="[{ key: 'base', label: '基本信息' }, { key: 'member', label: '成员管理' }, { key: 'account', label: '账号绑定' }, { key: 'anchor', label: '关联作者' }, { key: 'stats', label: '统计' }]" />
          <DescriptionList v-if="detailTab === 'base'" :items="baseItems" />
          <template v-if="detailTab === 'member'">
            <button v-if="writable" v-perm="'ims:ip-group:member'" class="btn btn-pri" type="button" @click="openMember()">添加成员</button>
            <DataTable :columns="memberColumns" :data="members" />
          </template>
          <template v-if="detailTab === 'account'">
            <p v-if="accountHint">{{ accountHint }}</p>
            <button v-if="writable && !accountReadOnly" v-perm="'ims:ip-group:account'" class="btn btn-pri" type="button" @click="openBind">绑定账号</button>
            <DataTable :columns="accountColumns" :data="accounts" />
          </template>
          <template v-if="detailTab === 'anchor'">
            <p v-if="anchorHint">{{ anchorHint }}</p>
            <button v-if="writable && !anchorReadOnly" v-perm="'ims:ip-group:anchor'" class="btn btn-pri" type="button" @click="openAnchor">关联作者</button>
            <DataTable :columns="anchorColumns" :data="anchors" />
          </template>
          <template v-if="detailTab === 'stats'">
            <p v-if="stats?.mock">{{ stats.mockLabel }}</p>
            <StatCard :items="statItems" />
          </template>
        </template>
      </template>
    </LeftTreeLayout>
    <template v-else>
      <div class="filters">
        <QueryBar v-model="authorQuery" :fields="authorFields" @search="authorPageNo = 1; loadAuthors()" @reset="authorGroupId = ''; authorUserId = ''; authorPageNo = 1; loadAuthors()" />
        <IpGroupSelect v-model="authorGroupId" />
        <UserSelect v-model="authorUserId" />
      </div>
      <DataTable :columns="authorColumns" :data="authorRows" />
      <AppPagination v-model:page-no="authorPageNo" v-model:page-size="authorPageSize" :total="authorTotal" @change="loadAuthors()" />
    </template>

    <FormDrawer v-model:open="groupOpen" :title="groupForm.id ? '编辑 IP 组' : groupForm.groupType === 'SMALL' ? '新建小组' : '新建大组'" :model="groupForm" :submit="saveGroup">
      <el-form-item label="组名" required><el-input v-model="groupForm.groupName" maxlength="50" /></el-form-item>
      <el-form-item label="类型"><el-input :model-value="groupForm.groupType === 'SMALL' ? '小组' : '大组'" disabled /></el-form-item>
      <el-form-item v-if="groupForm.groupType === 'SMALL'" label="上级" required>
        <el-select v-model="groupForm.parentId" placeholder="请选择上级大组">
          <el-option v-for="item in bigParents" :key="item.id" :label="item.groupName" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="组长"><UserSelect :model-value="textOf(groupForm.leaderUserId)" @update:model-value="groupForm.leaderUserId = single($event)" /></el-form-item>
      <el-form-item label="等级"><DictSelect :model-value="textOf(groupForm.level)" dict-type="dict_ip_group_level" @update:model-value="groupForm.level = single($event)" /></el-form-item>
      <el-form-item label="排序"><el-input v-model="groupForm.sortOrder" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="groupForm.remark" maxlength="255" type="textarea" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="memberOpen" :title="editingMember ? '修改成员' : '添加成员'" :model="memberForm" :submit="saveMember">
      <el-form-item v-if="!editingMember" label="用户" required><UserSelect :model-value="textOf(memberForm.userId)" @update:model-value="memberForm.userId = single($event)" /></el-form-item>
      <el-form-item label="岗位" required><DictSelect :model-value="textOf(memberForm.position)" dict-type="dict_position" @update:model-value="memberForm.position = single($event)" /></el-form-item>
      <el-form-item label="主/兼"><DictSelect :model-value="textOf(memberForm.relationType)" dict-type="dict_member_relation" @update:model-value="memberForm.relationType = single($event)" /></el-form-item>
      <el-form-item label="设为组长"><el-switch v-model="memberForm.isLeader" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="bindOpen" title="绑定账号" :model="bindForm" :submit="saveBind">
      <el-form-item label="账号" required>
        <AccountSelect :model-value="listOf(bindForm.accountIds)" multiple include-unassigned :ip-group-id="selectedId" @update:model-value="bindForm.accountIds = listOf($event)" />
      </el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="anchorOpen" title="关联作者" :model="anchorForm" :submit="saveAnchor">
      <el-form-item label="作者" required><AuthorSelect :model-value="textOf(anchorForm.authorId)" @update:model-value="anchorForm.authorId = single($event)" /></el-form-item>
      <el-form-item label="作者类型"><DictSelect :model-value="textOf(anchorForm.anchorType)" dict-type="dict_author_type" @update:model-value="anchorForm.anchorType = single($event)" /></el-form-item>
      <el-form-item label="设为主作者"><el-switch v-model="anchorForm.isPrimary" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="authorOpen" :title="editingAuthor ? '编辑作者' : '新建作者'" :model="authorForm" :submit="saveAuthor">
      <el-form-item label="作者名" required><el-input v-model="authorForm.authorName" maxlength="64" /></el-form-item>
      <el-form-item label="类型" required><DictSelect :model-value="textOf(authorForm.authorType)" dict-type="dict_author_type" @update:model-value="authorForm.authorType = single($event)" /></el-form-item>
      <el-form-item label="归属 IP 组"><IpGroupSelect :model-value="textOf(authorForm.ipGroupId)" only-small @update:model-value="onAuthorGroup" /></el-form-item>
      <el-form-item label="绑定用户"><UserSelect :model-value="textOf(authorForm.userId)" @update:model-value="authorForm.userId = single($event)" /></el-form-item>
      <el-form-item label="主推号">
        <AccountSelect v-if="authorForm.ipGroupId" :model-value="textOf(authorForm.primaryAccountId)" :ip-group-id="String(authorForm.ipGroupId)" @update:model-value="authorForm.primaryAccountId = single($event)" />
        <p v-else>请先为作者指定归属小组</p>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="authorForm.remark" maxlength="255" type="textarea" /></el-form-item>
    </FormDrawer>
    <DetailDrawer v-model:open="authorDetailOpen" :title="String(authorCurrent?.authorName || '作者详情')" status-dict="dict_author_status" :status-value="String(authorCurrent?.status || '')">
      <DescriptionList :items="[{ label: '编号', value: authorCurrent?.authorNo }, { label: '类型', value: authorCurrent?.authorTypeLabel }, { label: '归属 IP 组', value: authorCurrent?.ipGroupText }, { label: '绑定用户', value: authorCurrent?.userName }, { label: '主推号', value: authorCurrent?.primaryAccountName }, { label: '备注', value: authorCurrent?.remark }]" />
      <p>{{ authorCurrent?.dashboardHint }}</p>
      <p v-for="item in (authorCurrent?.groups as Record<string, unknown>[] | undefined) || []" :key="String(item.id)">{{ item.groupName }} {{ item.isPrimary ? "主作者" : "" }}</p>
      <template #footer>
        <button v-perm="'ims:ip-group:author:update'" class="btn btn-sec" type="button" @click="toggleAuthor">{{ authorCurrent?.status === "DISABLED" ? "启用" : "停用" }}</button>
      </template>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.tree-head { display: flex; justify-content: space-between; align-items: center; }
.tree-btn { display: flex; gap: 6px; align-items: center; width: 100%; text-align: left; background: transparent; border: 0; padding: 6px 8px; }
.tree-btn.on { background: #eef3ff; }
.tree-btn .hit { background: #fff3bf; }
.tree-btn.muted { opacity: 0.65; }
.detail-head h2 { margin: 8px 0; }
.filters { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; }
</style>
