import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createAppRouter } from "@/router";
import { useAuthStore } from "@/stores/auth";

describe("live routes", () => {
  it("registers sessions, alarm and ledger, and redirects the old paths", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.accessToken = "token";
    auth.ready = true;
    auth.pwdResetRequired = false;
    auth.permCodes = ["ims:live:session:query", "ims:live:alarm:query", "ims:live:ledger:query"];
    const router = await createAppRouter();
    expect(router.getRoutes().find((item) => item.name === "live-sessions")?.path).toBe("/ims/live/sessions");
    expect(router.getRoutes().find((item) => item.name === "live-alarm")?.meta.perm).toBe("ims:live:alarm:query");
    expect(router.getRoutes().find((item) => item.name === "live-ledger")?.meta.perm).toBe("ims:live:ledger:query");
    await router.push("/ims/live/register");
    expect(router.currentRoute.value.path).toBe("/ims/live/sessions");
    expect(router.currentRoute.value.query.tab).toBe("risk");
    await router.push("/ims/live/report");
    expect(router.currentRoute.value.fullPath).toContain("tab=pending");
  });
});
