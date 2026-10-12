import { defineStore } from "pinia";
import { call } from "@/api/generated/endpoints";

export interface ExportTask {
  id: string;
  status: string;
  progress: number;
  error: string;
  fileKey: string;
}

function normalize(raw: unknown): ExportTask[] {
  const list = Array.isArray(raw) ? raw : ((raw as { list?: unknown[] })?.list ?? []);
  if (!Array.isArray(list)) return [];
  return list.map((item) => {
    const row = item as Record<string, unknown>;
    return {
      id: String(row.id ?? ""),
      status: String(row.status || ""),
      progress: Number(row.progress || 0),
      error: String(row.error || ""),
      fileKey: String(row.fileKey || ""),
    };
  });
}

export const useDownloadStore = defineStore("download", {
  state: () => ({
    tasks: [] as ExportTask[],
    collapsed: false,
    timer: 0,
  }),
  getters: {
    active(state): boolean {
      return state.tasks.some((item) => item.status === "PENDING" || item.status === "RUNNING");
    },
    visible(state): boolean {
      return state.tasks.length > 0 && !state.collapsed;
    },
  },
  actions: {
    async refresh() {
      const data = await call<unknown>("export_my_page_admin_api_ims_export_task_my_page_get", { silent: true });
      this.tasks = normalize(data);
      if (!this.active) this.stop();
    },
    start() {
      if (this.timer) return;
      this.timer = window.setInterval(() => {
        void this.refresh();
      }, 3000);
    },
    stop() {
      if (this.timer) window.clearInterval(this.timer);
      this.timer = 0;
    },
    async track() {
      await this.refresh();
      if (this.active) this.start();
    },
  },
});
