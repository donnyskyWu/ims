import { describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { createAppRouter } from "@/router";
import { useAuthStore } from "@/stores/auth";

describe("ip group routes", () => {
  it("registers the group page and the author deep link", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.accessToken = "token";
    auth.ready = true;
    auth.pwdResetRequired = false;
    auth.permCodes = ["ims:ip-group:query", "ims:ip-group:author:query"];
    const router = await createAppRouter();
    const group = router.getRoutes().find((item) => item.name === "ip-group");
    const author = router.getRoutes().find((item) => item.name === "ip-group-author");
    expect(group?.path).toBe("/ims/ip-group");
    expect(group?.meta.perm).toBe("ims:ip-group:query");
    expect(author?.path).toBe("/ims/ip-group/author");
    expect(author?.meta.perm).toBe("ims:ip-group:author:query");
    await router.push("/ims/ip-group/author");
    expect(router.currentRoute.value.name).toBe("ip-group-author");
  });
});
