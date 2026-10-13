import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import type { RouteLocationNormalized } from "vue-router";
import { createAppRouter } from "@/router";
import { useAuthStore } from "@/stores/auth";
import { routeAllowed } from "@/router/access";

describe("ip group routes", () => {
  it("registers the operations page and the author deep link", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.accessToken = "token";
    auth.ready = true;
    auth.pwdResetRequired = false;
    auth.permCodes = ["ims:ip-group:query", "ims:ip-group:author:query"];
    const router = await createAppRouter();
    const ops = router.getRoutes().find((item) => item.name === "ip-group");
    const author = router.getRoutes().find((item) => item.name === "ip-group-author");
    expect(ops?.path).toBe("/ims/ip-group");
    expect(ops?.meta.perm).toBe("ims:ip-group:query");
    expect(author?.path).toBe("/ims/ip-group/author");
    expect(author?.meta.perm).toBe("ims:ip-group:author:query");
    expect(author?.meta.view).toBe("author");
    const hidden = router.resolve("/ims/ip-group") as unknown as RouteLocationNormalized;
    expect(routeAllowed(hidden, [], auth.permCodes)).toBe(true);
    expect(routeAllowed(hidden, [], [])).toBe(false);
    const authorRoute = router.resolve("/ims/ip-group/author") as unknown as RouteLocationNormalized;
    expect(routeAllowed(authorRoute, [], ["ims:ip-group:query"])).toBe(false);
    expect(routeAllowed(authorRoute, [], auth.permCodes)).toBe(true);
  });
});
