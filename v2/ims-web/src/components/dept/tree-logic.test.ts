import { describe, expect, it } from "vitest";
import { canMoveDept, fallbackSelection, filterDeptTree, type DeptNode } from "./tree-logic";

const tree: DeptNode[] = [
  {
    id: "1",
    parentId: "0",
    name: "星河传媒",
    source: "DINGTALK",
    status: "ENABLED",
    localOrphan: 0,
    memberCount: 2,
    directMemberCount: 1,
    leaderUserId: "",
    children: [
      {
        id: "2",
        parentId: "1",
        name: "市场部",
        source: "DINGTALK",
        status: "ENABLED",
        localOrphan: 0,
        memberCount: 1,
        directMemberCount: 0,
        leaderUserId: "",
        children: [
          {
            id: "3",
            parentId: "2",
            name: "市场一组",
            source: "DINGTALK",
            status: "ENABLED",
            localOrphan: 0,
            memberCount: 1,
            directMemberCount: 1,
            leaderUserId: "",
            children: [],
          },
        ],
      },
      {
        id: "4",
        parentId: "1",
        name: "运营部",
        source: "LOCAL",
        status: "ENABLED",
        localOrphan: 0,
        memberCount: 1,
        directMemberCount: 1,
        leaderUserId: "",
        children: [],
      },
    ],
  },
];

describe("dept tree logic", () => {
  it("filters by name and keeps ancestors", () => {
    const found = filterDeptTree(tree, "一组");
    expect(found[0].name).toBe("星河传媒");
    expect(found[0].children[0].name).toBe("市场部");
    expect(found[0].children[0].children[0].name).toBe("市场一组");
  });

  it("blocks moving into descendants or local parents", () => {
    expect(canMoveDept(tree, "2", "3").ok).toBe(false);
    expect(canMoveDept(tree, "2", "4").reason).toContain("本地部门");
    expect(canMoveDept(tree, "4", "2").ok).toBe(true);
  });

  it("falls back to the parent when the node disappears", () => {
    expect(fallbackSelection(tree, "9", false)).toBe(null);
    expect(fallbackSelection(tree, "3", false)).toBe("3");
  });
});
