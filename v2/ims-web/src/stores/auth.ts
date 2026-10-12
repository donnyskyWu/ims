import { defineStore } from "pinia";
import { call } from "@/api/generated/endpoints";
import { bindSession } from "@/api/http";
import type { PermDetail } from "@/utils/perm";

const ACCESS = "ims.access";
const REFRESH = "ims.refresh";
const RESET = "ims.pwdReset";

export interface MenuNode {
  id: string;
  name: string;
  permCode: string | null;
  type: string;
  path: string | null;
  children: MenuNode[];
}

export interface SessionUser {
  id: string;
  username: string;
  nickname: string;
  avatar: string;
  mainDeptName: string;
  deptNames: string[];
  positionLabel: string;
  pwdResetRequired: boolean;
}

function textId(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function normalizeMenus(nodes: unknown): MenuNode[] {
  if (!Array.isArray(nodes)) return [];
  return nodes.map((item) => {
    const node = item as Record<string, unknown>;
    return {
      id: textId(node.id),
      name: String(node.name || ""),
      permCode: node.permCode ? String(node.permCode) : null,
      type: String(node.type || ""),
      path: node.path ? String(node.path) : null,
      children: normalizeMenus(node.children),
    };
  });
}

function normalizeDetails(raw: unknown): Record<string, PermDetail> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out: Record<string, PermDetail> = {};
  for (const [key, value] of Object.entries(raw as Record<string, PermDetail>)) {
    out[key] = value || {};
  }
  return out;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem(ACCESS) || "",
    refreshToken: localStorage.getItem(REFRESH) || "",
    user: null as SessionUser | null,
    menus: [] as MenuNode[],
    permCodes: [] as string[],
    permDetails: {} as Record<string, PermDetail>,
    dataScopeText: "",
    hint: "",
    pwdResetRequired: localStorage.getItem(RESET) === "1",
    ready: false,
  }),
  getters: {
    loggedIn: (state) => Boolean(state.accessToken),
  },
  actions: {
    persist() {
      if (this.accessToken) localStorage.setItem(ACCESS, this.accessToken);
      else localStorage.removeItem(ACCESS);
      if (this.refreshToken) localStorage.setItem(REFRESH, this.refreshToken);
      else localStorage.removeItem(REFRESH);
      localStorage.setItem(RESET, this.pwdResetRequired ? "1" : "0");
    },
    applySession(payload: { accessToken?: string; refreshToken?: string; pwdResetRequired?: boolean }) {
      if (payload.accessToken) this.accessToken = payload.accessToken;
      if (payload.refreshToken) this.refreshToken = payload.refreshToken;
      if (typeof payload.pwdResetRequired === "boolean") this.pwdResetRequired = payload.pwdResetRequired;
      this.persist();
    },
    applyMe(payload: Record<string, unknown>) {
      const nested = (payload.user || null) as Record<string, unknown> | null;
      const source = nested || payload;
      const reset = typeof nested?.pwdResetRequired === "boolean" ? Boolean(nested.pwdResetRequired) : this.pwdResetRequired;
      this.user = {
        id: textId(source.id),
        username: String(source.username || ""),
        nickname: String(source.nickname || source.username || ""),
        avatar: String(source.avatar || ""),
        mainDeptName: String(source.mainDeptName || ""),
        deptNames: Array.isArray(source.deptNames) ? source.deptNames.map(String) : [],
        positionLabel: String(source.positionLabel || ""),
        pwdResetRequired: reset,
      };
      this.pwdResetRequired = reset;
      this.menus = normalizeMenus(payload.menus);
      this.permCodes = Array.isArray(payload.permCodes) ? payload.permCodes.map(String) : [];
      this.permDetails = normalizeDetails(payload.permDetails);
      this.dataScopeText = String(payload.dataScopeText || "");
      this.hint = String(payload.hint || "");
      this.ready = true;
      this.persist();
    },
    async login(username: string, password: string) {
      const data = await call<{ accessToken: string; refreshToken: string; pwdResetRequired?: boolean }>(
        "login_admin_api_ims_auth_login_post",
        { body: { username, password }, silent: true },
      );
      this.applySession(data);
      await this.fetchMe();
    },
    async fetchMe() {
      const data = await call<Record<string, unknown>>("me_admin_api_ims_auth_me_get");
      this.applyMe(data);
    },
    async refreshMeSilent() {
      if (!this.accessToken) return;
      try {
        const data = await call<Record<string, unknown>>("me_admin_api_ims_auth_me_get", { silent: true });
        this.applyMe(data);
      } catch {
        /* 静默刷新失败时保留当前会话，交给下一次请求处理 */
      }
    },
    async refreshTokens(): Promise<boolean> {
      if (!this.refreshToken) return false;
      try {
        const data = await call<{ accessToken: string; refreshToken: string }>("refresh_token_admin_api_ims_auth_refresh_token_post", {
          body: { refreshToken: this.refreshToken },
          silent: true,
        });
        this.applySession(data);
        return true;
      } catch {
        return false;
      }
    },
    clearLocal() {
      this.accessToken = "";
      this.refreshToken = "";
      this.user = null;
      this.menus = [];
      this.permCodes = [];
      this.permDetails = {};
      this.dataScopeText = "";
      this.hint = "";
      this.pwdResetRequired = false;
      this.ready = false;
      this.persist();
    },
    async logout() {
      try {
        await call("logout_admin_api_ims_auth_logout_post", { silent: true });
      } catch {
        /* 本地会话仍然清除 */
      }
      this.clearLocal();
    },
  },
});

export function installAuthBridge(store: ReturnType<typeof useAuthStore>, goLogin: (kind: "kick" | "expired") => void): void {
  bindSession({
    authHeader: () => (store.accessToken ? `Bearer ${store.accessToken}` : null),
    refresh: () => store.refreshTokens(),
    onKick: () => {
      store.clearLocal();
      goLogin("kick");
    },
    onExpired: () => {
      store.clearLocal();
      goLogin("expired");
    },
  });
  window.addEventListener("storage", (event) => {
    if (event.key === ACCESS && !event.newValue) {
      store.clearLocal();
      goLogin("expired");
    }
  });
  window.addEventListener("focus", () => {
    void store.refreshMeSilent();
  });
  window.setInterval(() => {
    void store.refreshMeSilent();
  }, 5 * 60 * 1000);
}
