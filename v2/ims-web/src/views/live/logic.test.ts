import { describe, expect, it } from "vitest";
import { SESSION_CODE, derived, durationText, riskLevel, ruleError } from "./logic";

describe("live logic", () => {
  it("scores the 39/40/69/70 boundaries and accepts a 5-digit session code", () => {
    expect(riskLevel(39)).toBe("GREEN");
    expect(riskLevel(40)).toBe("YELLOW");
    expect(riskLevel(69)).toBe("YELLOW");
    expect(riskLevel(70)).toBe("RED");
    expect(SESSION_CODE.test("IMS20261013DYS0001")).toBe(true);
    expect(SESSION_CODE.test("IMS20261013DYS10000")).toBe(true);
    expect(SESSION_CODE.test("IMS20261013DYS001")).toBe(false);
    expect(durationText(185)).toBe("3 小时 5 分");
    expect(derived(100, 0, 4, 20).unitPrice).toBeNull();
    expect(derived(100, 4, 0, 0).roas).toBeNull();
    expect(ruleError({ ruleType: "THRESHOLD", metric: "VIEWER_DROP", operator: "PCT_DROP", threshold: 30, windowMinutes: 0 })).toContain("窗口");
  });
});
