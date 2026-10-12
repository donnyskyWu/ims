import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { bindSession, http, request, resetHttpForTests } from "./http";

vi.mock("@/utils/toast", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

function ok(config: InternalAxiosRequestConfig, data: unknown, status = 200): AxiosResponse {
  return { data, status, statusText: "", headers: { "x-trace-id": "abcdef123456" }, config };
}

describe("http", () => {
  beforeEach(() => {
    resetHttpForTests();
    bindSession({
      authHeader: () => "Bearer old",
      refresh: vi.fn(async () => true),
      onKick: vi.fn(),
      onExpired: vi.fn(),
    });
  });

  it("unwraps a successful payload", async () => {
    http.defaults.adapter = async (config) => ok(config, { code: 0, msg: "成功", data: { id: "9" } });
    await expect(request({ url: "/auth/me" })).resolves.toEqual({ id: "9" });
  });

  it("refreshes once and replays queued 401 requests", async () => {
    let refreshCount = 0;
    http.defaults.adapter = async (config) => {
      if (String(config.url).includes("refresh-token")) {
        refreshCount += 1;
        return ok(config, { code: 0, data: { accessToken: "new", refreshToken: "r" } });
      }
      const retried = (config as { _retried?: boolean })._retried;
      if (!retried) {
        const error = Object.assign(new Error("401"), {
          config,
          response: { status: 401, data: { code: 1002, msg: "登录已失效，请重新登录" }, headers: {} },
          isAxiosError: true,
        });
        throw error;
      }
      return ok(config, { code: 0, data: { ok: true } });
    };
    bindSession({
      authHeader: () => "Bearer old",
      refresh: async () => {
        refreshCount += 1;
        return true;
      },
      onKick: vi.fn(),
      onExpired: vi.fn(),
    });
    const [first, second] = await Promise.all([request({ url: "/demo/a", silent: true }), request({ url: "/demo/b", silent: true })]);
    expect(first).toEqual({ ok: true });
    expect(second).toEqual({ ok: true });
    expect(refreshCount).toBe(1);
  });
});
