<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import PasswordForm from "@/components/PasswordForm.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import { systemApi, type Row } from "@/api/system";
import { useAuthStore } from "@/stores/auth";
import { toast } from "@/utils/toast";

const auth = useAuthStore();
const router = useRouter();
const profile = ref<Row>({});
const sessions = ref<Row[]>([]);

const columns: TableColumn[] = [
  { key: "loginAt", label: "登录时间", type: "time" },
  { key: "ip", label: "地址" },
  { key: "device", label: "设备" },
  { key: "currentText", label: "当前" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [{ label: "下线", show: (row) => !row.current, onClick: (row) => void drop(row) }],
  },
];

async function load() {
  profile.value = await systemApi.me();
  const list = await systemApi.sessions();
  sessions.value = list.map((item) => ({ ...item, currentText: item.current ? "本机" : "" }));
}

async function saved() {
  toast.success("保存成功");
  await load();
}

async function drop(row: Row) {
  const data = await systemApi.dropSession(String(row.sid));
  if (data.logout) {
    auth.clearLocal();
    await router.replace("/login");
    return;
  }
  toast.success("已下线");
  await load();
}

onMounted(() => { void load(); });
</script>

<template>
  <section>
    <PageHeader title="个人中心" :show-scope="false" />
    <DescriptionList
      :items="[
        { label: '用户名', value: profile.username },
        { label: '姓名', value: profile.nickname },
        { label: '主部门', value: profile.mainDeptName },
        { label: '角色', value: Array.isArray(profile.roleNames) ? profile.roleNames.join('、') : '' },
        { label: '手机', value: profile.mobile, type: 'masked' },
        { label: '钉钉', value: profile.dingtalkBound ? '已绑定' : '未绑定' },
      ]"
    />
    <h2>{{ profile.hasPassword ? "修改密码" : "设置密码" }}</h2>
    <PasswordForm :mode="profile.hasPassword ? 'change' : 'set'" @saved="saved" />
    <h2>我的会话</h2>
    <DataTable :columns="columns" :data="sessions" />
  </section>
</template>

<style scoped>
h2 { margin: 24px 0 8px; font-size: 18px; }
</style>
