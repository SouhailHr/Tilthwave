import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

const emit = vi.fn();
vi.mock("@/lib/eventBus", () => ({ emit: (...args: unknown[]) => emit(...args), subscribe: () => () => {} }));

// Every request goes through the real client, interceptors included; only the wire is faked.
function answer(status: number): AxiosAdapter {
  return async (config: InternalAxiosRequestConfig) => {
    const response = { status, statusText: "", headers: {}, config, data: { detail: "x" } } as AxiosResponse;
    if (status >= 400) {
      const { AxiosError } = await import("axios");
      throw new AxiosError("failed", "ERR_BAD_REQUEST", config, undefined, response);
    }
    return response;
  };
}

beforeEach(() => {
  vi.resetModules();
  emit.mockClear();
  document.cookie = "tw_csrf=; Max-Age=0; Path=/";
});

describe("api client", () => {
  it("emits auth:expired once for two simultaneous 401s (one redirect, not two)", async () => {
    const { api } = await import("./client");
    api.defaults.adapter = answer(401);
    const results = await Promise.allSettled([api.get("/zones/"), api.get("/farms/")]);
    expect(results.map((r) => r.status)).toEqual(["rejected", "rejected"]);
    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit).toHaveBeenCalledWith(expect.objectContaining({ type: "auth:expired" }));
  });

  it("emits again after the microtask reset, so expire-then-relogin-then-expire still redirects", async () => {
    const { api } = await import("./client");
    api.defaults.adapter = answer(401);
    await api.get("/zones/").catch(() => {});
    await Promise.resolve(); // the guard resets on the next tick
    await api.get("/zones/").catch(() => {});
    expect(emit).toHaveBeenCalledTimes(2);
  });

  it("does not treat a 401 from the session probe as an expiry", async () => {
    const { api } = await import("./client");
    api.defaults.adapter = answer(401);
    await api.get("/auth/me").catch(() => {});
    expect(emit).not.toHaveBeenCalled();
  });

  it("sends the CSRF cookie as a header on mutations only, with credentials", async () => {
    document.cookie = "tw_csrf=abc123; Path=/";
    const { api, CSRF_HEADER } = await import("./client");
    const seen: InternalAxiosRequestConfig[] = [];
    api.defaults.adapter = async (config) => {
      seen.push(config);
      return { status: 200, statusText: "", headers: {}, config, data: {} } as AxiosResponse;
    };
    await api.post("/zones/", {});
    await api.get("/zones/");
    expect(api.defaults.withCredentials).toBe(true);
    expect(seen[0].headers?.[CSRF_HEADER]).toBe("abc123");
    expect(seen[1].headers?.[CSRF_HEADER]).toBeUndefined();
  });
});
