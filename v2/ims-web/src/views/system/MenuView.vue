<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import Perm from "@/components/Perm.vue";
import { systemApi, type Row } from "@/api/system";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { requiredRule } from "@/components/form/rules";

interface MenuNode {
  id: string;
  name: string;
  path: string;
  permCode: string;
  type: string;
  visible: number;
  sort: number;
  keepAlive: number;
  seedLocked: boolean;
  children: MenuNode[];
}

const tree = ref<MenuNode[]>([]);
const drawer = ref(false);
const editing = ref<MenuNode | null>(null);
const form = ref<Row>({ name: "", type: "MENU", permCode: "", path: "", parentId: "0", sort: 0, visible: true, keepAlive: false, icon: "" });

function nodes(raw: unknown): MenuNode[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const row = item as Row;
    return {
      id: String(row.id),
      name: String(row.name || ""),
      path: String(row.path || ""),
      permCode: String(row.permCode || ""),
      type: String(row.type || ""),
      visible: Number(row.visible || 0),
      sort: Number(row.sort || 0),
      keepAlive: Number(row.keepAlive || 0),
      seedLocked: Boolean(row.seedLocked),
      children: nodes(row.children),
    };
  });
}

async function load() {
  tree.value = nodes(await systemApi.menuTree());
}

function openCreate(parent?: MenuNode) {
  editing.value = null;
  form.value = { name: "", type: "MENU", permCode: "", path: "", parentId: parent?.id || "0", sort: 0, visible: true, keepAlive: false, icon: "" };
  drawer.value = true;
}

function openEdit(node: MenuNode) {
  editing.value = node;
  form.value = { id: node.id, name: node.name, type: node.type, permCode: node.permCode, path: node.path, sort: node.sort, visible: node.visible === 1, keepAlive: node.keepAlive === 1, icon: "" };
  drawer.value = true;
}

async function save(model: Row) {
  return systemApi.menuSave(model, Boolean(editing.value));
}

async function remove(node: MenuNode) {
  try {
    await confirm({ title: "删除菜单", message: `删除「${node.name}」？有下级或授权时会拒绝。`, danger: true, action: async () => { await systemApi.menuDelete(node.id); } });
    toast.success("删除成功");
    await load();
  } catch { /* 取消 */ }
}

async function toggle(node: MenuNode) {
  await systemApi.menuVisible(node.id, node.visible !== 1);
  await load();
}

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="菜单" sub-title="种子菜单的路由和权限码锁定，名称、排序和显隐可以改。">
      <template #actions>
        <Perm code="ims:system:menu:create"><button class="btn btn-pri" type="button" @click="openCreate()">新建</button></Perm>
      </template>
    </PageHeader>
    <el-tree :data="tree" node-key="id" default-expand-all :props="{ label: 'name', children: 'children' }">
      <template #default="{ data }">
        <span class="node">
          <span>{{ data.name }}</span>
          <em>{{ data.type }} {{ data.permCode }}</em>
          <em v-if="data.seedLocked">种子锁定</em>
          <em v-if="!data.visible">隐藏</em>
          <Perm code="ims:system:menu:create"><button class="btn btn-txt" type="button" @click.stop="openCreate(data)">下级</button></Perm>
          <Perm code="ims:system:menu:update"><button class="btn btn-txt" type="button" @click.stop="openEdit(data)">编辑</button></Perm>
          <Perm code="ims:system:menu:update"><button class="btn btn-txt" type="button" @click.stop="toggle(data)">{{ data.visible ? "隐藏" : "显示" }}</button></Perm>
          <Perm code="ims:system:menu:delete"><button class="btn btn-txt" type="button" @click.stop="remove(data)">删除</button></Perm>
        </span>
      </template>
    </el-tree>
    <FormDrawer v-model:open="drawer" :title="editing ? '编辑菜单' : '新建菜单'" :model="form" :rules="{ name: requiredRule('名称') }" :submit="save" @saved="load">
      <el-form-item label="名称" prop="name"><el-input v-model="form.name" maxlength="50" /></el-form-item>
      <el-form-item label="类型">
        <el-select v-model="form.type" :disabled="Boolean(editing)"><el-option label="目录" value="DIR" /><el-option label="菜单" value="MENU" /><el-option label="按钮" value="BUTTON" /></el-select>
      </el-form-item>
      <el-form-item label="权限码"><el-input v-model="form.permCode" :disabled="Boolean(editing?.seedLocked)" /></el-form-item>
      <el-form-item label="路由"><el-input v-model="form.path" :disabled="Boolean(editing?.seedLocked)" /></el-form-item>
      <el-form-item v-if="!editing" label="上级编号"><el-input v-model="form.parentId" /></el-form-item>
      <el-form-item label="排序"><el-input v-model="form.sort" /></el-form-item>
      <el-form-item label="显示"><el-switch v-model="form.visible" /></el-form-item>
      <el-form-item label="缓存"><el-switch v-model="form.keepAlive" /></el-form-item>
    </FormDrawer>
  </section>
</template>

<style scoped>
.node { display: inline-flex; gap: 8px; align-items: center; }
em { color: var(--text2); font-style: normal; font-size: 12px; }
</style>
