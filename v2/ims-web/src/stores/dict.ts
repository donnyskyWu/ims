import { defineStore } from "pinia";
import { dictSimpleList } from "@/api/generated/endpoints";

export interface DictItem {
  dictValue: string;
  dictLabel: string;
  colorType: string;
  status: string;
  sort: number;
}

const TTL = 10 * 60 * 1000;

interface Bucket {
  items: DictItem[];
  at: number;
}

function normalize(raw: unknown): DictItem[] {
  const list = Array.isArray(raw) ? raw : ((raw as { list?: unknown })?.list ?? []);
  if (!Array.isArray(list)) return [];
  return list.map((item) => {
    const row = item as Record<string, unknown>;
    return {
      dictValue: String(row.dictValue || row.value || ""),
      dictLabel: String(row.dictLabel || row.label || ""),
      colorType: String(row.colorType || "neutral"),
      status: String(row.status || "ENABLED"),
      sort: Number(row.sort || 0),
    };
  });
}

export const useDictStore = defineStore("dict", {
  state: () => ({
    buckets: {} as Record<string, Bucket>,
    inflight: {} as Record<string, Promise<DictItem[]> | undefined>,
  }),
  actions: {
    async getDict(type: string, force = false): Promise<DictItem[]> {
      const cached = this.buckets[type];
      if (!force && cached && Date.now() - cached.at < TTL) return cached.items;
      const pending = this.inflight[type];
      if (pending && !force) return pending;
      const task = dictSimpleList<unknown>(type)
        .then((data) => {
          const items = normalize(data);
          this.buckets[type] = { items, at: Date.now() };
          return items;
        })
        .finally(() => {
          delete this.inflight[type];
        });
      this.inflight[type] = task;
      return task;
    },
    async refresh(type: string) {
      return this.getDict(type, true);
    },
    items(type: string): DictItem[] {
      return this.buckets[type]?.items || [];
    },
    label(type: string, value: string | null | undefined): string {
      if (value === null || value === undefined || value === "") return "—";
      const found = this.items(type).find((item) => item.dictValue === value);
      if (!found) {
        console.warn(`字典未收录：${type}`);
        return String(value);
      }
      return found.dictLabel;
    },
    color(type: string, value: string | null | undefined): string {
      const found = this.items(type).find((item) => item.dictValue === value);
      return found?.colorType || "neutral";
    },
    seed(type: string, items: DictItem[]) {
      this.buckets[type] = { items, at: Date.now() };
    },
  },
});
