<script setup lang="ts">
import { reactive, ref } from "vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AppModal from "@/components/AppModal.vue";
import StepsWizard from "@/components/StepsWizard.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { emailRule, integerRule, mobileRule, moneyRule, percentRule, requiredRule } from "@/components/form/rules";

const size = ref<"S" | "M" | "L">("M");
const open = ref(false);
const model = reactive<Record<string, unknown>>({ name: "", mobile: "", email: "", amount: "", rate: "", count: "", enabled: false });
const modalWidth = ref<360 | 520 | 800>(520);
const modal = ref(false);
const step = ref(0);
const stepName = ref("");

async function save(payload: Record<string, unknown>) {
  if (payload.mobile && !/^1\d{10}$/.test(String(payload.mobile))) throw Object.assign(new Error("手机号格式不正确"), { code: 1001 });
  return payload;
}
</script>

<template>
  <section class="page">
    <h1>表单</h1>
    <div class="row">
      <button v-for="item in (['S', 'M', 'L'] as const)" :key="item" class="btn btn-sec" type="button" @click="size = item; open = true">{{ item === 'S' ? '小' : item === 'M' ? '中' : '大' }}抽屉</button>
      <button v-for="item in ([360, 520, 800] as const)" :key="item" class="btn btn-sec" type="button" @click="modalWidth = item; modal = true">弹窗 {{ item }}</button>
      <button class="btn btn-sec" type="button" @click="confirm({ title: '作废', message: '确定作废？', danger: true, reasonRequired: true })">作废</button>
      <button class="btn btn-sec" type="button" @click="toast.success('同一提示')">同一提示</button>
    </div>
    <FormDrawer v-model:open="open" :size="size" title="表单" :model="model" :rules="{ name: [requiredRule('名称')], mobile: [mobileRule], email: [emailRule], amount: [moneyRule], rate: [percentRule], count: [integerRule] }" :submit="save">
      <div class="formrow">
        <el-form-item label="名称" prop="name"><el-input v-model="model.name" /></el-form-item>
        <el-form-item label="手机号" prop="mobile"><el-input v-model="model.mobile" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="model.email" /></el-form-item>
        <el-form-item label="金额" prop="amount"><el-input v-model="model.amount" /></el-form-item>
        <el-form-item label="比例" prop="rate"><el-input v-model="model.rate" /></el-form-item>
        <el-form-item label="数量" prop="count"><el-input v-model="model.count" /></el-form-item>
        <el-form-item class="span-2" label="启用"><button class="sw" :class="{ on: model.enabled }" type="button" @click="model.enabled = !model.enabled"><i /></button></el-form-item>
      </div>
    </FormDrawer>
    <AppModal v-model:open="modal" title="结果" :width="modalWidth"><p>处理完成</p></AppModal>
    <StepsWizard v-model:current="step" :steps="[{ key: 'a', title: '基本信息', validate: async () => Boolean(stepName) }, { key: 'b', title: '确认' }]">
      <template #a><input v-model="stepName" placeholder="名称" /></template>
      <template #b><p>已填写 {{ stepName }}</p></template>
    </StepsWizard>
  </section>
</template>

<style scoped>
.row { display: flex; gap: 8px; flex-wrap: wrap; }
h1 { font-size: 28px; }
input { height: 34px; border: 1px solid var(--line2); border-radius: var(--r-s); padding: 0 8px; }
</style>
