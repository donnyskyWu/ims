<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import Perm from "@/components/Perm.vue";
import MaskedText from "@/components/MaskedText.vue";
import RoleSelect from "@/components/RoleSelect.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import { systemApi, type Row } from "@/api/system";
import { toast } from "@/utils/toast";

const groups = ["内容审核", "钉钉", "钉钉考勤", "AI", "通用"];
const rows = ref<Row[]>([]);
const active = ref(groups[0]);
const drafts = ref<Record<string, string>>({});
const historyOpen = ref(false);
const history = ref<Row[]>([]);
const historyTitle = ref("");

const tabs = computed(() => {
  const extra = rows.value.map((item) => String(item.groupName || "")).filter((name) => name && !groups.includes(name));
  return [...groups, ...new Set(extra)].map((key) => ({ key, label: key }));
});
const visible = computed(() => rows.value.filter((item) => String(item.groupName || "") === active.value));

async function load() {
  rows.value = await systemApi.params();
  const next: Record<string, string> = {};
  for (const row of rows.value) next[String(row.paramKey)] = row.valueType === "SECRET" ? "" : String(row.value ?? "");
  drafts.value = next;
}

async function save(row: Row) {
  const key = String(row.paramKey);
  await systemApi.paramSave(key, drafts.value[key] ?? "");
  toast.success("保存成功");
  await load();
}

async function openHistory(row: Row) {
  historyTitle.value = String(row.name || row.paramKey);
  history.value = await systemApi.paramHistory(String(row.paramKey));
  historyOpen.value = true;
}

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="参数" sub-title="分组为内容审核、钉钉、钉钉考勤、AI 开关和通用。培训 AI 不在本页。" />
    <AppTabs v-model:active="active" :items="tabs" />
    <div v-for="row in visible" :key="String(row.paramKey)" class="item">
      <div>
        <strong>{{ row.name }}</strong>
        <p class="muted">{{ row.paramKey }} <span v-if="row.remark">· {{ row.remark }}</span></p>
        <p v-if="row.valueType === 'ROLE_REF' && row.roleName" class="muted">当前角色：{{ row.roleName }}</p>
      </div>
      <div class="edit">
        <MaskedText v-if="row.valueType === 'SECRET'" :value="String(row.value || '')" />
        <el-switch v-if="row.valueType === 'BOOLEAN'" :model-value="drafts[String(row.paramKey)] === 'true'" @change="drafts[String(row.paramKey)] = $event ? 'true' : 'false'" />
        <el-select v-else-if="row.valueType === 'ENUM'" v-model="drafts[String(row.paramKey)]">
          <el-option v-for="item in (row.options as string[]) || []" :key="item" :label="item" :value="item" />
        </el-select>
        <RoleSelect v-else-if="row.valueType === 'ROLE_REF'" v-model="drafts[String(row.paramKey)]" allow-inactive />
        <el-input v-else v-model="drafts[String(row.paramKey)]" :placeholder="row.valueType === 'SECRET' ? '留空表示不修改' : ''" />
        <Perm code="ims:system:param:update"><button class="btn btn-pri" type="button" @click="save(row)">保存</button></Perm>
        <button class="btn btn-txt" type="button" @click="openHistory(row)">历史</button>
      </div>
    </div>
    <DetailDrawer v-model:open="historyOpen" :title="historyTitle + ' 变更'">
      <ul>
        <li v-for="(item, index) in history" :key="index">{{ item.field }}：{{ item.before }} → {{ item.after }}（{{ item.time }}）</li>
      </ul>
      <p v-if="!history.length" class="muted">暂无变更</p>
    </DetailDrawer>
  </section>
</template>

<style scoped>
.item { display: flex; justify-content: space-between; gap: 16px; padding: 12px 0; border-bottom: 1px solid var(--line); }
.edit { display: flex; gap: 8px; align-items: center; min-width: 360px; }
</style>
