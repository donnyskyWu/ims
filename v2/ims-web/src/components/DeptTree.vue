<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useDeptStore } from "@/stores/dept";
import { useAuthStore } from "@/stores/auth";
import { call } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";
import { hasPerm } from "@/utils/perm";
import { confirm } from "./confirm";
import { toast } from "@/utils/toast";
import FormDrawer from "./FormDrawer.vue";
import AppModal from "./AppModal.vue";
import UserSelect from "./UserSelect.vue";
import DeptTreeSelect from "./DeptTreeSelect.vue";
import EmptyState from "./EmptyState.vue";
import { fmtTime } from "@/utils/format";
import DeptBranch from "./DeptBranch.vue";
import {
  ancestorIds,
  canMoveDept,
  fallbackSelection,
  filterDeptTree,
  findDept,
  isPendingDept,
  type DeptNode,
} from "./dept/tree-logic";

const props = withDefaults(
  defineProps<{ showCount?: boolean; showSync?: boolean; editable?: boolean }>(),
  { showCount: true, showSync: true, editable: true },
);
const selected = defineModel<string | null>("selected", { default: null });
const includeChildren = defineModel<boolean>("includeChildren", { default: true });
const emit = defineEmits<{ select: [id: string | null, includeChildren: boolean] }>();

const dept = useDeptStore();
const auth = useAuthStore();
const keyword = ref("");
const applied = ref("");
const expanded = ref<string[]>([]);
const savedExpanded = ref<string[] | null>(null);
const dragOver = ref("");
const formOpen = ref(false);
const formMode = ref<"create" | "rename">("create");
const formModel = ref<Record<string, unknown>>({ name: "", leaderUserId: "", sort: 0 });
const formParent = ref<DeptNode | null>(null);
const moveOpen = ref(false);
const moveTarget = ref<string | null>(null);
const moving = ref<DeptNode | null>(null);
const syncing = ref(false);
const lastSync = ref("");
let searchTimer = 0;

const permState = computed(() => ({ permCodes: auth.permCodes, permDetails: auth.permDetails }));
const canCreate = computed(() => hasPerm(permState.value, "ims:system:dept:create"));
const canUpdate = computed(() => hasPerm(permState.value, "ims:system:dept:update"));
const canDelete = computed(() => hasPerm(permState.value, "ims:system:dept:delete"));
const canSync = computed(() => hasPerm(permState.value, "ims:system:org-sync:run"));

const pendingNode = computed(() => dept.flat.find((item) => item.source === "SYSTEM") || null);
const filtered = computed(() => filterDeptTree(dept.tree.filter((item) => item.source !== "SYSTEM"), applied.value));

onMounted(async () => {
  await dept.load();
  expanded.value = dept.tree.map((item) => item.id);
  void loadSync();
});

watch(
  () => dept.version,
  () => {
    const next = fallbackSelection(dept.tree, selected.value, dept.showDisabled);
    if (next !== selected.value) choose(next);
  },
);

watch(keyword, (value) => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    if (value.trim() && savedExpanded.value === null) savedExpanded.value = [...expanded.value];
    applied.value = value.trim();
    if (!applied.value) {
      if (savedExpanded.value) expanded.value = savedExpanded.value;
      savedExpanded.value = null;
      return;
    }
    const hits = dept.flat.filter((item) => item.name.includes(applied.value));
    const open = new Set<string>();
    hits.forEach((item) => ancestorIds(dept.tree, item.id).forEach((id) => open.add(id)));
    expanded.value = [...open];
  }, 300);
});

function choose(id: string | null) {
  if (id === selected.value) return;
  selected.value = id;
  emit("select", id, includeChildren.value);
}

function toggle(id: string) {
  expanded.value = expanded.value.includes(id) ? expanded.value.filter((item) => item !== id) : [...expanded.value, id];
}

function menuOf(node: DeptNode) {
  if (!props.editable || isPendingDept(node)) return [];
  const items: { key: string; label: string }[] = [];
  if (canCreate.value && node.status !== "DISABLED") items.push({ key: "create", label: "新增下级" });
  if (canUpdate.value) {
    items.push({ key: "rename", label: "改名 / 设负责人" });
    items.push({ key: "move", label: "移动" });
    items.push({ key: "status", label: node.status === "DISABLED" ? "启用" : "停用" });
    if (node.localOrphan) items.push({ key: "keep", label: "确认保留" });
  }
  if (canDelete.value) items.push({ key: "delete", label: "删除" });
  return items;
}

function openCreate(node: DeptNode) {
  formMode.value = "create";
  formParent.value = node;
  formModel.value = { name: "", leaderUserId: "", sort: 0 };
  formOpen.value = true;
}

function openRename(node: DeptNode) {
  formMode.value = "rename";
  formParent.value = node;
  formModel.value = { name: node.name, leaderUserId: node.leaderUserId, sort: 0 };
  formOpen.value = true;
}

async function submitForm(model: Record<string, unknown>) {
  const parent = formParent.value;
  if (!parent) return;
  if (formMode.value === "create") {
    const created = await call<{ id: string }>("dept_create_admin_api_ims_system_dept_create_post", {
      body: { name: model.name, parentId: parent.id, source: "LOCAL" },
      silent: true,
    });
    if (model.leaderUserId || model.sort) {
      await call("dept_update_admin_api_ims_system_dept_update_put", {
        body: { id: created.id, leaderUserId: model.leaderUserId || undefined, sort: Number(model.sort || 0) },
        silent: true,
      });
    }
    await dept.reload();
    choose(String(created.id));
    return created;
  }
  const updated = await call<{ syncOverrideHint?: boolean }>("dept_update_admin_api_ims_system_dept_update_put", {
    body: { id: parent.id, name: model.name, leaderUserId: model.leaderUserId || undefined, sort: Number(model.sort || 0) },
    silent: true,
  });
  await dept.reload();
  if (parent.source === "DINGTALK") toast.success("下次钉钉同步将以钉钉为准覆盖此修改");
  return updated;
}

const dingHint = computed(() => formMode.value === "rename" && formParent.value?.source === "DINGTALK");

function blockedMoveIds(node: DeptNode): string[] {
  const ids = [node.id, ...node.children.flatMap((child) => [child.id, ...collect(child)])];
  if (node.source === "DINGTALK") ids.push(...dept.flat.filter((item) => item.source === "LOCAL").map((item) => item.id));
  const pending = dept.flat.find((item) => item.source === "SYSTEM");
  if (pending) ids.push(pending.id);
  return ids;
}

function collect(node: DeptNode): string[] {
  return node.children.flatMap((child) => [child.id, ...collect(child)]);
}

function openMove(node: DeptNode) {
  moving.value = node;
  moveTarget.value = null;
  moveOpen.value = true;
}

async function doMove(id: string, parentId: string) {
  const source = findDept(dept.tree, id);
  const check = canMoveDept(dept.tree, id, parentId);
  if (!check.ok) {
    toast.error(check.reason || "不能移动");
    return;
  }
  try {
    await call("dept_move_admin_api_ims_system_dept_move_put", { body: { id, parentId }, silent: true });
    await dept.reload();
    if (source?.source === "DINGTALK") toast.success("下次钉钉同步将以钉钉为准覆盖此修改");
  } catch (caught) {
    const biz = caught as BizError;
    toast.error(biz.code === 1219 ? "同一上级部门下已有同名部门" : biz.msg);
    await dept.reload();
  }
}

async function confirmMove() {
  if (!moving.value || !moveTarget.value) return;
  const target = findDept(dept.tree, moveTarget.value);
  await confirm({
    title: "移动部门",
    message: `确定将「${moving.value.name}」移动到「${target?.name || ""}」下？`,
    action: async () => {
      await doMove(moving.value!.id, moveTarget.value!);
      moveOpen.value = false;
    },
  });
}

function onDrop(target: DeptNode) {
  const sourceId = dragOver.value;
  dragOver.value = "";
  if (!sourceId || !canUpdate.value) return;
  const source = findDept(dept.tree, sourceId);
  const check = canMoveDept(dept.tree, sourceId, target.id);
  if (!check.ok || !source) return;
  void confirm({
    title: "移动部门",
    message: `确定将「${source.name}」移动到「${target.name}」下？`,
    action: () => doMove(sourceId, target.id),
  });
}

function refMessage(error: BizError, fallback: string) {
  const refs = ((error.data as { refs?: { entity: string; count: number }[] })?.refs || []);
  if (!refs.length) return error.msg || fallback;
  const text = refs
    .map((item) => (item.entity === "人员" ? `人员 ${item.count} 人` : `${item.entity} ${item.count} 个`))
    .join("、");
  return `${fallback}（${text}）`;
}

async function changeStatus(node: DeptNode) {
  const next = node.status === "DISABLED" ? "ENABLED" : "DISABLED";
  const message = next === "DISABLED" ? "停用后该部门不能再作为新人员的部门，已有人员不受影响" : `确定启用部门「${node.name}」？`;
  await confirm({
    title: next === "DISABLED" ? "停用部门" : "启用部门",
    message,
    danger: next === "DISABLED",
    action: async () => {
      try {
        await call("dept_status_admin_api_ims_system_dept_update_status_put", { body: { id: node.id, status: next }, silent: true });
        await dept.reload();
      } catch (caught) {
        const biz = caught as BizError;
        throw new BizError(biz.code, biz.code === 1502 ? "请先停用下级部门" : biz.msg, biz.data, biz.traceId, biz.httpStatus);
      }
    },
  });
}

async function removeNode(node: DeptNode) {
  await confirm({
    title: "删除部门",
    message: `确定删除部门「${node.name}」？`,
    danger: true,
    action: async () => {
      try {
        await call("dept_delete_admin_api_ims_system_dept_delete_delete", { query: { id: node.id }, silent: true });
        await dept.reload();
      } catch (caught) {
        const biz = caught as BizError;
        throw new BizError(biz.code, refMessage(biz, "该部门下仍有子部门或人员"), biz.data, biz.traceId, biz.httpStatus);
      }
    },
  });
}

async function keepNode(node: DeptNode) {
  await confirm({
    title: "确认保留",
    message: `确认保留本地部门「${node.name}」在当前位置？`,
    action: async () => {
      await call("confirm_orphan_admin_api_ims_system_dept_confirm_orphan_put", { body: { id: node.id }, silent: true });
      await dept.reload();
    },
  });
}

function onMenu(node: DeptNode, key: string) {
  if (key === "create") openCreate(node);
  if (key === "rename") openRename(node);
  if (key === "move") openMove(node);
  if (key === "status") void changeStatus(node);
  if (key === "delete") void removeNode(node);
  if (key === "keep") void keepNode(node);
}

async function loadSync() {
  if (!canSync.value) return;
  try {
    const batch = await call<Record<string, unknown> | null>("org_latest_batch_admin_api_ims_system_org_sync_latest_batch_get", { silent: true });
    lastSync.value = batch?.finishedAt ? fmtTime(String(batch.finishedAt)) : "";
    if (batch?.status === "RUNNING") {
      syncing.value = true;
      window.setTimeout(() => void loadSync(), 3000);
    } else syncing.value = false;
  } catch {
    lastSync.value = "";
  }
}

async function syncOrg() {
  await confirm({
    title: "同步钉钉组织",
    message: "将以钉钉组织为准更新部门与人员，本地对钉钉部门的修改会被覆盖，本地新建的部门不受影响。确定同步？",
    action: async () => {
      syncing.value = true;
      try {
        const batch = await call<Record<string, unknown>>("org_reconcile_admin_api_ims_system_org_sync_reconcile_post", { silent: true });
        await dept.reload();
        const orphan = dept.flat.filter((item) => item.localOrphan).length;
        const summary = `同步完成：新增部门 ${batch.deptCreated || 0}、更新 ${batch.deptUpdated || 0}、停用 ${batch.deptDisabled || 0}；新增人员 ${batch.userCreated || 0}、离职 ${batch.userResigned || 0}；待分配 ${batch.unassignedCount || 0} 人`;
        toast.success(orphan ? `${summary}，有 ${orphan} 个本地部门待确认` : summary);
        lastSync.value = fmtTime(String(batch.finishedAt || new Date().toISOString()));
      } catch (caught) {
        const biz = caught as BizError;
        throw new BizError(biz.code, biz.code === 1001 ? "同步正在进行中" : biz.msg, biz.data);
      } finally {
        syncing.value = false;
      }
    },
  });
}

</script>

<template>
  <section class="panel">
    <header v-if="showSync && canSync">
      <button class="btn btn-sec btn-sm" type="button" :disabled="syncing" @click="syncOrg">{{ syncing ? "同步中…" : "同步钉钉组织" }}</button>
      <p class="muted">{{ lastSync ? `上次同步：${lastSync}` : "尚未同步" }}</p>
    </header>
    <input v-model="keyword" class="search" placeholder="搜索部门" />
    <label class="check"><input type="checkbox" :checked="dept.showDisabled" @change="dept.setShowDisabled(($event.target as HTMLInputElement).checked)" /> 显示停用部门</label>
    <EmptyState v-if="dept.error" type="error" @retry="dept.reload()" />
    <p v-else-if="applied && !filtered.length" class="muted">未找到匹配的部门</p>
    <ul v-else class="tree">
      <li :class="{ on: selected === null }" @click="choose(null)">全部</li>
      <li v-if="pendingNode" :class="{ on: selected === pendingNode.id }" :title="`直属 ${pendingNode.directMemberCount} 人，含下级共 ${pendingNode.memberCount} 人`" @click="choose(pendingNode.id)">
        待分配 <em v-if="showCount">{{ pendingNode.memberCount }}</em>
      </li>
      <DeptBranch
        v-for="node in filtered"
        :key="node.id"
        :node="node"
        :expanded="expanded"
        :selected="selected"
        :keyword="applied"
        :show-count="showCount"
        :drag-over="dragOver"
        :menu="menuOf"
        @toggle="toggle"
        @select="choose"
        @menu="onMenu"
        @drag="dragOver = $event"
        @drop="onDrop"
      />
    </ul>
    <FormDrawer v-model:open="formOpen" :title="formMode === 'create' ? '新增下级' : '修改部门'" size="S" :model="formModel" :submit="submitForm">
      <p v-if="dingHint" class="hint-bar">该部门来自钉钉，下次钉钉同步将以钉钉为准覆盖此修改</p>
      <div class="fld">
        <label><i class="req">*</i>部门名称</label>
        <el-input v-model="formModel.name" maxlength="50" />
      </div>
      <div class="fld">
        <label>负责人</label>
        <UserSelect v-model="formModel.leaderUserId as string" />
      </div>
      <div class="fld">
        <label>排序</label>
        <el-input v-model="formModel.sort" />
      </div>
    </FormDrawer>
    <AppModal v-model:open="moveOpen" title="移动部门" :width="520">
      <p v-if="moving?.source === 'DINGTALK'" class="muted">钉钉部门不能移到本地部门下</p>
      <DeptTreeSelect v-if="moving" v-model="moveTarget" :disabled-ids="blockedMoveIds(moving)" :disable-local="moving.source === 'DINGTALK'" />
      <template #footer>
        <button class="btn btn-pri" type="button" @click="confirmMove">确定</button>
      </template>
    </AppModal>
  </section>
</template>

<style scoped>
.panel { width: var(--tree-w); background: var(--card); border-radius: var(--r); padding: 12px; overflow: auto; max-height: calc(100vh - 140px); }
.search { width: 100%; height: 32px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 8px; margin: 8px 0; }
.tree, .tree ul { list-style: none; margin: 0; padding-left: 12px; }
.tree > li, :deep(.row) { display: flex; gap: 4px; align-items: center; min-height: 28px; cursor: pointer; font-size: 13px; }
.on, :deep(.on) { background: var(--blue-bg); }
:deep(.off) { color: var(--text2); }
:deep(em) { color: var(--text2); font-style: normal; }
:deep(.mini) { font-size: 12px; color: var(--st-info-fg); background: var(--st-info-bg); border-radius: var(--r-xs); padding: 0 4px; }
:deep(.warn) { color: var(--st-warning-fg); background: var(--st-warning-bg); }
:deep(.mute) { color: var(--st-neutral-fg); background: var(--st-neutral-bg); }
:deep(.exp), :deep(summary) { border: none; background: transparent; cursor: pointer; }
:deep(.more) { margin-left: auto; }
.check { font-size: 12px; color: var(--text2); }
</style>
