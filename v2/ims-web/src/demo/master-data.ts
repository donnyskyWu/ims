export interface MasterRow {
  id: string;
  label: string;
  certExpired?: boolean;
  platform?: string;
  status?: string;
  ipGroupId?: string;
  accountId?: string;
  parentLabel?: string;
  children?: MasterRow[];
}

export const realNames: MasterRow[] = [
  { id: "rn-1", label: "张敏", certExpired: false },
  { id: "rn-2", label: "李四", certExpired: true },
];

export const accounts: MasterRow[] = [
  { id: "ac-1", label: "短视频一号", platform: "短视频", status: "使用中", ipGroupId: "ip-2" },
  { id: "ac-2", label: "图文二号", platform: "图文", status: "停用", ipGroupId: "ip-1" },
];

export const ipGroups: MasterRow[] = [
  {
    id: "ip-1",
    label: "华东大组",
    children: [{ id: "ip-2", label: "上海小组", parentLabel: "华东大组" }],
  },
];

export const authors: MasterRow[] = [
  { id: "au-1", label: "作者甲", accountId: "ac-1" },
  { id: "au-2", label: "作者乙", accountId: "ac-2" },
];

export const companies: MasterRow[] = [{ id: "co-1", label: "星河文化有限公司" }];
export const assets: MasterRow[] = [{ id: "as-1", label: "直播电脑 01" }];
export const simCards: MasterRow[] = [{ id: "sim-1", label: "尾号 1024" }];
export const matches: MasterRow[] = [{ id: "mt-1", label: "周末联赛" }];
export const topics: MasterRow[] = [{ id: "tp-1", label: "开季选题" }];

export function pageOf(rows: MasterRow[], keyword: string, pageNo: number) {
  const matched = rows.filter((row) => !keyword || row.label.includes(keyword));
  const start = (pageNo - 1) * 20;
  return { list: matched.slice(start, start + 20), total: matched.length };
}
