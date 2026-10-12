import { ElMessage } from "element-plus";

type Level = "success" | "warning" | "error" | "info";

const recent: { text: string; at: number }[] = [];
let showing = 0;

function push(level: Level, text: string, duration = 3000): void {
  const now = Date.now();
  const hit = recent.find((item) => item.text === text && now - item.at < 1000);
  if (hit) return;
  recent.push({ text, at: now });
  if (recent.length > 20) recent.shift();
  if (showing >= 3) return;
  showing += 1;
  ElMessage({
    type: level,
    message: text,
    duration,
    grouping: false,
    offset: 16,
    onClose: () => {
      showing = Math.max(0, showing - 1);
    },
  });
}

export const toast = {
  success(text: string, duration?: number) {
    push("success", text, duration);
  },
  warning(text: string, duration?: number) {
    push("warning", text, duration);
  },
  error(text: string, duration?: number) {
    push("error", text, duration);
  },
  info(text: string, duration?: number) {
    push("info", text, duration);
  },
};

export function resetToastForTests(): void {
  recent.splice(0, recent.length);
  showing = 0;
}
