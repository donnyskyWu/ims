export interface ConfirmOptions {
  title: string;
  message: string;
  okText?: string;
  danger?: boolean;
  reasonRequired?: boolean;
  reasonLabel?: string;
  reasonMax?: number;
  action?: (reason?: string) => Promise<void>;
}

export interface ConfirmResult {
  reason?: string;
}

type Opener = (options: ConfirmOptions) => Promise<ConfirmResult>;

let opener: Opener | null = null;

export function registerConfirm(fn: Opener): void {
  opener = fn;
}

export function confirm(options: ConfirmOptions): Promise<ConfirmResult> {
  if (!opener) return Promise.reject(new Error("确认框尚未就绪"));
  return opener(options);
}
