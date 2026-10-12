import { describe, expect, it } from "vitest";
import { dateLine, greeting, greetingByHour, identityLine, messageEmpty, relativeTime, summaryLine, todoEmpty } from "./logic";

describe("workbench copy", () => {
  it("picks the greeting by shanghai hour", () => {
    expect(greetingByHour(4)).toBe("凌晨好");
    expect(greetingByHour(5)).toBe("早上好");
    expect(greetingByHour(10)).toBe("早上好");
    expect(greetingByHour(11)).toBe("中午好");
    expect(greetingByHour(13)).toBe("下午好");
    expect(greetingByHour(18)).toBe("晚上好");
    expect(greetingByHour(23)).toBe("凌晨好");
    expect(greeting(new Date("2026-10-12T01:00:00Z"))).toBe("早上好");
  });

  it("builds the identity and summary lines", () => {
    expect(identityLine("测试员工", "市场一部", "测试-直播运营")).toBe("测试员工（市场一部·测试-直播运营）");
    expect(summaryLine(dateLine(new Date("2026-10-12T01:00:00Z")), 3, 2)).toContain("待办 3 条");
    expect(summaryLine("今天", 0, 0)).toContain("未读消息 0 条");
  });

  it("describes empty lists", () => {
    expect(todoEmpty(false)).toBe("暂无待办");
    expect(todoEmpty(true)).toBe("无匹配待办");
    expect(messageEmpty("ALL", "")).toBe("暂无消息");
    expect(messageEmpty("UNREAD", "")).toBe("暂无未读消息");
    expect(messageEmpty("READ", "  ")).toBe("暂无已读消息");
    expect(messageEmpty("ALL", "找不到")).toBe("无匹配消息");
  });

  it("formats a recent shanghai timestamp", () => {
    const now = new Date("2026-10-12T02:30:00Z");
    expect(relativeTime("2026-10-12T10:00:00", now)).toBe("30 分钟前");
    expect(relativeTime("", now)).toBe("—");
  });
});
