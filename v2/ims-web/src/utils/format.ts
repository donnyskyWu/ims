const EMPTY = "—";

function blank(value: unknown): boolean {
  return value === null || value === undefined || value === "";
}

export function fmtMoney(value: string | number | null | undefined): string {
  if (blank(value)) return EMPTY;
  const number = Number(value);
  if (Number.isNaN(number)) return EMPTY;
  const abs = Math.abs(number).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return number < 0 ? `¥-${abs}` : `¥${abs}`;
}

export function moneyNegative(value: string | number | null | undefined): boolean {
  if (blank(value)) return false;
  const number = Number(value);
  return !Number.isNaN(number) && number < 0;
}

export function fmtPercent(value: string | number | null | undefined): string {
  if (blank(value)) return EMPTY;
  const number = Number(value);
  if (Number.isNaN(number)) return EMPTY;
  return `${number}%`;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function asDate(value: string | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

export function fmtTime(value: string | Date | null | undefined): string {
  if (blank(value) || value === undefined || value === null) return EMPTY;
  const date = asDate(value);
  if (!date) return EMPTY;
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fmtDate(value: string | Date | null | undefined): string {
  if (blank(value) || value === undefined || value === null) return EMPTY;
  const date = asDate(value);
  if (!date) return EMPTY;
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function fmtMonth(value: string | Date | null | undefined): string {
  if (blank(value) || value === undefined || value === null) return EMPTY;
  if (typeof value === "string" && /^\d{4}-\d{2}$/.test(value)) return value;
  const date = asDate(value);
  if (!date) return EMPTY;
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
}

export function fmtRange(start: string | null | undefined, end: string | null | undefined): string {
  if (blank(start) && blank(end)) return EMPTY;
  return `${start || EMPTY} ~ ${end || EMPTY}`;
}

export function emptyText(value: unknown): string {
  if (blank(value)) return EMPTY;
  return String(value);
}

export const EMPTY_MARK = EMPTY;
