import { describe, expect, it } from "vitest";
import { flattenGroups, nodeText, type GroupNode } from "./logic";

const tree: GroupNode[] = [
  {
    id: "1",
    groupName: "华东大组",
    groupType: "BIG",
    level: "S",
    memberCount: 2,
    accountCount: 1,
    authorCount: 1,
    children: [
      { id: "2", groupName: "直播小组", groupType: "SMALL", memberCount: 1, accountCount: 1, authorCount: 1 },
      { id: "3", groupName: "短视频小组", groupType: "SMALL", memberCount: 1, accountCount: 0, authorCount: 0 },
    ],
  },
];

describe("ip group tree search", () => {
  it("keeps the parent when a small group matches and highlights the hit", () => {
    const rows = flattenGroups(tree, "直播");
    expect(rows.map((item) => item.groupName)).toEqual(["华东大组", "直播小组"]);
    expect(rows[0].hit).toBe(false);
    expect(rows[1].hit).toBe(true);
    expect(rows[1].depth).toBe(1);
  });

  it("returns an empty list when nothing matches", () => {
    expect(flattenGroups(tree, "不存在")).toEqual([]);
  });

  it("formats the node with counts and level", () => {
    expect(nodeText(tree[0])).toBe("华东大组 (2/1/1) [S级]");
  });
});
