/** 场次编号与风控纯函数。页面和路由冒烟共用。 */

export const SESSION_CODE = /^IMS\d{8}[A-Z]{3}\d{4,5}$/;

export function riskLevel(score: number): "GREEN" | "YELLOW" | "RED" {
  if (score >= 70) return "RED";
  if (score >= 40) return "YELLOW";
  return "GREEN";
}

export function durationText(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return "—";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours && mins) return `${hours} 小时 ${mins} 分`;
  if (hours) return `${hours} 小时`;
  return `${mins} 分`;
}

export function derived(gmv: number | null, orders: number | null, viewers: number | null, cost: number | null) {
  const money = (left: number | null, right: number | null) => {
    if (left === null || !right) return null;
    return (Math.round((left / right) * 100) / 100).toFixed(2);
  };
  return {
    unitPrice: money(gmv, orders),
    uvValue: money(gmv, viewers),
    roas: money(gmv, cost),
  };
}

export function ruleError(input: { ruleType: string; metric: string; operator: string; threshold: number; windowMinutes?: number | null }): string {
  if (input.ruleType === "THRESHOLD" && !["GMV_DROP", "VIEWER_DROP", "BALANCE_LOW"].includes(input.metric)) {
    return "阈值型指标不正确";
  }
  if (input.ruleType === "EVENT" && !["ACCOUNT_ABNORMAL", "BANNED_WORD"].includes(input.metric)) {
    return "事件型指标不正确";
  }
  if (input.ruleType === "THRESHOLD" && (input.windowMinutes == null || input.windowMinutes < 1 || input.windowMinutes > 60)) {
    return "窗口须为 1～60 分钟";
  }
  if (input.operator === "PCT_DROP" && (input.threshold < 1 || input.threshold > 100)) {
    return "降幅须为 1～100";
  }
  return "";
}
