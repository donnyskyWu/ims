import { defineStore } from "pinia";
import { call } from "@/api/generated/endpoints";

const UNREAD = "message_unread_count_admin_api_ims_message_unread_count_get";

export const useInboxStore = defineStore("inbox", {
  state: () => ({
    unread: 0,
    open: false,
  }),
  actions: {
    async refresh() {
      try {
        const data = await call<{ count: number }>(UNREAD, { silent: true });
        this.unread = Math.max(0, Number(data.count || 0));
      } catch {
        return;
      }
    },
    setUnread(value: number) {
      this.unread = Math.max(0, Number(value || 0));
    },
    show() {
      this.open = true;
    },
  },
});
