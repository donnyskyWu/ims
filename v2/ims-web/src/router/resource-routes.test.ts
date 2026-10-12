import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createAppRouter } from "@/router";
import { useAuthStore } from "@/stores/auth";

describe("resource routes", () => {
  it("opens certificate tabs and redirects the expire deep link", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.accessToken = "token";
    auth.ready = true;
    auth.pwdResetRequired = false;
    const router = await createAppRouter();
    const certificate = router.getRoutes().find((item) => item.name === "corp-certificate");
    expect(certificate?.path).toBe("/ims/corp/resource/certificate");
    const anyPerm = certificate?.meta.anyPerm as string[];
    expect(anyPerm).toContain("ims:cert:expire:query");
    expect(anyPerm).toContain("ims:cert:archive:query");
    const company = router.getRoutes().find((item) => item.name === "corp-company");
    expect(company?.meta.perm).toBe("ims:corp:company:query");
    await router.push("/ims/cert/expire?certId=9");
    expect(router.currentRoute.value.path).toBe("/ims/corp/resource/certificate");
    expect(router.currentRoute.value.query.tab).toBe("expire");
    expect(router.currentRoute.value.query.certId).toBe("9");
    const names = router.getRoutes().map((item) => item.path);
    expect(names.some((path) => path.includes("账号管理") || path.includes("设备管理"))).toBe(false);
  });
});
