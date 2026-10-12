import { defineStore } from "pinia";
import { call } from "@/api/generated/endpoints";
import { flattenDept, normalizeDept, type DeptNode } from "@/components/dept/tree-logic";

export const useDeptStore = defineStore("dept", {
  state: () => ({
    tree: [] as DeptNode[],
    loaded: false,
    loading: false,
    error: false,
    showDisabled: false,
    version: 0,
  }),
  getters: {
    flat(state): DeptNode[] {
      return flattenDept(state.tree);
    },
  },
  actions: {
    async load(force = false) {
      if (this.loading) return;
      if (this.loaded && !force) return;
      this.loading = true;
      this.error = false;
      try {
        const data = await call<unknown[]>("dept_tree_admin_api_ims_system_dept_tree_get", {
          query: this.showDisabled ? { status: "ALL" } : {},
          silent: true,
        });
        const list = Array.isArray(data) ? data : [];
        this.tree = list.map((item) => normalizeDept(item));
        this.loaded = true;
        this.version += 1;
      } catch {
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
    async reload() {
      this.loaded = false;
      await this.load(true);
    },
    async setShowDisabled(value: boolean) {
      this.showDisabled = value;
      await this.reload();
    },
    nameOf(id: string | null | undefined): string {
      if (!id) return "";
      return this.flat.find((item) => item.id === id)?.name || "";
    },
  },
});
