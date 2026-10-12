import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createAppRouter } from "@/router";
import { useAuthStore } from "@/stores/auth";

describe("device routes", () => {
  it("opens device pages and redirects the old asset paths", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.accessToken = "token";
    auth.ready = true;
    auth.pwdResetRequired = false;
    const router = await createAppRouter();
    const office = router.getRoutes().find((item) => item.name === "device-office");
    const live = router.getRoutes().find((item) => item.name === "device-live");
    const phone = router.getRoutes().find((item) => item.name === "device-phone");
    expect(office?.meta.perm).toBe("ims:device:asset:query");
    expect(live?.meta.deviceKind).toBe("live");
    expect(phone?.path).toBe("/ims/corp/device/phone");
    expect(router.getRoutes().some((item) => item.name === "asset-reverse")).toBe(false);
    await router.push("/ims/asset/reverse?userId=8");
    expect(router.currentRoute.value.path).toBe("/ims/corp/device/office");
    expect(router.currentRoute.value.query.drawer).toBe("reverse");
    await router.push("/ims/asset/verify?taskId=3");
    expect(router.currentRoute.value.query.drawer).toBe("verify");
    expect(router.currentRoute.value.query.taskId).toBe("3");
    await router.push("/ims/asset/ledger");
    expect(router.currentRoute.value.query.drawer).toBe("ledger");
  });
});
