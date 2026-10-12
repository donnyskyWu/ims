import { describe, expect, it } from "vitest";
import { fmtDate, fmtMoney, fmtPercent, fmtRange, fmtTime, moneyNegative } from "./format";

describe("format", () => {
  it("formats money, percent and empty", () => {
    expect(fmtMoney("1234.5")).toBe("¥1,234.50");
    expect(fmtMoney("-20")).toBe("¥-20.00");
    expect(moneyNegative("-20")).toBe(true);
    expect(fmtMoney("")).toBe("—");
    expect(fmtPercent(5)).toBe("5%");
    expect(fmtPercent(null)).toBe("—");
  });

  it("formats time and range", () => {
    expect(fmtTime("2026-10-12T10:05:00")).toBe("2026-10-12 10:05");
    expect(fmtDate("2026-10-12T10:05:00")).toBe("2026-10-12");
    expect(fmtRange("2026-10-05", "2026-10-11")).toBe("2026-10-05 ~ 2026-10-11");
  });
});
