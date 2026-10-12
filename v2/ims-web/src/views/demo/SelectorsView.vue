<script setup lang="ts">
import { ref } from "vue";
import UserSelect from "@/components/UserSelect.vue";
import DeptTreeSelect from "@/components/DeptTreeSelect.vue";
import PositionSelect from "@/components/PositionSelect.vue";
import RoleSelect from "@/components/RoleSelect.vue";
import DictSelect from "@/components/DictSelect.vue";
import PeriodPicker from "@/components/PeriodPicker.vue";
import RealNameSelect from "@/components/RealNameSelect.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import IpGroupSelect from "@/components/IpGroupSelect.vue";
import AuthorSelect from "@/components/AuthorSelect.vue";
import CompanySelect from "@/components/CompanySelect.vue";
import AssetSelect from "@/components/AssetSelect.vue";
import SimCardSelect from "@/components/SimCardSelect.vue";
import MatchSelect from "@/components/MatchSelect.vue";
import TopicSelect from "@/components/TopicSelect.vue";
import DeptTree from "@/components/DeptTree.vue";

const user = ref("u-2");
const dept = ref("");
const position = ref("");
const role = ref("");
const created = ref("");
const editing = ref("X");
const querying = ref("");
const range = ref<string[] | null>(null);
const realname = ref("");
const account = ref("");
const group = ref("");
const author = ref("");
const company = ref("");
const asset = ref("");
const sim = ref("");
const match = ref("");
const topic = ref("");
const selected = ref<string | null>(null);
</script>

<template>
  <section class="page">
    <h1>选择器</h1>
    <div class="grid">
      <label>人员<UserSelect v-model="user" /></label>
      <label>部门<DeptTreeSelect v-model="dept" /></label>
      <label>岗位<PositionSelect v-model="position" /></label>
      <label>角色<RoleSelect v-model="role" /></label>
      <label>新建字典<DictSelect v-model="created" dict-type="dict_demo_status" mode="create" /></label>
      <label>编辑字典<DictSelect v-model="editing" dict-type="dict_demo_status" mode="edit" /></label>
      <label>查询字典<DictSelect v-model="querying" dict-type="dict_demo_status" mode="query" /></label>
      <label>日期<PeriodPicker v-model="range" :max-range="31" /></label>
      <label>实名人<RealNameSelect v-model="realname" /></label>
      <label>平台账号<AccountSelect v-model="account" /></label>
      <label>分组<IpGroupSelect v-model="group" /></label>
      <label>作者<AuthorSelect v-model="author" :account-id="account || undefined" /></label>
      <label>公司<CompanySelect v-model="company" /></label>
      <label>设备<AssetSelect v-model="asset" /></label>
      <label>手机卡<SimCardSelect v-model="sim" /></label>
      <label>赛事<MatchSelect v-model="match" /></label>
      <label>选题<TopicSelect v-model="topic" /></label>
    </div>
    <DeptTree v-model:selected="selected" :editable="false" :show-sync="false" />
  </section>
</template>

<style scoped>
h1 { font-size: 28px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text2); }
</style>
