import { describe, expect, it } from "vitest";
import { decidePolicy, networkMessage, type ErrorCodeEntry } from "./error-policy";

const table: ErrorCodeEntry[] = [
  { code: 1001, msg: "参数校验失败", strategy: "fieldError" },
  { code: 1002, msg: "登录已失效，请重新登录", strategy: "relogin" },
  { code: 1003, msg: "您的账号已在其他设备登录，本设备已下线", strategy: "relogin" },
  { code: 1008, msg: "暂无权限", strategy: "noPermission" },
  { code: 1504, msg: "资源不可用", strategy: "toast" },
  { code: 5007, msg: "系统繁忙，请稍后再试", strategy: "toast" },
];

describe("error policy", () => {
  it("maps field errors without toast when a form is open", () => {
    const decision = decidePolicy(
      { code: 1001, msg: "参数校验失败", data: { fieldErrors: [{ field: "name", message: "不能为空" }] } },
      table,
      { hasForm: true },
    );
    expect(decision.toast).toBeUndefined();
    expect(decision.fieldErrors?.[0].field).toBe("name");
  });

  it("toasts no permission and keeps the page", () => {
    expect(decidePolicy({ code: 1008, msg: "暂无权限" }, table).toast).toBe("暂无权限");
  });

  it("closes the drawer on missing resource", () => {
    const decision = decidePolicy({ code: 1504, msg: "资源不可用" }, table, { inDrawer: true });
    expect(decision.closeDrawer).toBe(true);
    expect(decision.toast).toBe("资源不可用");
  });

  it("appends a problem number for server errors", () => {
    const decision = decidePolicy({ code: 5007, msg: "系统繁忙，请稍后再试", traceId: "abcdef12-9999" }, table);
    expect(decision.toast).toBe("系统繁忙，请稍后再试 问题编号：abcdef12");
  });

  it("kicks the session on another login", () => {
    expect(decidePolicy({ code: 1003, msg: "您的账号已在其他设备登录，本设备已下线" }, table).relogin).toBe("kick");
  });

  it("stays quiet when silent", () => {
    expect(decidePolicy({ code: 1008, msg: "暂无权限" }, table, { silent: true })).toEqual({});
  });

  it("uses the network copy", () => {
    expect(networkMessage()).toBe("网络异常，请检查网络后重试");
  });
});
