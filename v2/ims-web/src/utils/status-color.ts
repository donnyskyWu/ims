const KNOWN = ["primary", "success", "warning", "danger", "neutral", "info", "purple", "yellow"] as const;

export type ColorType = (typeof KNOWN)[number];

export function statusVars(colorType: string | null | undefined): { color: string; background: string } {
  const name = KNOWN.includes(colorType as ColorType) ? (colorType as ColorType) : "neutral";
  return { color: `var(--st-${name}-fg)`, background: `var(--st-${name}-bg)` };
}
