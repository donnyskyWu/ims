import { describe, expect, it } from "vitest";
import { hasAllPerm, hasAnyPerm, hasPerm, isPermCode } from "./perm";

const state = {
  permCodes: ["ims:demo:order:query", "ims:demo:order:create"],
  permDetails: {
    "ims:demo:order:query": { r: 1, w: 0, d: 0 },
    "ims:demo:order:create": { r: 1, w: 1, d: 0 },
  },
};

describe("perm", () => {
  it("checks codes and actions", () => {
    expect(hasPerm(state, "ims:demo:order:query")).toBe(true);
    expect(hasPerm(state, "ims:demo:order:query", "w")).toBe(false);
    expect(hasPerm(state, "ims:demo:order:create", "w")).toBe(true);
    expect(hasPerm(state, "ims:demo:order:delete")).toBe(false);
    expect(hasAnyPerm(state, ["ims:demo:order:delete", "ims:demo:order:query"])).toBe(true);
    expect(hasAllPerm(state, ["ims:demo:order:query", "ims:demo:order:create"], "r")).toBe(true);
  });

  it("rejects malformed codes", () => {
    expect(isPermCode("ims:demo:order:query")).toBe(true);
    expect(isPermCode("admin")).toBe(false);
  });
});
