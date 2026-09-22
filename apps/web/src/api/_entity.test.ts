import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/utils/tokenStorage", () => ({
  getStoredToken: () => null,
  clearStoredToken: () => {},
  setStoredToken: () => {},
}));

import {
  entityChildKey,
  entityDetailKey,
  entityListKey,
  entityRootKey,
} from "./_entity";

describe("Generic Repository key helpers", () => {
  it("entityListKey is parameterised by params", () => {
    expect(entityListKey("zones", { page: 1, size: 20 })).toEqual([
      "zones",
      "list",
      { page: 1, size: 20 },
    ]);
  });

  it("entityDetailKey nests the id under the resource", () => {
    expect(entityDetailKey("farms", 7)).toEqual(["farms", "detail", 7]);
  });

  it("entityRootKey is the invalidation prefix that matches list + detail", () => {
    const root = entityRootKey("sensors");
    expect(root).toEqual(["sensors"]);
    expect(entityListKey("sensors", {}).slice(0, 1)).toEqual(root);
    expect(entityDetailKey("sensors", 1).slice(0, 1)).toEqual(root);
  });

  it("entityChildKey supports stats / sub-resources", () => {
    expect(entityChildKey("farms", "stats", "Sunny")).toEqual([
      "farms",
      "stats",
      "Sunny",
    ]);
    expect(entityChildKey("farms", "stats", "Sunny").slice(0, 1)).toEqual(
      entityRootKey("farms"),
    );
  });
});

describe("client interceptor 401 redirect contract", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("emits auth:expired and clears the token on 401", async () => {
    const events: { type: string }[] = [];
    let clearedCount = 0;

    vi.doMock("@/utils/tokenStorage", () => ({
      getStoredToken: () => "fake-token",
      clearStoredToken: () => {
        clearedCount += 1;
      },
      setStoredToken: () => {},
    }));
    vi.doMock("@/lib/eventBus", () => ({
      emit: (e: { type: string }) => events.push(e),
      subscribe: () => () => {},
    }));

    const { api } = await import("./client");

    // Manually trigger the interceptor's rejection handler the way axios would.
    const interceptors = (
      api.interceptors.response as unknown as {
        handlers: { fulfilled: unknown; rejected: (err: unknown) => unknown }[];
      }
    ).handlers;
    const handler = interceptors[0]?.rejected;
    expect(handler).toBeTypeOf("function");

    await expect(
      handler({
        response: { status: 401 },
        isAxiosError: true,
      } as never),
    ).rejects.toBeDefined();

    expect(clearedCount).toBe(1);
    expect(events.some((e) => e.type === "auth:expired")).toBe(true);
  });
});

describe("createEntity Idempotency-Key", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("attaches a fresh key per call, scoped to this request only", async () => {
    // Regression for: the key used to be generated in the axios request interceptor, so it
    // fired for every POST including /auth/login (which must never carry one), and a key
    // generated there can't survive being the same across a retry of one logical attempt.
    const post = vi.fn().mockResolvedValue({ data: { id: 1 } });
    vi.doMock("@/api/client", () => ({ api: { post } }));

    const { createEntity } = await import("./_entity");
    await createEntity("zones", { zone_name: "Zone A" });
    await createEntity("zones", { zone_name: "Zone B" });

    expect(post).toHaveBeenCalledTimes(2);
    const [, , firstConfig] = post.mock.calls[0];
    const [, , secondConfig] = post.mock.calls[1];
    const firstKey = firstConfig.headers["Idempotency-Key"];
    const secondKey = secondConfig.headers["Idempotency-Key"];
    expect(firstKey).toEqual(expect.any(String));
    expect(firstKey).not.toBe(secondKey);
  });
});