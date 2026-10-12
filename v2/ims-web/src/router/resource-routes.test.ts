import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createAppRouter } from "@/router";

describe("resource routes", () => {
  it("opens certificate tabs and redirects the expire deep link", async () => {
    setActivePinia(createPinia());
    const router = await createAppRouter();
    const certificate = router.getRoutes().find((item) => item.name === "corp-certificate");
    expect(certificate?.path).toBe("/ims/corp/resource/certificate");
    const anyPerm = certificate?.meta.anyPerm as string[];
    expect(anyPerm).toContain("ims:cert:expire:query");
    expect(anyPerm).toContain("ims:cert:archive:query");
    const company = router.getRoutes().find((item) => item.name === "corp-company");
    expect(company?.meta.perm).toBe("ims:corp:company:query");
    const redirected = router.resolve("/ims/cert/expire?certId=9");
    expect(redirected.path).toBe("/ims/corp/resource/certificate");
    expect(redirected.query.tab).toBe("expire");
    expect(redirected.query.certId).toBe("9");
    const names = router.getRoutes().map((item) => item.path);
    expect(names.some((path) => path.includes("账号管理") || path.includes("设备管理"))).toBe(false);
  });
});
