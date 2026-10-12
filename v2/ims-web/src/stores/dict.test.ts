import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { dictSimpleList } from "@/api/generated/endpoints";
import { useDictStore } from "./dict";

vi.mock("@/api/generated/endpoints", () => ({
  dictSimpleList: vi.fn(),
}));

describe("dict store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(dictSimpleList).mockReset();
  });

  it("caches a type and collapses concurrent reads", async () => {
    vi.mocked(dictSimpleList).mockResolvedValue([{ dictValue: "ACTIVE", dictLabel: "在职", colorType: "success", status: "ENABLED" }]);
    const store = useDictStore();
    const [first, second] = await Promise.all([store.getDict("dict_user_status"), store.getDict("dict_user_status")]);
    expect(first).toEqual(second);
    expect(dictSimpleList).toHaveBeenCalledTimes(1);
    expect(store.label("dict_user_status", "ACTIVE")).toBe("在职");
    expect(store.color("dict_user_status", "ACTIVE")).toBe("success");
  });

  it("warns and shows the raw value when missing", () => {
    const store = useDictStore();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(store.label("dict_user_status", "UNKNOWN")).toBe("UNKNOWN");
    expect(warn).toHaveBeenCalled();
  });
});
