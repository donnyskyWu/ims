export const TODO_TABS = [
  { key: "ALL", label: "全部" },
  { key: "APPROVAL", label: "审批" },
  { key: "RETURN", label: "归还" },
  { key: "REVIEW", label: "审核" },
  { key: "CONFIRM", label: "确认" },
  { key: "WARNING", label: "预警" },
  { key: "ALERT", label: "告警" },
  { key: "LEARN", label: "学习" },
] as const;

export const MESSAGE_TABS = [
  { key: "ALL", label: "全部" },
  { key: "UNREAD", label: "未读" },
  { key: "READ", label: "已读" },
] as const;

export const BIZ_CARDS = [
  { field: "myAccountCount", title: "我名下账号", path: "/ims/asset/reverse" },
  { field: "myAssetCount", title: "我名下资产", path: "/ims/asset/mine" },
  { field: "myCertCount", title: "我的证件", path: "/ims/cert/archive", warnField: "myCertWarningCount" },
  { field: "myLiveSessionCount", title: "我的场次", path: "/ims/live/ledger" },
] as const;

export const PLACEHOLDER_HINT = "该能力将在后续模块交付";
export const SOON_HINT = "功能将在后续批次交付";

export function greetingByHour(hour: number): string {
  if (hour >= 5 && hour < 11) return "早上好";
  if (hour >= 11 && hour < 13) return "中午好";
  if (hour >= 13 && hour < 18) return "下午好";
  if (hour >= 18 && hour < 23) return "晚上好";
  return "凌晨好";
}

export function shanghaiHour(now: Date): number {
  const text = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    hour: "numeric",
    hourCycle: "h23",
  }).format(now);
  return Number(text);
}

export function greeting(now = new Date()): string {
  return greetingByHour(shanghaiHour(now));
}

export function dateLine(now = new Date()): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(now);
}

export function identityLine(name: string, dept: string, roles: string): string {
  const tail = [dept, roles].filter(Boolean).join("·");
  if (!name) return tail;
  if (!tail) return name;
  return `${name}（${tail}）`;
}

export function summaryLine(dateText: string, todoCount: number, unread: number): string {
  return `${dateText} · 待办 ${todoCount} 条 · 未读消息 ${unread} 条`;
}

export function parseShanghai(value: string | null | undefined): Date | null {
  if (!value) return null;
  const text = value.includes("T") ? value : value.replace(" ", "T");
  const zoned = /[zZ]|[+-]\d{2}:\d{2}$/.test(text) ? text : `${text}+08:00`;
  const date = new Date(zoned);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

export function formatShanghai(value: string | null | undefined): string {
  const date = parseShanghai(value);
  if (!date) return "—";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const pick = (type: string) => parts.find((item) => item.type === type)?.value || "";
  return `${pick("year")}-${pick("month")}-${pick("day")} ${pick("hour")}:${pick("minute")}`;
}

export function relativeTime(value: string | null | undefined, now = new Date()): string {
  const date = parseShanghai(value);
  if (!date) return "—";
  const delta = now.getTime() - date.getTime();
  if (delta < 0) return formatShanghai(value);
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  return formatShanghai(value);
}

export function todoEmpty(filtered: boolean): string {
  return filtered ? "无匹配待办" : "暂无待办";
}

export function messageEmpty(tab: string, keyword: string): string {
  if (keyword.trim()) return "无匹配消息";
  if (tab === "UNREAD") return "暂无未读消息";
  if (tab === "READ") return "暂无已读消息";
  return "暂无消息";
}

export function tabCount(byType: Record<string, number> | undefined, key: string, total: number): number {
  if (key === "ALL") return total;
  return Number(byType?.[key] || 0);
}
