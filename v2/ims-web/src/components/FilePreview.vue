<script setup lang="ts">
import { ref } from "vue";
import { call } from "@/api/generated/endpoints";
import { BizError } from "@/api/http";

const props = defineProps<{ fileKey: string; watermark?: boolean }>();
const error = ref("");
const imageUrl = ref("");

async function openPreview() {
  error.value = "";
  try {
    const blob = await call<Blob>("file_preview_admin_api_ims_file_preview_get", {
      query: { fileKey: props.fileKey },
      responseType: "blob",
      silent: true,
    });
    const type = blob.type || "";
    const url = URL.createObjectURL(blob);
    if (type.startsWith("image/")) imageUrl.value = url;
    else window.open(url, "_blank");
  } catch (caught) {
    const biz = caught as BizError;
    error.value = biz.code === 1504 ? "文件不可用" : biz.msg || "文件不可用";
  }
}
</script>

<template>
  <span>
    <button class="btn btn-txt" type="button" @click="openPreview">预览</button>
    <img v-if="imageUrl" :src="imageUrl" alt="" class="pic" />
    <p v-if="error" class="ferr">{{ error }}</p>
  </span>
</template>

<style scoped>
.pic { display: block; max-width: 240px; margin-top: 8px; border-radius: var(--r-s); }
</style>
