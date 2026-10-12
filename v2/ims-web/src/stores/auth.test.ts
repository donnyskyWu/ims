import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { call } from "@/api/generated/endpoints";
import { useAuthStore } from "./auth";

vi.mock("@/api/generated/endpoints", () => ({
  call: vi.fn(),
}));

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
    vi.mocked(call).mockReset();
  });

  it("normalizes the current user and keeps string ids", () => {
    const store = useAuthStore();
    store.applyMe({
      id: "42",
      username: "qa",
      nickname: "测试",
      permCodes: ["ims:demo:order:query"],
      menus: [{ id: "7", name: "示例", permCode: "ims:demo:order:query", type: "MENU", children: [] }],
      dataScopeText: "全部数据",
      permDetails: { "ims:demo:order:query": { r: 1, w: 0, d: 0 } },
    });
    expect(store.user?.id).toBe("42");
    expect(store.menus[0].id).toBe("7");
    expect(store.permDetails["ims:demo:order:query"].w).toBe(0);
  });

  it("stores tokens from login and clears them on logout", async () => {
    vi.mocked(call).mockImplementation(async (operationId: string) => {
      if (operationId.includes("login")) return { accessToken: "a", refreshToken: "r", pwdResetRequired: true };
      if (operationId.includes("auth_me")) return { id: "1", username: "qa", nickname: "测试", permCodes: [], menus: [] };
      return {};
    });
    const store = useAuthStore();
    await store.login("qa", "secret");
    expect(store.accessToken).toBe("a");
    expect(store.pwdResetRequired).toBe(true);
    expect(localStorage.getItem("ims.access")).toBe("a");
    await store.logout();
    expect(store.accessToken).toBe("");
    expect(localStorage.getItem("ims.access")).toBeNull();
  });
});
