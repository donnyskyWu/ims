import { describe, expect, it } from "vitest";
import { inDingTalk, landingPath, preferredTab, ssoErrorText, type MenuLike } from "./login-logic";

const menus: MenuLike[] = [
  {
    path: "/ims/auth",
    children: [
      { path: "/ims/auth/org" },
      { path: "/ims/auth/position" },
    ],
  },
];

describe("login logic", () => {
  it("keeps only the callback error codes", () => {
    const messages = { 1216: "账号已冻结或已离职，无法登录", 9999: "隐藏" };
    expect(ssoErrorText("1216", messages)).toContain("离职");
    expect(ssoErrorText("9999", messages)).toBe("");
    expect(ssoErrorText(null, messages)).toBe("");
  });

  it("defaults to ding talk and remembers account login", () => {
    expect(preferredTab(null, true)).toBe("ding");
    expect(preferredTab("account", true)).toBe("account");
    expect(preferredTab("ding", false)).toBe("account");
  });

  it("lands on a safe menu, otherwise the first leaf", () => {
    expect(landingPath(menus, "/ims/auth/position")).toBe("/ims/auth/position");
    expect(landingPath(menus, "https://evil.example")).toBe("/ims/auth/org");
    expect(landingPath([], "/ims/auth/org")).toBe("/");
  });

  it("lands on the workbench when that menu exists", () => {
    expect(landingPath([{ path: "/ims/workbench" }], "/")).toBe("/ims/workbench");
  });

  it("detects the ding talk app", () => {
    expect(inDingTalk("Mozilla DingTalk")).toBe(true);
    expect(inDingTalk("Mozilla Chrome")).toBe(false);
  });
});
