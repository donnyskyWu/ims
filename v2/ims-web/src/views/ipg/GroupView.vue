<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import AppPagination from "@/components/AppPagination.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import EmptyState from "@/components/EmptyState.vue";
import StatCard from "@/components/StatCard.vue";
import StatusTag from "@/components/StatusTag.vue";
import UserSelect from "@/components/UserSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import AuthorSelect from "@/components/AuthorSelect.vue";
import IpGroupSelect from "@/components/IpGroupSelect.vue";
import ExportButton from "@/components/ExportButton.vue";
import LeftTreeLayout from "@/layouts/LeftTreeLayout.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

interface GroupNode {
  id: string;
  groupName: string;
  groupType: string;
  groupTypeLabel: string;
  status: string;
  statusLabel: string;
  label: string;
  readOnly?: boolean;
  children?: GroupNode[];
  [key: string]: unknown;
}

const route = useRoute();
const router = useRouter();
const view = ref(route.name === "ip-group-author" ? "author" : "group");
const tree = ref<GroupNode[]>([]);
const keyword = ref("");
const selected = ref<GroupNode | null>(null);
const tab = ref("base");
const members = ref<Record<string, unknown>[]>([]);
const accounts = ref<Record<string, unknown>[]>([]);
const accountHint = ref("");
const accountReadOnly = ref(false);
const anchors = ref<Record<string, unknown>[]>([]);
const stats = ref<Record<string, unknown> | null>(null);
interface GroupDraft {
  id?: string;
  groupName: string;
  groupType: string;
  parentId: string;
  level: string;
  leaderUserId: string;
  sortOrder?: number;
  status: string;
  remark: string;
}
interface MemberDraft {
  userId: string;
  position: string;
  relationType: string;
  isLeader: boolean;
}
interface AnchorDraft {
  authorId: string;
  anchorType: string;
  isPrimary: boolean;
}
interface AuthorDraft {
  authorName: string;
  authorType: string;
  ipGroupId: string;
  userId: string;
  primaryAccountId: string;
  remark: string;
  status?: string;
}

function asModel<T extends object>(value: T): Record<string, unknown> {
  return value as unknown as Record<string, unknown>;
}

function text(value: unknown): string {
  return value == null ? "" : String(value);
}

const groupDrawer = ref(false);
const groupForm = ref<GroupDraft>({ groupName: "", groupType: "BIG", parentId: "", level: "", leaderUserId: "", status: "", remark: "" });
const groupMode = ref<"big" | "small" | "edit">("big");
const memberDrawer = ref(false);
const memberForm = ref<MemberDraft>({ userId: "", position: "", relationType: "", isLeader: false });
const editingMember = ref<Record<string, unknown> | null>(null);
const accountDrawer = ref(false);
const accountIds = ref<string[]>([]);
const anchorDrawer = ref(false);
const anchorForm = ref<AnchorDraft>({ authorId: "", anchorType: "", isPrimary: false });
const authorQuery = ref<Record<string, unknown>>({ keyword: "", authorType: "", status: "" });
const authorGroupId = ref("");
const authors = ref<Record<string, unknown>[]>([]);
const authorTotal = ref(0);
const authorPage = ref(1);
const authorPageSize = ref(20);
const authorDrawer = ref(false);
const authorForm = ref<AuthorDraft>({ authorName: "", authorType: "", ipGroupId: "", userId: "", primaryAccountId: "", remark: "" });
const editingAuthor = ref<Record<string, unknown> | null>(null);
const authorDetail = ref<Record<string, unknown> | null>(null);

const viewTabs = [
  { key: "group", label: "IP 组运营" },
  { key: "author", label: "作者管理" },
];
const detailTabs = [
  { key: "base", label: "基本信息" },
  { key: "member", label: "成员管理" },
  { key: "account", label: "账号绑定" },
  { key: "anchor", label: "关联作者" },
  { key: "stats", label: "统计" },
];
const authorFields: QueryField[] = [
  { key: "keyword", label: "作者名", type: "input" },
  { key: "authorType", label: "类型", type: "dict", dictType: "dict_author_type" },
  { key: "status", label: "状态", type: "dict", dictType: "dict_author_status" },
];

const shownTree = computed(() => filterTree(tree.value, keyword.value.trim()));
const statItems = computed(() => {
  const row = stats.value || {};
  return [
    { title: "成员数", value: Number(row.memberCount || 0) },
    { title: "账号数", value: Number(row.accountCount || 0) },
    { title: "作者数", value: Number(row.authorCount || 0) },
    { title: "粉丝数", value: Number(row.fanCount || 0), desc: String(row.mockLabel || "") },
    { title: "作品数", value: Number(row.workCount || 0), desc: "示意" },
    { title: "内部内容", value: Number(row.contentCount || 0), desc: "示意" },
    { title: "成本", value: Number(row.cost || 0), desc: "示意" },
    { title: "营收", value: Number(row.revenue || 0), desc: "示意" },
    { title: "本月场次数", value: Number(row.monthSessionCount || 0) },
    { title: "已核准 GMV", value: String(row.confirmedGmv || "0.00") },
  ];
});

const memberColumns: TableColumn[] = [
  { key: "userName", label: "姓名" },
  { key: "positionLabel", label: "岗位" },
  { key: "relationLabel", label: "主/兼" },
  { key: "leaderText", label: "组长" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "编辑", perm: "ims:ip-group:member", onClick: (row) => openMember(row) },
      { label: "移除", perm: "ims:ip-group:member", danger: true, onClick: (row) => void removeMember(row) },
    ],
  },
];
const accountColumns: TableColumn[] = [
  { key: "accountNo", label: "账号编号", type: "mono" },
  { key: "nickname", label: "昵称" },
  { key: "platformLabel", label: "平台" },
  { key: "status", label: "状态" },
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
        show: () => !accountReadOnly.value,
        onClick: (row) => void unbind(row),
      },
    ],
  },
];
const anchorColumns: TableColumn[] = [
  { key: "authorName", label: "作者名" },
  { key: "authorTypeLabel", label: "类型" },
  { key: "primaryText", label: "主作者" },
  { key: "userName", label: "绑定用户" },
  { key: "primaryAccountNo", label: "主推号" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "设为主作者", perm: "ims:ip-group:anchor", show: (row) => row.isPrimary !== true && selected.value?.groupType === "SMALL", onClick: (row) => void makePrimary(row) },
      { label: "移除", perm: "ims:ip-group:anchor", danger: true, show: () => selected.value?.groupType === "SMALL", onClick: (row) => void removeAnchor(row) },
    ],
  },
];
const authorColumns: TableColumn[] = [
  { key: "authorNo", label: "作者编号", type: "mono" },
  { key: "authorName", label: "作者名" },
  { key: "authorTypeLabel", label: "类型" },
  { key: "ipGroupText", label: "归属 IP 组" },
  { key: "userName", label: "绑定用户" },
  { key: "primaryAccountNo", label: "主推号" },
  { key: "status", label: "状态", type: "status", dictType: "dict_author_status" },
  { key: "updateTime", label: "更新时间" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "详情", onClick: (row) => void openAuthorDetail(row) },
      { label: "编辑", perm: "ims:ip-group:author:update", onClick: (row) => openAuthor(row) },
      { label: "停用", perm: "ims:ip-group:author:update", show: (row) => row.status === "ENABLED", onClick: (row) => void setAuthorStatus(row, "DISABLED") },
      { label: "启用", perm: "ims:ip-group:author:update", show: (row) => row.status === "DISABLED", onClick: (row) => void setAuthorStatus(row, "ENABLED") },
      { label: "删除", perm: "ims:ip-group:author:delete", danger: true, onClick: (row) => void removeAuthor(row) },
    ],
  },
];

function filterTree(nodes: GroupNode[], key: string): GroupNode[] {
  if (!key) return nodes;
  const out: GroupNode[] = [];
  for (const node of nodes) {
    const children = filterTree(node.children || [], key);
    const hit = String(node.groupName || "").includes(key);
    if (hit || children.length) out.push({ ...node, children });
  }
  return out;
}

function syncView() {
  view.value = route.name === "ip-group-author" ? "author" : "group";
}

async function loadTree() {
  const data = await resourceGet<{ list: GroupNode[] }>("/ip-group/accessible-tree");
  tree.value = data.list || [];
  if (selected.value) {
    const found = findNode(tree.value, String(selected.value.id));
    selected.value = found;
  }
}

function findNode(nodes: GroupNode[], id: string): GroupNode | null {
  for (const node of nodes) {
    if (String(node.id) === id) return node;
    const child = findNode(node.children || [], id);
    if (child) return child;
  }
  return null;
}

async function pick(node: GroupNode) {
  selected.value = node;
  tab.value = "base";
  await loadDetail();
}

async function loadDetail() {
  if (!selected.value) return;
  const id = selected.value.id;
  if (tab.value === "member") {
    const data = await resourceGet<{ list: Record<string, unknown>[] }>(`/ip-group/${id}/members`);
    members.value = (data.list || []).map((row) => ({ ...row, leaderText: row.isLeader ? "是" : "否" }));
  }
  if (tab.value === "account") {
    const data = await resourceGet<{ list: Record<string, unknown>[]; hint?: string; readOnly?: boolean }>(`/ip-group/${id}/accounts`);
    accounts.value = data.list || [];
    accountHint.value = data.hint || "";
    accountReadOnly.value = Boolean(data.readOnly);
  }
  if (tab.value === "anchor") {
    const data = await resourceGet<{ list: Record<string, unknown>[] }>(`/ip-group/${id}/anchors`);
    anchors.value = (data.list || []).map((row) => ({ ...row, primaryText: row.isPrimary ? "是" : "否" }));
  }
  if (tab.value === "stats") stats.value = await resourceGet(`/ip-group/${id}/stats`);
}

watch(tab, () => void loadDetail());

function openBig() {
  groupMode.value = "big";
  groupForm.value = { groupName: "", level: "", leaderUserId: "", remark: "", groupType: "BIG", parentId: "", status: "ENABLED" };
  groupDrawer.value = true;
}
function openSmall(parent?: GroupNode) {
  const current = parent || selected.value;
  groupMode.value = "small";
  groupForm.value = { groupName: "", parentId: current?.id || "", level: "", leaderUserId: "", remark: "", groupType: "SMALL", status: "ENABLED" };
  groupDrawer.value = true;
}
function openEditGroup() {
  if (!selected.value) return;
  groupMode.value = "edit";
  groupForm.value = {
    id: selected.value.id,
    groupName: selected.value.groupName,
    groupType: selected.value.groupType,
    parentId: text(selected.value.parentId),
    level: text(selected.value.level),
    leaderUserId: text(selected.value.leaderUserId),
    sortOrder: Number(text(selected.value.sortOrder) || 0),
    status: selected.value.status,
    remark: text(selected.value.remark),
  };
  groupDrawer.value = true;
}
async function saveGroup(model: Record<string, unknown>) {
  try {
    if (groupMode.value === "edit") await resourceSend("PUT", "/ip-group/update", model);
    else await resourceSend("POST", "/ip-group/create", { ...model, groupType: groupMode.value === "big" ? "BIG" : "SMALL" }, "ip-group-create");
  } catch (error) {
    toast.error((error as BizError).message || "保存失败");
    throw error;
  }
  await loadTree();
}
async function disableGroup() {
  if (!selected.value) return;
  const next = selected.value.status === "DISABLED" ? "ENABLED" : "DISABLED";
  await resourceSend("PUT", "/ip-group/update", { id: selected.value.id, status: next });
  toast.success(next === "DISABLED" ? "已停用" : "已启用");
  await loadTree();
}
async function removeGroup() {
  if (!selected.value) return;
  const id = selected.value.id;
  try {
    await confirm({
      title: "删除 IP 组",
      message: "删除后不可恢复。仍有成员、账号或作者时会被拒绝。",
      danger: true,
      action: async () => {
        await resourceSend("DELETE", `/ip-group/delete?id=${id}`);
      },
    });
    toast.success("已删除");
    selected.value = null;
    await loadTree();
  } catch (error) {
    const biz = error as BizError;
    if (biz?.message) toast.error(biz.message);
  }
}

function openMember(row?: Record<string, unknown>) {
  editingMember.value = row || null;
  memberForm.value = row
    ? {
        userId: text(row.userId),
        position: text(row.position),
        relationType: text(row.relationType),
        isLeader: row.isLeader === "是" || row.isLeader === true,
      }
    : { userId: "", position: "", relationType: "PRIMARY", isLeader: false };
  memberDrawer.value = true;
}
async function saveMember(model: Record<string, unknown>) {
  if (!selected.value) return;
  try {
    if (editingMember.value?.id) await resourceSend("PUT", `/ip-group/${selected.value.id}/members/${editingMember.value.id}`, model);
    else await resourceSend("POST", `/ip-group/${selected.value.id}/members`, model, "ip-member");
  } catch (error) {
    toast.error((error as BizError).message || "保存失败");
    throw error;
  }
  await loadTree();
  await loadDetail();
}
async function removeMember(row: Record<string, unknown>) {
  if (!selected.value) return;
  await confirm({ title: "移除成员", message: "确认移除该成员？", danger: true, action: async () => undefined });
  const data = await resourceSend<{ hint?: string }>("DELETE", `/ip-group/${selected.value.id}/members/${row.id}`);
  if (data?.hint) toast.warning(data.hint);
  await loadTree();
  await loadDetail();
}

async function saveAccounts() {
  if (!selected.value) return;
  try {
    await resourceSend("POST", `/ip-group/${selected.value.id}/accounts`, { accountIds: accountIds.value }, "ip-account");
    accountDrawer.value = false;
    toast.success("已绑定");
  } catch (error) {
    const biz = error as BizError;
    toast.error(biz.code === 1223 ? `${biz.message}。请到关联作者页签设置主作者。` : biz.message || "绑定失败");
    throw error;
  }
  await loadTree();
  await loadDetail();
}
async function unbind(row: Record<string, unknown>) {
  if (!selected.value) return;
  await confirm({ title: "解绑账号", message: "解绑后作者引用仍保留，可在账号详情调整。", action: async () => undefined });
  const data = await resourceSend<{ hint?: string }>("DELETE", `/ip-group/${selected.value.id}/accounts/${row.id}`);
  if (data?.hint) toast.info(data.hint);
  await loadTree();
  await loadDetail();
}
async function saveAnchor(model: Record<string, unknown>) {
  if (!selected.value) return;
  try {
    await resourceSend("POST", `/ip-group/${selected.value.id}/anchors`, model, "ip-anchor");
  } catch (error) {
    toast.error((error as BizError).message || "保存失败");
    throw error;
  }
  await loadTree();
  await loadDetail();
}
async function makePrimary(row: Record<string, unknown>) {
  if (!selected.value) return;
  await resourceSend("PUT", `/ip-group/${selected.value.id}/anchors/${row.id}/primary`);
  toast.success("已设置主作者");
  await loadDetail();
}
async function removeAnchor(row: Record<string, unknown>) {
  if (!selected.value) return;
  await confirm({ title: "移除关联", message: "若当前是主作者，移除后不会自动递补。", danger: true, action: async () => undefined });
  const data = await resourceSend<{ hint?: string }>("DELETE", `/ip-group/${selected.value.id}/anchors/${row.id}`);
  if (data?.hint) toast.warning(data.hint);
  await loadTree();
  await loadDetail();
}

async function loadAuthors() {
  const data = await resourcePage<Record<string, unknown>>("/ip-group/author/page", {
    pageNo: authorPage.value,
    pageSize: authorPageSize.value,
    ...authorQuery.value,
    ipGroupId: authorGroupId.value || undefined,
  });
  authors.value = data.list;
  authorTotal.value = data.total;
}
function openAuthor(row?: Record<string, unknown>) {
  editingAuthor.value = row || null;
  authorForm.value = row
    ? {
        authorName: text(row.authorName),
        authorType: text(row.authorType),
        ipGroupId: text(row.ipGroupId),
        userId: text(row.userId),
        primaryAccountId: text(row.primaryAccountId),
        remark: text(row.remark),
        status: text(row.status),
      }
    : { authorName: "", authorType: "", ipGroupId: "", userId: "", primaryAccountId: "", remark: "" };
  authorDrawer.value = true;
}
async function saveAuthor(model: Record<string, unknown>) {
  try {
    if (editingAuthor.value?.id) await resourceSend("PUT", `/ip-group/author/${editingAuthor.value.id}`, model);
    else await resourceSend("POST", "/ip-group/author", model, "ip-author");
  } catch (error) {
    toast.error((error as BizError).message || "保存失败");
    throw error;
  }
  await loadAuthors();
}
async function setAuthorStatus(row: Record<string, unknown>, status: string) {
  await resourceSend("PUT", `/ip-group/author/${row.id}/status`, { status });
  await loadAuthors();
}
async function removeAuthor(row: Record<string, unknown>) {
  await confirm({ title: "删除作者", message: "仍被账号或组引用时不能删除。", danger: true, action: async () => undefined });
  try {
    await resourceSend("DELETE", `/ip-group/author/${row.id}`);
    toast.success("已删除");
    await loadAuthors();
  } catch (error) {
    toast.error((error as BizError).message || "删除失败");
  }
}
async function openAuthorDetail(row: Record<string, unknown>) {
  authorDetail.value = await resourceGet(`/ip-group/author/${row.id}`);
}

function changeView(key: string) {
  if (key === "author") void router.push("/ims/ip-group/author");
  else void router.push("/ims/ip-group");
}

watch(() => route.name, syncView);
watch(view, (key) => {
  if (key === "author") void loadAuthors();
});
onMounted(async () => {
  syncView();
  await loadTree();
  if (view.value === "author") await loadAuthors();
});
</script>

<template>
  <section>
    <PageHeader title="IP 组" sub-title="日常运营 / IP 组">
      <template #actions>
        <ExportButton v-if="view === 'author'" v-perm="'ims:ip-group:author:export'" :export-api="() => resourceGet('/ip-group/author/export', { ...authorQuery, ipGroupId: authorGroupId })" />
        <button v-if="view === 'author'" v-perm="'ims:ip-group:author:create'" class="btn btn-pri" type="button" @click="openAuthor()">新建作者</button>
      </template>
    </PageHeader>
    <AppTabs v-model:active="view" :items="viewTabs" @change="changeView" />

    <LeftTreeLayout v-if="view === 'group'">
      <template #tree>
        <div class="tree-head">
          <strong>IP 组结构</strong>
          <button v-perm="'ims:ip-group:create'" class="btn btn-pri btn-sm" type="button" @click="openBig">+ 新建大组</button>
        </div>
        <el-input v-model="keyword" placeholder="搜索组名" clearable />
        <EmptyState v-if="!shownTree.length && keyword" desc="无匹配的 IP 组" />
        <EmptyState v-else-if="!tree.length" desc="请从左侧选择 IP 组">
          <template #action>
            <button v-perm="'ims:ip-group:create'" class="btn btn-pri" type="button" @click="openBig">新建大组</button>
          </template>
        </EmptyState>
        <ul v-else class="ip-tree">
          <li v-for="big in shownTree" :key="big.id">
            <button type="button" class="node" :class="{ on: selected?.id === big.id, off: big.status === 'DISABLED', hit: keyword && String(big.groupName).includes(keyword) }" @click="pick(big)">
              <StatusTag dict-type="dict_ip_group_type" :value="big.groupType" />
              {{ big.label }}
              <StatusTag v-if="big.status === 'DISABLED'" dict-type="dict_ip_group_status" :value="big.status" />
            </button>
            <ul>
              <li v-for="small in big.children || []" :key="small.id">
                <button type="button" class="node child" :class="{ on: selected?.id === small.id, off: small.status === 'DISABLED', hit: keyword && String(small.groupName).includes(keyword) }" @click="pick(small)">
                  {{ small.label }}
                  <StatusTag v-if="small.status === 'DISABLED'" dict-type="dict_ip_group_status" :value="small.status" />
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </template>
      <template #main>
        <EmptyState v-if="!selected" desc="请从左侧选择 IP 组" />
        <div v-else>
          <div class="head">
            <StatusTag dict-type="dict_ip_group_type" :value="String(selected.groupType)" />
            <h2>{{ selected.groupName }}</h2>
            <span>组长 {{ selected.leaderName || "—" }} | 上级 {{ selected.parentName || "—" }} | 创建于 {{ selected.createTime }}</span>
            <button v-if="selected.groupType === 'BIG' && !selected.readOnly" v-perm="'ims:ip-group:create'" class="btn btn-sec" type="button" @click="openSmall(selected)">+ 新建小组</button>
            <button v-if="!selected.readOnly" v-perm="'ims:ip-group:update'" class="btn btn-sec" type="button" @click="openEditGroup">编辑</button>
            <button v-if="!selected.readOnly" v-perm="'ims:ip-group:update'" class="btn btn-sec" type="button" @click="disableGroup">{{ selected.status === "DISABLED" ? "启用" : "停用" }}</button>
            <button v-if="!selected.readOnly" v-perm="'ims:ip-group:delete'" class="btn btn-sec" type="button" @click="removeGroup">删除</button>
          </div>
          <AppTabs v-model:active="tab" :items="detailTabs" />
          <DescriptionList
            v-if="tab === 'base'"
            :items="[
              { label: '组名', value: selected.groupName },
              { label: '类型', value: selected.groupTypeLabel },
              { label: '上级', value: selected.parentName || '—' },
              { label: '组长', value: selected.leaderName },
              { label: '等级', value: selected.levelLabel },
              { label: '状态', value: selected.statusLabel },
              { label: '排序', value: selected.sortOrder },
              { label: '备注', value: selected.remark || '—' },
              { label: '创建时间', value: selected.createTime },
              { label: '更新时间', value: selected.updateTime },
            ]"
          />
          <div v-if="tab === 'member'">
            <button v-if="!selected.readOnly" v-perm="'ims:ip-group:member'" class="btn btn-pri" type="button" @click="openMember()">添加成员</button>
            <DataTable :columns="memberColumns" :data="members" />
          </div>
          <div v-if="tab === 'account'">
            <p v-if="accountHint">{{ accountHint }}</p>
            <button v-if="!accountReadOnly && !selected.readOnly" v-perm="'ims:ip-group:account'" class="btn btn-pri" type="button" @click="accountIds = []; accountDrawer = true">绑定账号</button>
            <DataTable :columns="accountColumns" :data="accounts" />
          </div>
          <div v-if="tab === 'anchor'">
            <p v-if="selected.groupType === 'BIG'">大组不可关联作者，请在小组下操作。</p>
            <button v-if="selected.groupType === 'SMALL' && !selected.readOnly" v-perm="'ims:ip-group:anchor'" class="btn btn-pri" type="button" @click="anchorForm = { authorId: '', anchorType: '', isPrimary: false }; anchorDrawer = true">添加作者</button>
            <DataTable :columns="anchorColumns" :data="anchors" />
          </div>
          <div v-if="tab === 'stats'">
            <p class="mock">示意数据，采集/财务上线后替换。成员、账号、作者为真实计数。</p>
            <StatCard :items="statItems" />
          </div>
        </div>
      </template>
    </LeftTreeLayout>

    <div v-else>
      <div class="filters">
        <QueryBar v-model="authorQuery" :fields="authorFields" @search="authorPage = 1; loadAuthors()" @reset="authorGroupId = ''; authorPage = 1; loadAuthors()" />
        <IpGroupSelect v-model="authorGroupId" only-small />
      </div>
      <DataTable :columns="authorColumns" :data="authors" />
      <AppPagination v-model:page-no="authorPage" v-model:page-size="authorPageSize" :total="authorTotal" @change="loadAuthors()" />
      <DescriptionList
        v-if="authorDetail"
        :items="[
          { label: '编号', value: authorDetail.authorNo },
          { label: '作者名', value: authorDetail.authorName },
          { label: '类型', value: authorDetail.authorTypeLabel },
          { label: '归属组', value: authorDetail.ipGroupText },
          { label: '主推号', value: authorDetail.primaryAccountNo },
          { label: '说明', value: authorDetail.dashboardHint },
        ]"
      />
      <p v-if="authorDetail">关联组：{{ (authorDetail.groups as { groupName: string }[] | undefined)?.map((item) => item.groupName).join('、') || '—' }}</p>
    </div>

    <FormDrawer v-model:open="groupDrawer" :title="groupMode === 'edit' ? '编辑 IP 组' : groupMode === 'big' ? '新建大组' : '新建小组'" :model="asModel(groupForm)" :submit="saveGroup" @saved="loadTree()">
      <el-form-item label="组名" required><el-input v-model="groupForm.groupName" maxlength="50" /></el-form-item>
      <el-form-item label="类型"><el-input :model-value="groupMode === 'big' || groupForm.groupType === 'BIG' ? '大组' : '小组'" disabled /></el-form-item>
      <el-form-item v-if="groupMode !== 'big' && groupForm.groupType !== 'BIG'" label="上级" required>
        <IpGroupSelect v-model="groupForm.parentId" only-big />
      </el-form-item>
      <el-form-item label="等级"><DictSelect v-model="groupForm.level" dict-type="dict_ip_group_level" /></el-form-item>
      <el-form-item label="组长"><UserSelect v-model="groupForm.leaderUserId" /></el-form-item>
      <el-form-item v-if="groupMode === 'edit'" label="状态"><DictSelect v-model="groupForm.status" dict-type="dict_ip_group_status" mode="edit" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="groupForm.remark" maxlength="255" type="textarea" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="memberDrawer" :title="editingMember ? '编辑成员' : '添加成员'" :model="asModel(memberForm)" :submit="saveMember">
      <el-form-item v-if="!editingMember" label="用户" required><UserSelect v-model="memberForm.userId" /></el-form-item>
      <el-form-item label="岗位" required><DictSelect v-model="memberForm.position" dict-type="dict_position" /></el-form-item>
      <el-form-item label="主/兼" required><DictSelect v-model="memberForm.relationType" dict-type="dict_member_relation" /></el-form-item>
      <el-form-item label="设为组长"><el-switch v-model="memberForm.isLeader" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="accountDrawer" title="绑定账号" :model="{ accountIds }" :submit="async () => saveAccounts()">
      <el-form-item label="账号" required><AccountSelect v-model="accountIds" multiple /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="anchorDrawer" title="添加关联作者" :model="asModel(anchorForm)" :submit="saveAnchor">
      <el-form-item label="作者" required><AuthorSelect v-model="anchorForm.authorId" /></el-form-item>
      <el-form-item label="类型"><DictSelect v-model="anchorForm.anchorType" dict-type="dict_author_type" /></el-form-item>
      <el-form-item label="设为主作者"><el-switch v-model="anchorForm.isPrimary" /></el-form-item>
    </FormDrawer>
    <FormDrawer v-model:open="authorDrawer" :title="editingAuthor ? '编辑作者' : '新建作者'" :model="asModel(authorForm)" :submit="saveAuthor">
      <el-form-item label="作者名" required><el-input v-model="authorForm.authorName" maxlength="64" /></el-form-item>
      <el-form-item label="类型" required><DictSelect v-model="authorForm.authorType" dict-type="dict_author_type" /></el-form-item>
      <el-form-item label="归属小组"><IpGroupSelect v-model="authorForm.ipGroupId" only-small /></el-form-item>
      <el-form-item label="绑定用户"><UserSelect v-model="authorForm.userId" /></el-form-item>
      <el-form-item label="主推号">
        <AccountSelect v-model="authorForm.primaryAccountId" :ip-group-id="String(authorForm.ipGroupId || '')" />
        <p v-if="!authorForm.ipGroupId">请先为作者指定归属小组</p>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="authorForm.remark" maxlength="255" type="textarea" /></el-form-item>
    </FormDrawer>
  </section>
</template>

<style scoped>
.tree-head, .head, .filters { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
.ip-tree { list-style: none; padding: 0; margin: 8px 0; }
.ip-tree ul { list-style: none; padding-left: 16px; }
.node { display: flex; gap: 6px; align-items: center; width: 100%; text-align: left; background: transparent; border: 0; padding: 6px; }
.node.on { background: var(--bg-soft, #f4f7fb); }
.node.off { color: var(--text-3, #8a94a6); }
.node.hit { outline: 1px solid var(--pri, #2f6fed); }
.mock { color: var(--text-3, #8a94a6); }
</style>
